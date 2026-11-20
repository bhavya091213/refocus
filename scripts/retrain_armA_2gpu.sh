#!/bin/bash
# Runs ON the GPU instance. Re-trains arm A (conditioning=random) with the original recipe:
# SVD base, seed from the authors' config, 2 GPUs x per-GPU batch 1 (global batch 2),
# lr 1e-5 x scale_lr(2) = 2e-5, bf16, 4,000 steps. Same settings as scripts/run_ablation_8x.sh.
# Env: STEPS (4000), NAME (armA), CK (checkpoint every N steps, 2000),
#      GC (gradient checkpointing true|false; changes memory and speed, not the result).
set -u
cd ~/refocus/learn2refocus && . ../venv/bin/activate || exit 1
export WANDB_MODE=offline PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True REFOCUS_SKIP_VAL=1
STEPS=${STEPS:-4000}; NAME=${NAME:-armA}; CK=${CK:-2000}; GC=${GC:-true}
st() { echo "[$(date -u +%H:%M:%S)] $1" | tee -a ~/STATUS; }

sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 6#' \
    -e "s#^output_dir:.*#output_dir: \"./outputs/$NAME\"#" -e "s#^run_name:.*#run_name: \"$NAME\"#" \
    -e 's#^conditioning:.*#conditioning: "random"#' -e "s#^max_train_steps:.*#max_train_steps: $STEPS#" \
    -e "s#^gradient_checkpointing:.*#gradient_checkpointing: $GC#" -e 's#^mixed_precision:.*#mixed_precision: bf16#' \
    -e 's#^validation_steps:.*#validation_steps: 100000000#' -e "s#^checkpointing_steps:.*#checkpointing_steps: $CK#" \
    training/configs/focal_stacks_train.yaml > "training/configs/$NAME.yaml"

st "TRAIN START $NAME ($STEPS steps, 2 GPUs, gradient checkpointing $GC)"
CUDA_VISIBLE_DEVICES=0,1 accelerate launch --multi_gpu --num_processes 2 --num_machines 1 --mixed_precision bf16 \
    --main_process_port 29501 training/svd_runner.py --config "training/configs/$NAME.yaml" > ~/train_"$NAME".log 2>&1
if [ -d "outputs/$NAME/checkpoint-$STEPS/unet" ]; then
  st "TRAIN DONE $NAME"
else
  st "TRAIN FAILED $NAME (see ~/train_$NAME.log)"; exit 1
fi
