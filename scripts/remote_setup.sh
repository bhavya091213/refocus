set -e
cd ~/refocus
python3 -m venv venv && . venv/bin/activate
pip install -q --upgrade pip
pip install -q torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
pip install -q numpy==1.26.0 diffusers==0.32.0 transformers==4.50.0 accelerate==1.5.2 huggingface-hub==0.29.3 safetensors==0.5.3 \
  einops==0.8.1 peft==0.15.0 pillow==9.5.0 opencv-python-headless==4.11.0.86 scipy==1.15.2 scikit-image==0.24.0 \
  torchmetrics==1.7.4 torch-fidelity==0.3.0 lpips pyyaml==6.0.2 tqdm==4.67.1 matplotlib==3.10.1 imageio==2.37.0 imageio-ffmpeg==0.6.0 videoio==0.3.0 wandb==0.19.8 requests
python -c "import torch,diffusers,transformers;print('ENV_OK',torch.__version__,torch.cuda.is_available(),diffusers.__version__,transformers.__version__)"
