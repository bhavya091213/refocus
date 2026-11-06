import os, pickle, sys, collections
root = sys.argv[1]; spl = sys.argv[2]
scenes = {}
for s in os.listdir(root + "/scenes_merged_midsize_undistorted_RigCenter"):
    d = f"{root}/scenes_merged_midsize_undistorted_RigCenter/{s}/midsize/undistorted/RigCenter"
    if os.path.isdir(d): scenes[s] = len([f for f in os.listdir(d) if f.endswith(".jpg")])
c = collections.Counter(scenes.values())
tr = pickle.load(open(spl + "/train_scenes.pkl","rb")); te = pickle.load(open(spl + "/test_scenes.pkl","rb"))
print("scene dirs:", len(scenes), "frame-count histogram:", dict(c))
print("splits: train", len(tr), "test", len(te), "type", type(tr).__name__)
full = {s for s,n in scenes.items() if n==9}
print("usable train (9 frames):", len([s for s in tr if s in full]), " usable test:", len([s for s in te if s in full]))
print("dates:", sorted({s[4:12] for s in scenes})[:3], "...", sorted({s[4:12] for s in scenes})[-3:], "n days", len({s[4:12] for s in scenes}))
