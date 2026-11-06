#!/bin/bash
# 8-GPU parallel ablation. Three arms train at the same time on 2 GPUs each (DDP), each arm is evaluated on its own GPU as soon as it finishes;
# the authors' 200k checkpoint is evaluated on GPU 6 meanwhile. GPU 7 is spare.
#   GPUs 0,1 : arm A  random            GPUs 2,3 : arm B  ablate_position        GPUs 4,5 : arm C  ablate_time        GPU 6 : authors' checkpoint eval
# Identical for all arms except `conditioning`: SVD base, seed 0, data, bf16, gradient checkpointing, per-GPU batch 1 (global batch 2), lr 1e-5 x scale_lr(2) = 2e-5.
# Env: STEPS (default 4000), EVAL_SCENES (20), EVAL_POS (1,4,7).  Needs ~/dash.env (DASH_BASE, DASH_KEY).
set -u
source ~/dash.env
cd ~/refocus/learn2refocus && . ../venv/bin/activate
export WANDB_MODE=offline PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True REFOCUS_SKIP_VAL=1 DASH_URL=$DASH_BASE DASH_KEY=$DASH_KEY
STEPS=${STEPS:-4000}; EVAL_SCENES=${EVAL_SCENES:-20}; EVAL_POS=${EVAL_POS:-1,4,7}; CK=$(( STEPS / 4 ))
log() { curl -s -m 5 -X POST "$DASH_BASE/api/ingest/log?key=$DASH_KEY" -H 'Content-Type: application/json' -d "{\"run\":\"pipeline\",\"line\":\"$1\"}" >/dev/null 2>&1 || true; echo "[$(date -u +%H:%M:%S)] $1"; }

mkcfg() {  # name mode
  sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 6#' \
      -e "s#^output_dir:.*#output_dir: \"./outputs/$1\"#" -e "s#^run_name:.*#run_name: \"$1\"#" -e "s#^conditioning:.*#conditioning: \"$2\"#" \
      -e "s#^max_train_steps:.*#max_train_steps: $STEPS#" -e 's#^gradient_checkpointing:.*#gradient_checkpointing: true#' -e 's#^mixed_precision:.*#mixed_precision: bf16#' \
      -e 's#^validation_steps:.*#validation_steps: 100000000#' -e "s#^checkpointing_steps:.*#checkpointing_steps: $CK#" training/configs/focal_stacks_train.yaml > training/configs/$1.yaml
}
train() {  # name mode gpus port
  local name=$1 mode=$2 gpus=$3 port=$4
  [ -f outputs/$name/TRAIN_DONE ] && { log "skip train $name"; return; }
  mkcfg $name $mode
  local last=$(ls -d outputs/$name/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
  if [ -n "$last" ]; then log "resuming $name from $last"; sed -i "s#^load_from_checkpoint:.*#load_from_checkpoint: \"$last\"#" training/configs/$name.yaml; fi
  log "TRAIN START $name (conditioning=$mode, $STEPS steps, GPUs $gpus)"
  CUDA_VISIBLE_DEVICES=$gpus accelerate launch --multi_gpu --num_processes 2 --num_machines 1 --mixed_precision bf16 --main_process_port $port \
      training/svd_runner.py --config training/configs/$name.yaml > ~/train_$name.log 2>&1
  if [ -d outputs/$name/checkpoint-$STEPS ]; then touch outputs/$name/TRAIN_DONE; log "TRAIN DONE $name"; else log "TRAIN FAILED $name (see ~/train_$name.log)"; return 1; fi
}
evalmodel() {  # name mode ckpt gpu scenes pos
  local name=$1 mode=$2 ckpt=$3 gpu=$4 ns=$5 pos=$6
  [ -f outputs/eval_$name/EVAL_DONE ] && { log "skip eval $name"; return; }
  sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 4#' -e "s#^output_dir:.*#output_dir: \"./outputs/eval_$name\"#" \
      -e "s#^load_from_checkpoint:.*#load_from_checkpoint: \"$ckpt\"#" -e "s#^conditioning:.*#conditioning: \"$mode\"#" -e "s#^run_name:.*#run_name: \"eval_$name\"#" \
      training/configs/focal_stacks_test.yaml > training/configs/eval_$name.yaml
  log "EVAL START $name on GPU $gpu ($ns scenes x positions $pos)"
  CUDA_VISIBLE_DEVICES=$gpu REFOCUS_EVAL_SCENES=$ns REFOCUS_EVAL_POS=$pos accelerate launch --num_processes 1 --mixed_precision no --main_process_port $((29600+gpu)) \
      training/svd_runner.py --config training/configs/eval_$name.yaml > ~/eval_$name.log 2>&1
  CUDA_VISIBLE_DEVICES=$gpu python ~/eval_metrics.py $name $ns $pos > ~/metrics_$name.log 2>&1
  if grep -q EVAL_METRICS_DONE ~/metrics_$name.log; then touch outputs/eval_$name/EVAL_DONE
    log "EVAL DONE $name: $(python -c "import json;s=json.load(open('outputs/eval_$name/metrics.json'))['summary'];print('PSNR',s['psnr'],'SSIM',s['ssim'],'LPIPS',s['lpips'],'depth-rho',s['depth_consistency_rho'])")"
  else log "EVAL FAILED $name (see ~/metrics_$name.log / ~/eval_$name.log)"; return 1; fi
}
arm() { train $1 $2 $3 $4 && evalmodel $1 $2 ./outputs/$1/checkpoint-$STEPS ${3%%,*} $EVAL_SCENES $EVAL_POS; }

log "PIPELINE 8x START steps=$STEPS (global batch 2) eval=$EVAL_SCENES scenes x $EVAL_POS"
arm armA_random random 0,1 29501 &
arm armB_ablate_position ablate_position 2,3 29502 &
arm armC_ablate_time ablate_time 4,5 29503 &
evalmodel authors200k random ./checkpoints/checkpoint-200000 6 $EVAL_SCENES $EVAL_POS &
wait
log "PIPELINE ALL DONE"
touch ~/ALL_DONE
