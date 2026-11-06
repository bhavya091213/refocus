"""Real sample data for the click-to-refocus animation: variance-of-Laplacian in a window around a point, per frame."""
import json, numpy as np
from PIL import Image
fr=[np.asarray(Image.open(f"D:/Refocus/remotion/public/frames/f{i}.jpg").convert("L"),dtype=np.float64) for i in range(9)]
H,W=fr[0].shape
def lap(a): return -4*a[1:-1,1:-1]+a[:-2,1:-1]+a[2:,1:-1]+a[1:-1,:-2]+a[1:-1,2:]
L=[lap(a) for a in fr]
def sharp(cx,cy,r=22):
    return [float(l[max(cy-r,0):cy+r, max(cx-r,0):cx+r].var()) for l in L]
best={}
for cy in range(40,H-40,20):
    for cx in range(40,W-40,20):
        s=sharp(cx,cy); k=int(np.argmax(s)); sc=max(s)/ (np.mean(s)+1e-9)
        if sc>1.8 and (k not in best or sc>best[k][0]): best[k]=(sc,cx,cy,s)
out=[{"x":v[1],"y":v[2],"winner":k,"sharp":[round(x,1) for x in v[3]]} for k,v in sorted(best.items())]
print(json.dumps([{ "x":o["x"],"y":o["y"],"winner":o["winner"]} for o in out]))
json.dump({"w":W,"h":H,"points":out}, open("D:/Refocus/remotion/src/sharpness.json","w"))
