# usage: remote_bench.sh <tag> <mixed_precision: no|bf16> <grad_ckpt: false|true> <steps>
set -e
TAG=$1; MP=$2; GC=$3; STEPS=${4:-50}
cd ~/refocus/learn2refocus && . ../venv/bin/activate
sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 6#' \
    -e "s#^output_dir:.*#output_dir: \"./outputs/$TAG\"#" -e "s#^max_train_steps:.*#max_train_steps: $STEPS#" \
    -e "s#^gradient_checkpointing:.*#gradient_checkpointing: $GC#" -e "s#^mixed_precision:.*#mixed_precision: $( [ $MP = no ] && echo null || echo $MP )#" \
    -e 's#^validation_steps:.*#validation_steps: 100000#' training/configs/focal_stacks_train.yaml > training/configs/$TAG.yaml
export WANDB_MODE=offline REFOCUS_MAX_ITEMS=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -l 2 > ~/mem_$TAG.log &
MPID=$!
accelerate launch --num_processes 1 --mixed_precision $MP training/svd_runner.py --config training/configs/$TAG.yaml || echo "TRAIN_FAILED"
kill $MPID 2>/dev/null || true
echo "PEAK_MEM_MIB $(sort -n ~/mem_$TAG.log | tail -1)"
echo BENCH_DONE
