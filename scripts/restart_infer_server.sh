for p in $(pgrep -f "python infer_server"); do kill $p; done
sleep 2
cd ~/refocus/learn2refocus && . ../venv/bin/activate
sed -i 's/decode_chunk_size=8/decode_chunk_size=2/' simple_inference.py
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True REFOCUS_MAXPIX=${MAXPIX:-500000}
nohup python infer_server.py > ~/infer_server.log 2>&1 &
echo restarted
