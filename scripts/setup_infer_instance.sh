#!/bin/bash
# usage: setup_infer_instance.sh <ip>  -> installs env, code, starts the inference server on the instance (no dataset needed). Prints INFER_SETUP_DONE.
IP=$1; cd /d/Refocus
KEY="$HOME/.ssh/lambda_parakeet_ed25519"; SO="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o UserKnownHostsFile=NUL"
SSH() { ssh -i $KEY $SO ubuntu@$IP "$@"; }
until SSH 'echo up' >/dev/null 2>&1; do sleep 10; done; echo "ssh up $(date -u +%T)"
SSH 'mkdir -p ~/refocus'
scp -q -i $KEY $SO scripts/remote_setup.sh scripts/infer_server.py ubuntu@$IP:~/
SSH 'sed -i "s/\r$//" ~/remote_setup.sh ~/infer_server.py; (nohup bash ~/remote_setup.sh > ~/setup.log 2>&1 &); echo env-setup started'
tar --exclude=.git -cf - -C code learn2refocus | SSH 'tar -xf - -C ~/refocus' && echo "code uploaded"
until SSH 'grep -q ENV_OK ~/setup.log' 2>/dev/null; do sleep 10; done; echo "env ok"
SSH 'cd ~/refocus/learn2refocus && . ../venv/bin/activate && cp ~/infer_server.py . && (nohup python infer_server.py > ~/infer_server.log 2>&1 &); echo server-started'
until SSH 'curl -s localhost:8801/health' 2>/dev/null | grep -q ok; do sleep 15; SSH 'tail -n 2 ~/infer_server.log' 2>/dev/null | grep -qi "error\|Traceback" && { echo SERVER_FAILED; SSH 'tail -n 15 ~/infer_server.log'; exit 1; }; done
echo INFER_SETUP_DONE
