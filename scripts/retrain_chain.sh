#!/bin/bash
# Runs ON the GPU instance after remote_bootstrap.sh, unattended:
#   1. one-scene inference test with the base SVD U-Net (catches script errors before the long run)
#   2. 30-step smoke test with gradient checkpointing off, to see whether the faster path fits in memory
#   3. arm A training, 4,000 steps (retrain_armA_2gpu.sh)
#   4. full-size stacks for the scenes listed in ~/candidates.txt, input position 4, one process per GPU
# Progress lines go to ~/STATUS. Needs in ~: retrain_armA_2gpu.sh, infer_stacks.py, candidates.txt.
set -u
st() { echo "[$(date -u +%H:%M:%S)] $1" | tee -a ~/STATUS; }
BASE=/home/ubuntu/refocus/data/scenes_merged_midsize_undistorted_RigCenter
scene_dir() { echo "$BASE/$1/midsize/undistorted/RigCenter"; }

until grep -qE "BOOTSTRAP (DONE|FAILED)" ~/STATUS 2>/dev/null; do sleep 5; done
grep -q "BOOTSTRAP DONE" ~/STATUS || { st "CHAIN STOPPED: bootstrap failed"; exit 1; }
cd ~/refocus/learn2refocus && . ../venv/bin/activate || exit 1
cp ~/infer_stacks.py .
mapfile -t SCENES < ~/candidates.txt

# 1. inference test (base weights, so the output itself is meaningless; we only check the path works)
if CUDA_VISIBLE_DEVICES=0 python infer_stacks.py ./svdh/unet outputs/infer_test 4 "$(scene_dir "${SCENES[0]}")" > ~/infer_test.log 2>&1; then
  st "INFER TEST OK: $(tail -n 1 ~/infer_test.log)"
else
  st "INFER TEST FAILED (see ~/infer_test.log); continuing with training"
fi

# 2. smoke test without gradient checkpointing
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -l 2 > ~/smoke_mem.log 2>/dev/null &
MEMPID=$!
STEPS=30 NAME=smoke CK=100000 GC=false bash ~/retrain_armA_2gpu.sh > /dev/null 2>&1
kill "$MEMPID" 2>/dev/null
PEAK=$(sort -n ~/smoke_mem.log | tail -n 1)
SPEED=$(tr '\r' '\n' < ~/train_smoke.log | grep -o '30/30 \[[^]]*\]' | tail -n 1)
if [ -n "$SPEED" ] && [ "${PEAK:-99999}" -lt 72000 ]; then GC=false; else GC=true; fi
st "SMOKE: checkpointing off -> peak ${PEAK:-?} MiB, ${SPEED:-did not finish}; training with gradient_checkpointing=$GC"

# 3. the real run
STEPS=4000 NAME=armA CK=1000 GC=$GC bash ~/retrain_armA_2gpu.sh || { st "CHAIN STOPPED: training failed"; exit 1; }

# 4. full-size stacks, split across the two GPUs
UNET=outputs/armA/checkpoint-4000/unet
A=(); B=()
for i in "${!SCENES[@]}"; do
  if [ $((i % 2)) -eq 0 ]; then A+=("$(scene_dir "${SCENES[$i]}")"); else B+=("$(scene_dir "${SCENES[$i]}")"); fi
done
st "INFER START (${#SCENES[@]} scenes, input position 4)"
CUDA_VISIBLE_DEVICES=0 python infer_stacks.py "$UNET" outputs/demo 4 "${A[@]}" > ~/infer0.log 2>&1 &
P0=$!
CUDA_VISIBLE_DEVICES=1 python infer_stacks.py "$UNET" outputs/demo 4 "${B[@]}" > ~/infer1.log 2>&1 &
P1=$!
wait "$P0"; R0=$?
wait "$P1"; R1=$?
if [ "$R0" -eq 0 ] && [ "$R1" -eq 0 ]; then st "INFER DONE: $(wc -l < outputs/demo/psnr.tsv) stacks"; else st "INFER FAILED (see ~/infer0.log ~/infer1.log)"; fi
st "CHAIN DONE"
