cd ~/refocus/learn2refocus && . ../venv/bin/activate
export WANDB_MODE=offline CUDA_VISIBLE_DEVICES=7
for k in 4 6; do
  python simple_inference.py --image_path ~/refocus/blender_in/renders/macro/focal_position_000$k.png --input_focal_position $k --output_dir outputs/blender/macro_in$k 2>&1 | grep -vE "Warning|warn|it/s|s/it" | tail -2
done
echo MACRO_INFER_DONE
