#!/bin/bash
cd /d/Refocus
until grep -q SETUP_DONE logs/setup_rerun.log; do sleep 30; done
ssh -i $HOME/.ssh/lambda_parakeet_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL ubuntu@158.101.19.101 'cd ~ && sed -i "s/\r$//" run_single_arm.sh && (nohup bash run_single_arm.sh > ~/pipeline.log 2>&1 &) ; sleep 2; echo launched'
