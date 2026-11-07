#!/bin/bash
# usage: setup_new_instance.sh <ip>      (run from Git Bash on the PC)  -> prints SETUP_DONE when the instance is ready for run_ablation_8x.sh
IP=$1; cd /d/Refocus
KEY="$HOME/.ssh/lambda_parakeet_ed25519"; SO="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=NUL"
SSH() { ssh -i $KEY $SO ubuntu@$IP "$@"; }
until SSH 'echo up' >/dev/null 2>&1; do sleep 10; done; echo "ssh up $(date -u +%T)"
# 1) environment + model downloads on the instance (background there)
scp -q -i $KEY $SO scripts/remote_setup.sh scripts/remote_patch.py scripts/eval_metrics.py scripts/run_ablation_8x.sh scripts/run_single_arm.sh logs/dash.env ubuntu@$IP:~/
SSH 'mv ~/dash.env ~/dash.env; mkdir -p ~/refocus; (nohup bash ~/remote_setup.sh > ~/setup.log 2>&1 &); echo env-setup started'
# 2) code + dataset upload (parallel with the env install)
tar --exclude=.git -cf - -C code learn2refocus | SSH 'tar -xf - -C ~/refocus' && echo "code uploaded"
scp -q -i $KEY $SO data/raw/scenes_merged_midsize_undistorted_RigCenter.zip ubuntu@$IP:~/refocus/ && echo "dataset zip uploaded"
SSH 'cd ~/refocus && mkdir -p data && unzip -q -o scenes_merged_midsize_undistorted_RigCenter.zip -d data && echo "dataset extracted: $(ls data/*/ | wc -l) scenes"'
# 3) wait for env, then weights + patches
until SSH 'grep -q ENV_OK ~/setup.log' 2>/dev/null; do sleep 10; done; echo "env ok"
SSH 'cd ~/refocus/learn2refocus && . ../venv/bin/activate && python setup/download_svd_weights.py > ~/dl_svd.log 2>&1 && python setup/download_checkpoints.py > ~/dl_ckpt.log 2>&1 && echo weights-done' && echo "weights downloaded"
SSH '. ~/refocus/venv/bin/activate && python ~/remote_patch.py && pip install -q lpips 2>&1 | tail -1; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader'
echo SETUP_DONE
