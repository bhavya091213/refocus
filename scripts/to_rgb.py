import glob
from PIL import Image
n = 0
for p in glob.glob("/home/ubuntu/refocus/blender_in/renders/*/*.png"):
    im = Image.open(p)
    if im.mode != "RGB": im.convert("RGB").save(p); n += 1
print("converted", n)
