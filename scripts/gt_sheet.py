import sys
from PIL import Image
d, out = sys.argv[1], sys.argv[2]
W, H = 200, 280; s = Image.new("RGB", (9 * W, H))
for i in range(9): s.paste(Image.open(f"{d}/focal_position_{i:04d}.png").convert("RGB").resize((W, H)), (i * W, 0))
s.save(out, quality=90)
