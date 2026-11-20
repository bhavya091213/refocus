#!/bin/bash
# Runs ON the GPU instance. Once the arm-A retrain has finished, evaluates it with exactly the
# protocol of the original ablation (20 test scenes x input positions 1, 4, 7; one process,
# full precision), on GPU 1, then scores it with eval_metrics.py. Same commands as
# scripts/run_single_arm.sh. Needs ~/eval_metrics.py. Progress goes to ~/STATUS.
set -u
NAME=${NAME:-armA}; STEPS=${STEPS:-4000}; GPU=${GPU:-1}
st() { echo "[$(date -u +%H:%M:%S)] $1" | tee -a ~/STATUS; }

until grep -qE "TRAIN (DONE|FAILED) $NAME" ~/STATUS 2>/dev/null; do sleep 10; done
grep -q "TRAIN DONE $NAME" ~/STATUS || { st "EVAL SKIPPED: training failed"; exit 1; }
cd ~/refocus/learn2refocus && . ../venv/bin/activate || exit 1
export WANDB_MODE=offline PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 4#' \
    -e "s#^output_dir:.*#output_dir: \"./outputs/eval_$NAME\"#" \
    -e "s#^load_from_checkpoint:.*#load_from_checkpoint: \"./outputs/$NAME/checkpoint-$STEPS\"#" \
    -e 's#^conditioning:.*#conditioning: "random"#' -e "s#^run_name:.*#run_name: \"eval_$NAME\"#" \
    training/configs/focal_stacks_test.yaml > "training/configs/eval_$NAME.yaml"

st "EVAL START $NAME (20 scenes x positions 1,4,7, GPU $GPU)"
CUDA_VISIBLE_DEVICES=$GPU REFOCUS_EVAL_SCENES=20 REFOCUS_EVAL_POS=1,4,7 accelerate launch --num_processes 1 --mixed_precision no \
    --main_process_port 29600 training/svd_runner.py --config "training/configs/eval_$NAME.yaml" > ~/eval_"$NAME".log 2>&1
CUDA_VISIBLE_DEVICES=$GPU python ~/eval_metrics.py "$NAME" 20 1,4,7 > ~/metrics_"$NAME".log 2>&1
SUMMARY=$(python -c "import json;s=json.load(open('outputs/eval_$NAME/metrics.json'))['summary'];print('PSNR',s['psnr'],'SSIM',s['ssim'],'LPIPS',s['lpips'],'depth-rho',s['depth_consistency_rho'],'items',s['n_items'])" 2>/dev/null)
if grep -q EVAL_METRICS_DONE ~/metrics_"$NAME".log && [ -n "$SUMMARY" ]; then
  # keep a second copy of the small result files in ~ so they are quick to fetch before the instance goes away
  cp "outputs/eval_$NAME/metrics.json" ~/metrics_"$NAME".json
  st "EVAL DONE $NAME: $SUMMARY"
else
  st "EVAL FAILED $NAME (see ~/eval_$NAME.log ~/metrics_$NAME.log)"
fi
