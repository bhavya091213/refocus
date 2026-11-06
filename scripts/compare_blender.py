import os
from PIL import Image, ImageDraw
root = "/home/ubuntu/refocus"; W, H = 220, 308
import sys
for sc, k in [(j.split(":")[0], int(j.split(":")[1])) for j in sys.argv[1:]]:
    out = f"{root}/learn2refocus/outputs/blender/{sc}_in{k}/validation_images/focal_position_000{k}"
    gt = lambda i: Image.open(f"{root}/blender_in/renders/{sc}/focal_position_000{i}.png").convert("RGB").resize((W, H))
    sheet = Image.new("RGB", (9 * W, 3 * H + 36), (15, 17, 21)); d = ImageDraw.Draw(sheet)
    rows = ["Blender ground truth (real optics)", "Model output from ONE input photo", f"Input given to the model (position {k})"]
    for r in range(3): d.text((6, r * (H + 12) + 0), rows[r], fill=(230, 232, 238))
    for i in range(9):
        y0 = 12
        sheet.paste(gt(i), (i * W, y0))
        sheet.paste(Image.open(f"{out}/frame_{i}.png").convert("RGB").resize((W, H)), (i * W, y0 + H + 12))
        if i == k: sheet.paste(gt(i), (i * W, y0 + 2 * (H + 12)))
        d.text((i * W + 6, y0 + 2), f"pos {i}", fill=(255, 255, 255))
    sheet.save(f"{root}/compare_{sc}_in{k}.jpg", quality=90)
print("ok")
