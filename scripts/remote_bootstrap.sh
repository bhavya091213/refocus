#!/bin/bash
# Runs ON a fresh GPU instance. Clones the authors' code at the commit we used, builds the
# Python env (remote_setup.sh), downloads the SVD base weights, unpacks the dataset once it
# has been uploaded, and applies our patches (remote_patch.py). Progress goes to ~/STATUS.
# Needs in ~: remote_setup.sh, remote_patch.py. The dataset zip is uploaded separately to
# ~/refocus/ and its arrival is signalled by ~/UPLOAD_DONE.
set -u
COMMIT=45e3aabc2
ZIP=scenes_merged_midsize_undistorted_RigCenter.zip
st() { echo "[$(date -u +%H:%M:%S)] $1" | tee -a ~/STATUS; }
fail() { st "BOOTSTRAP FAILED: $1"; exit 1; }

mkdir -p ~/refocus && cd ~/refocus || exit 1
st "BOOTSTRAP START"
if [ ! -d learn2refocus ]; then
  git clone -q -b dev https://github.com/tedlasai/learn2refocus || fail "git clone"
fi
(cd learn2refocus && git checkout -q "$COMMIT") || fail "checkout $COMMIT"
st "code at $(cd learn2refocus && git rev-parse --short HEAD)"

bash ~/remote_setup.sh > ~/setup.log 2>&1
grep -q ENV_OK ~/setup.log || fail "python env (see ~/setup.log)"
st "env ok: $(grep ENV_OK ~/setup.log)"

cd ~/refocus/learn2refocus && . ../venv/bin/activate
python setup/download_svd_weights.py > ~/dl_svd.log 2>&1 || fail "SVD weights (see ~/dl_svd.log)"
st "SVD weights downloaded"

until [ -f ~/UPLOAD_DONE ]; do sleep 5; done
cd ~/refocus && mkdir -p data && unzip -q -o "$ZIP" -d data || fail "unzip dataset"
st "dataset extracted: $(ls -d data/*/ | wc -l) scene folders"

python ~/remote_patch.py > ~/patch.log 2>&1 || fail "patches (see ~/patch.log)"
st "patches: $(tr '\n' ' ' < ~/patch.log)"
st "gpus: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | tr '\n' ';')"
st "BOOTSTRAP DONE"
