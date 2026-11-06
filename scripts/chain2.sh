#!/bin/bash
cd /d/Refocus
SSHO="-i $HOME/.ssh/lambda_parakeet_ed25519 -o StrictHostKeyChecking=no"
S="C:/Users/Raj/AppData/Local/Temp/claude/C--Windows-System32/960471f0-c3ff-421f-8954-03a25a2a9522/scratchpad"
scp -q $SSHO scripts/remote_blender_infer.sh scripts/compare_blender.py ubuntu@150.136.66.111:~/
ssh $SSHO ubuntu@150.136.66.111 'cd ~ && JOBS="still_f4:2 still_f4:6 still_f8:2 still_f8:6" bash ~/remote_blender_infer.sh > ~/job2.log 2>&1; . ~/refocus/venv/bin/activate && python ~/compare_blender.py still_f4:2 still_f4:6 still_f8:2 still_f8:6'
for n in still_f4_in2 still_f4_in6 still_f8_in2 still_f8_in6; do scp -q $SSHO ubuntu@150.136.66.111:~/refocus/compare_$n.jpg "$S/compare_$n.jpg"; done
echo CHAIN_DONE
