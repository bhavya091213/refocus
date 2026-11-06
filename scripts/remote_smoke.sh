set -e
cd ~/refocus/learn2refocus && . ../venv/bin/activate
# --- patch 1: optional cap on validation items (REFOCUS_MAX_ITEMS), recorded in repo patches/
python - <<'PY'
p="training/validation.py"; s=open(p).read()
if "REFOCUS_MAX_ITEMS" not in s:
    s=s.replace("        for batch in val_dataloader:\n","        _n = 0\n        for batch in val_dataloader:\n            if os.environ.get('REFOCUS_MAX_ITEMS') and _n >= int(os.environ['REFOCUS_MAX_ITEMS']): break\n            _n += 1\n",1)
    open(p,"w").write(s)
PY
sed -e 's#^data_folder:.*#data_folder: "/home/ubuntu/refocus/data"#' -e 's#^num_workers:.*#num_workers: 4#' -e 's#^output_dir:.*#output_dir: "./outputs/smoke"#' training/configs/focal_stacks_test.yaml > training/configs/smoke.yaml
export WANDB_MODE=offline REFOCUS_MAX_ITEMS=${1:-9}
/usr/bin/time -v accelerate launch --num_processes 1 --mixed_precision no training/svd_runner.py --config training/configs/smoke.yaml
