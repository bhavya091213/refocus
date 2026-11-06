#!/bin/bash
# wait for f4/f8 renders -> RGB -> upload -> infer -> compare -> pull sheets to scratchpad
cd /d/Refocus
SSHO="-i $HOME/.ssh/lambda_parakeet_ed25519 -o StrictHostKeyChecking=no"
S="C:/Users/Raj/AppData/Local/Temp/claude/C--Windows-System32/960471f0-c3ff-421f-8954-03a25a2a9522/scratchpad"
for d in still_f4 still_f8; do until [ "$(ls blender/renders/$d/*.png 2>/dev/null | wc -l)" -ge 9 ]; do sleep 10; done; done
sleep 8
python -I -c "
import glob
from PIL import Image
for p in glob.glob('D:/Refocus/blender/renders/still_f*/*.png'):
    im=Image.open(p)
    if im.mode!='RGB': im.convert('RGB').save(p)
print('rgb ok')"
tar -cf - -C blender renders/still_f4 renders/still_f8 | ssh $SSHO ubuntu@150.136.66.111 'mkdir -p ~/refocus/blender_in && tar -xf - -C ~/refocus/blender_in'
scp -q $SSHO scripts/remote_blender_infer.sh scripts/compare_blender.py ubuntu@150.136.66.111:~/
ssh $SSHO ubuntu@150.136.66.111 'cd ~ && JOBS="still_f4:2 still_f4:6 still_f8:2 still_f8:6" bash ~/remote_blender_infer.sh > ~/job2.log 2>&1; . ~/refocus/venv/bin/activate && python ~/compare_blender.py still_f4:2 still_f4:6 still_f8:2 still_f8:6'
for n in still_f4_in2 still_f4_in6 still_f8_in2 still_f8_in6; do scp -q $SSHO ubuntu@150.136.66.111:~/refocus/compare_$n.jpg "$S/compare_$n.jpg"; done
echo CHAIN_DONE
