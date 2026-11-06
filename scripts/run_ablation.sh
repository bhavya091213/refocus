#!/bin/bash
# End-to-end, resumable ablation pipeline. Runs on the Lambda instance.
#   smoke-eval -> train A -> eval A -> train B -> eval B -> train C -> eval C -> eval authors' checkpoint
# Arms (only 'conditioning' differs; same SVD base, seed, data, steps, hyperparameters):
#   A = random (paper default)   B = ablate_position (no position signal)   C = ablate_time (position via motion_bucket_id)
# Env: STEPS (default 10000), EVAL_SCENES (default 20), EVAL_POS (default 1,4,7). DASH_BASE/DASH_KEY in ~/dash.env
set -u
source ~/dash.env
cd ~/refocus/learn2refocus && . ../venv/bin/activate
export WANDB_MODE=offline PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True REFOCUS_SKIP_VAL=1 DASH_URL=$DASH_BASE DASH_KEY=$DASH_KEY
STEPS=${STEPS:-10000}; EVAL_SCENES=${EVAL_SCENES:-20}; EVAL_POS=${EVAL_POS:-1,4,7}
log() { curl -s -m 5 -X POST "$DASH_BASE/api/ingest/log?key=$DASH_KEY" -H 'Content-Type: application/json' -d "{\"run\":\"pipeline\",\"line\":\"$1\"}" >/dev/null 2>&1 || true; echo "[$(date -u +%H:%M:%S)] $1"; }

mkcfg() {  # name mode  -> training config (bf16 + gradient checkpointing; only 'conditioning' differs between arms)
  sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 6#' \
      -e "s#^output_dir:.*#output_dir: \"./outputs/$1\"#" -e "s#^run_name:.*#run_name: \"$1\"#" -e "s#^conditioning:.*#conditioning: \"$2\"#" \
      -e "s#^max_train_steps:.*#max_train_steps: $STEPS#" -e 's#^gradient_checkpointing:.*#gradient_checkpointing: true#' -e 's#^mixed_precision:.*#mixed_precision: bf16#' \
      -e 's#^validation_steps:.*#validation_steps: 100000000#' -e 's#^checkpointing_steps:.*#checkpointing_steps: 2500#' training/configs/focal_stacks_train.yaml > training/configs/$1.yaml
}
train() {  # name mode
  local name=$1 mode=$2
  [ -f outputs/$name/TRAIN_DONE ] && { log "skip train $name (done)"; return; }
  mkcfg $name $mode
  local last=$(ls -d outputs/$name/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
  if [ -n "$last" ]; then log "resuming $name from $last"; sed -i "s#^load_from_checkpoint:.*#load_from_checkpoint: \"$last\"#" training/configs/$name.yaml; fi
  log "TRAIN START $name (conditioning=$mode, $STEPS steps)"
  accelerate launch --num_processes 1 --mixed_precision bf16 training/svd_runner.py --config training/configs/$name.yaml > ~/train_$name.log 2>&1
  if [ -d outputs/$name/checkpoint-$STEPS ]; then touch outputs/$name/TRAIN_DONE; log "TRAIN DONE $name"; else log "TRAIN FAILED $name (see ~/train_$name.log)"; return 1; fi
}
evalmodel() {  # name mode ckpt_path scenes pos
  local name=$1 mode=$2 ckpt=$3 ns=$4 pos=$5
  [ -f outputs/eval_$name/EVAL_DONE ] && { log "skip eval $name (done)"; return; }
  sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 4#' -e "s#^output_dir:.*#output_dir: \"./outputs/eval_$name\"#" \
      -e "s#^load_from_checkpoint:.*#load_from_checkpoint: \"$ckpt\"#" -e "s#^conditioning:.*#conditioning: \"$mode\"#" -e "s#^run_name:.*#run_name: \"eval_$name\"#" \
      training/configs/focal_stacks_test.yaml > training/configs/eval_$name.yaml
  log "EVAL START $name ($ns scenes x positions $pos)"
  REFOCUS_EVAL_SCENES=$ns REFOCUS_EVAL_POS=$pos accelerate launch --num_processes 1 --mixed_precision no training/svd_runner.py --config training/configs/eval_$name.yaml > ~/eval_$name.log 2>&1
  python ~/eval_metrics.py $name $ns $pos > ~/metrics_$name.log 2>&1
  if grep -q EVAL_METRICS_DONE ~/metrics_$name.log; then touch outputs/eval_$name/EVAL_DONE; log "EVAL DONE $name: $(python -c "import json;s=json.load(open('outputs/eval_$name/metrics.json'))['summary'];print('PSNR',s['psnr'],'SSIM',s['ssim'],'LPIPS',s['lpips'],'depth-rho',s['depth_consistency_rho'])")"
  else log "EVAL FAILED $name (see ~/metrics_$name.log / ~/eval_$name.log)"; return 1; fi
}

log "PIPELINE START steps=$STEPS eval=$EVAL_SCENES scenes x $EVAL_POS"
evalmodel smoke random ./checkpoints/checkpoint-200000 2 $EVAL_POS || { log "SMOKE EVAL FAILED - stopping before training"; exit 1; }
[ -n "${ONLY_SMOKE:-}" ] && { log "smoke only: stopping here"; exit 0; }
train armA_random random            || exit 1
evalmodel armA_random random ./outputs/armA_random/checkpoint-$STEPS $EVAL_SCENES $EVAL_POS
train armB_ablate_position ablate_position || exit 1
evalmodel armB_ablate_position ablate_position ./outputs/armB_ablate_position/checkpoint-$STEPS $EVAL_SCENES $EVAL_POS
train armC_ablate_time ablate_time  || exit 1
evalmodel armC_ablate_time ablate_time ./outputs/armC_ablate_time/checkpoint-$STEPS $EVAL_SCENES $EVAL_POS
evalmodel authors200k random ./checkpoints/checkpoint-200000 $EVAL_SCENES $EVAL_POS
log "PIPELINE ALL DONE"
touch ~/ALL_DONE
