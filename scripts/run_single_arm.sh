#!/bin/bash
# Re-train arm A (conditioning=random) on ONE A100 to obtain a kept checkpoint, then evaluate it on the same 20 scenes x positions 1,4,7.
# 1 GPU x gradient_accumulation_steps 2 x per-GPU batch 1 = global batch 2, lr = 1e-5 x 2 (accum) = 2e-5: same optimisation as the 2-GPU run. Seed 0.
# Env: STEPS (default 4000). Needs ~/dash.env.
set -u
source ~/dash.env
cd ~/refocus/learn2refocus && . ../venv/bin/activate
export WANDB_MODE=offline PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True REFOCUS_SKIP_VAL=1 DASH_URL=$DASH_BASE DASH_KEY=$DASH_KEY
STEPS=${STEPS:-4000}; NAME=armA_rerun
log() { curl -s -m 5 -X POST "$DASH_BASE/api/ingest/log?key=$DASH_KEY" -H 'Content-Type: application/json' -d "{\"run\":\"pipeline\",\"line\":\"$1\"}" >/dev/null 2>&1 || true; echo "[$(date -u +%H:%M:%S)] $1"; }
sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 6#' \
    -e "s#^output_dir:.*#output_dir: \"./outputs/$NAME\"#" -e "s#^run_name:.*#run_name: \"$NAME\"#" -e 's#^conditioning:.*#conditioning: "random"#' \
    -e "s#^max_train_steps:.*#max_train_steps: $STEPS#" -e 's#^gradient_checkpointing:.*#gradient_checkpointing: true#' -e 's#^mixed_precision:.*#mixed_precision: bf16#' \
    -e 's#^gradient_accumulation_steps:.*#gradient_accumulation_steps: 2#' -e 's#^validation_steps:.*#validation_steps: 100000000#' \
    -e "s#^checkpointing_steps:.*#checkpointing_steps: $STEPS#" training/configs/focal_stacks_train.yaml > training/configs/$NAME.yaml
last=$(ls -d outputs/$NAME/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
if [ -n "$last" ]; then log "resuming from $last"; sed -i "s#^load_from_checkpoint:.*#load_from_checkpoint: \"$last\"#" training/configs/$NAME.yaml; fi
log "TRAIN START $NAME (random, $STEPS steps, 1 GPU x accum 2)"
CUDA_VISIBLE_DEVICES=0 accelerate launch --num_processes 1 --mixed_precision bf16 --main_process_port 29501 training/svd_runner.py --config training/configs/$NAME.yaml > ~/train_$NAME.log 2>&1
[ -d outputs/$NAME/checkpoint-$STEPS ] || { log "TRAIN FAILED (see ~/train_$NAME.log)"; exit 1; }
touch outputs/$NAME/TRAIN_DONE; log "TRAIN DONE $NAME"
sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 4#' -e "s#^output_dir:.*#output_dir: \"./outputs/eval_$NAME\"#" \
    -e "s#^load_from_checkpoint:.*#load_from_checkpoint: \"./outputs/$NAME/checkpoint-$STEPS\"#" -e 's#^conditioning:.*#conditioning: "random"#' -e "s#^run_name:.*#run_name: \"eval_$NAME\"#" \
    training/configs/focal_stacks_test.yaml > training/configs/eval_$NAME.yaml
log "EVAL START $NAME (20 scenes x positions 1,4,7)"
CUDA_VISIBLE_DEVICES=0 REFOCUS_EVAL_SCENES=20 REFOCUS_EVAL_POS=1,4,7 accelerate launch --num_processes 1 --mixed_precision no --main_process_port 29600 training/svd_runner.py --config training/configs/eval_$NAME.yaml > ~/eval_$NAME.log 2>&1
CUDA_VISIBLE_DEVICES=0 python ~/eval_metrics.py $NAME 20 1,4,7 > ~/metrics_$NAME.log 2>&1
if grep -q EVAL_METRICS_DONE ~/metrics_$NAME.log; then log "EVAL DONE $NAME: $(python -c "import json;s=json.load(open('outputs/eval_$NAME/metrics.json'))['summary'];print('PSNR',s['psnr'],'SSIM',s['ssim'],'LPIPS',s['lpips'],'depth-rho',s['depth_consistency_rho'])")"; else log "EVAL FAILED (see ~/metrics_$NAME.log)"; fi
log "PIPELINE ALL DONE"; touch ~/ALL_DONE
