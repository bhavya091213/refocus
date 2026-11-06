cd ~/refocus/learn2refocus && . ../venv/bin/activate
export WANDB_MODE=offline
for job in ${JOBS:-still_life:2 still_life:6 garden:2 garden:5}; do
  sc=${job%%:*}; k=${job##*:}
  echo "=== $sc input_pos=$k"
  python simple_inference.py --image_path ~/refocus/blender_in/renders/$sc/focal_position_000$k.png --input_focal_position $k --output_dir outputs/blender/${sc}_in$k 2>&1 | grep -vE "Warning|warn|it/s|s/it" | tail -3
done
echo INFER_DONE
