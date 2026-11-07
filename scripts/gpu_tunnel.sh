#!/bin/bash
# keeps an ssh tunnel PC:8801 -> inference instance:8801 alive
cd /d/Refocus
while true; do
  IP=$(cat logs/infer_ip.txt)
  ssh -N -L 8801:127.0.0.1:8801 -i $HOME/.ssh/lambda_parakeet_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -o ServerAliveInterval=15 -o ExitOnForwardFailure=yes ubuntu@$IP
  sleep 10
done
