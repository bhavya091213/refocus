#!/bin/bash
# Unattended: wait for the arm-A re-run (train + eval) on the A100, pull the trained UNet + metrics + logs to this PC, then terminate the instance.
# Started with: nohup bash scripts/finish_rerun.sh > logs/finish_rerun.log 2>&1 &
cd /d/Refocus
IP=$(cat logs/new_ip.txt); IID=$(cat logs/instance_id.txt)
SSHO="-i $HOME/.ssh/lambda_parakeet_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ConnectTimeout=15"
OUT=/d/Refocus/checkpoints/armA_rerun; mkdir -p $OUT
echo "[$(date -u +%T)] waiting for pipeline on $IP"
until ssh $SSHO ubuntu@$IP 'grep -qE "ALL DONE|FAILED" ~/pipeline.log' 2>/dev/null; do sleep 120; done
ssh $SSHO ubuntu@$IP 'tail -n 8 ~/pipeline.log' 2>/dev/null | tee $OUT/pipeline.log
if ssh $SSHO ubuntu@$IP 'grep -q FAILED ~/pipeline.log' 2>/dev/null; then
  echo "[$(date -u +%T)] FAILED - pulling logs only, NOT terminating (watchdog will stop it at the deadline)"
  scp -q $SSHO "ubuntu@$IP:~/train_armA_rerun.log" "ubuntu@$IP:~/eval_armA_rerun.log" "ubuntu@$IP:~/metrics_armA_rerun.log" $OUT/ 2>/dev/null
  exit 1
fi
echo "[$(date -u +%T)] pulling results"
scp -q -r $SSHO "ubuntu@$IP:~/refocus/learn2refocus/outputs/armA_rerun/checkpoint-4000/unet" $OUT/ \
 && scp -q $SSHO "ubuntu@$IP:~/refocus/learn2refocus/outputs/eval_armA_rerun/metrics.json" "ubuntu@$IP:~/refocus/learn2refocus/outputs/eval_armA_rerun/sheet_in1.jpg" "ubuntu@$IP:~/refocus/learn2refocus/outputs/eval_armA_rerun/sheet_in4.jpg" "ubuntu@$IP:~/refocus/learn2refocus/outputs/eval_armA_rerun/sheet_in7.jpg" "ubuntu@$IP:~/train_armA_rerun.log" $OUT/ \
 && [ -f $OUT/unet/diffusion_pytorch_model.safetensors ] && [ -f $OUT/metrics.json ] && touch $OUT/PULLED_OK
if [ -f $OUT/PULLED_OK ]; then
  K=$(cat secrets/lambda.key | tr -d '\r\n')
  curl -s -X POST https://cloud.lambda.com/api/v1/instance-operations/terminate -H "Authorization: Bearer $K" -H 'Content-Type: application/json' -d "{\"instance_ids\":[\"$IID\"]}" | head -c 150
  echo; echo "[$(date -u +%T)] pulled OK and instance terminated"
else
  echo "[$(date -u +%T)] PULL INCOMPLETE - instance left running for the watchdog (deadline in logs/deadline.txt)"
fi
