import os, pickle, sys
from PIL import Image
root = "/home/ubuntu/refocus"; out = root + "/learn2refocus/outputs/smoke/validation_images"
te = pickle.load(open(root + "/learn2refocus/splits/test_scenes.pkl", "rb"))
base = root + "/data/scenes_merged_midsize_undistorted_RigCenter"
scenes = sorted(s for s in os.listdir(base) if s in set(te))
sc = scenes[0]; print("scene", sc, "n_positions_done", sorted(d for d in os.listdir(out) if d.startswith("position_") and os.path.isdir(out + "/" + d + "/images") and os.listdir(out + "/" + d + "/images")))
gt = [Image.open(f"{base}/{sc}/midsize/undistorted/RigCenter/focal_position_{i:04d}_frame_0000.jpg").convert("RGB") for i in range(9)]
W, H = 200, 280; sheet = Image.new("RGB", (9 * W, 3 * H), "black")
pos = int(sys.argv[1])
for i in range(9):
    sheet.paste(gt[i].resize((W, H)), (i * W, 0))
    p = f"{out}/position_{pos}/images/img_0_frame_{i}.png"
    sheet.paste(Image.open(p).convert("RGB").resize((W, H)), (i * W, H))
    if i == pos: sheet.paste(gt[pos].resize((W, H)), (i * W, 2 * H))   # the input photo
sheet.save(root + "/sheet.jpg", quality=90); print("ok")
