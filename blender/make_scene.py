"""Build a depth-layered scene from Poly Haven CC0 assets and render a 9-frame focal stack with Blender's thin-lens DoF.
Run:  blender -b -P make_scene.py -- --scene still_life --out D:/Refocus/blender/renders/still_life [--preview] [--only 3]
Frame k = camera focus distance FOCUS[k]. Resolution 640x896 (portrait, matches the training data)."""
import bpy, sys, math, os, argparse
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scene", default="still_life"); ap.add_argument("--out", required=True)
ap.add_argument("--preview", action="store_true"); ap.add_argument("--only", type=int, default=None)
ap.add_argument("--samples", type=int, default=48); ap.add_argument("--fstop", type=float, default=1.4)
a = ap.parse_args(argv)

ASSETS = "D:/Refocus/blender/assets"
W, H = (320, 448) if a.preview else (640, 896)
# focus distances in metres for the 9 positions (position 8 ~ infinity). Log-spaced; NOT the phone's calibration -- see report.
FOCUS = [0.45, 0.6, 0.85, 1.2, 1.8, 2.8, 4.5, 9.0, 200.0]

# scene presets: (asset, depth m, lateral -1..1, target height m, yaw deg)
SCENES = {
    "still_life": dict(hdri="studio_small_09", floor=(0.55, 0.42, 0.30), items=[
        ("rubber_duck_toy", 0.8, -0.5, 0.13, 20), ("food_apple_01", 0.9, 0.5, 0.09, 0),
        ("marble_bust_01", 1.7, 0.05, 0.50, 20), ("potted_plant_02", 3.0, -0.6, 0.60, 0),
        ("concrete_cat_statue", 4.8, 0.55, 0.60, 20)]),
    "garden": dict(hdri="kloofendal_48d_partly_cloudy_puresky", floor=(0.18, 0.30, 0.10), items=[
        ("rock_moss_set_01", 0.8, -0.5, 0.18, 30), ("rubber_duck_toy", 0.6, 0.55, 0.13, 200),
        ("tree_small_02", 3.5, -0.45, 2.0, 0), ("marble_bust_01", 2.0, 0.35, 0.50, 20), ("potted_plant_02", 5.5, 0.4, 0.8, 0)]),
}
SCENES["macro"] = dict(hdri="studio_small_09", floor=(0.55, 0.42, 0.30), phone=True, items=[
    ("rubber_duck_toy", 0.10, -0.45, 0.040, 20), ("food_apple_01", 0.133, 0.45, 0.035, 0),
    ("marble_bust_01", 0.20, -0.05, 0.075, 20), ("concrete_cat_statue", 0.40, 0.45, 0.15, 20), ("potted_plant_02", 0.40, -0.5, 0.15, 0)])
S = SCENES[a.scene]
PHONE = S.get("phone", False)
if PHONE:   # phone-like camera (small sensor, wide lens, f/1.8) and the README's position scale: 0..8 = 5 cm..infinity, ASSUMED linear in diopters
    LENS, SENSOR, CAM_Z = 6.0, 7.0, 0.03
    FOCUS = [1.0 / (20.0 * (1 - k / 8.0)) for k in range(8)] + [200.0]
    if a.fstop == 1.4: a.fstop = 1.8
else:
    LENS, SENSOR, CAM_Z = 50.0, 36.0, 0.28

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 16 if a.preview else a.samples
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Filmic" if "Filmic" in [e.identifier for e in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "AgX"
# GPU if available (AMD -> HIP), else CPU
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dt in ("HIP", "OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dt; prefs.get_devices()
            if any(d.type == dt for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == dt
                sc.cycles.device = "GPU"; print("DEVICE", dt); break
        except Exception: pass
except Exception as e: print("gpu setup failed", e)

# world: HDRI
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(f"{ASSETS}/{S['hdri']}/{S['hdri']}_1k.hdr")
bg = nt.nodes.new("ShaderNodeBackground"); out = nt.nodes.new("ShaderNodeOutputWorld")
mapn = nt.nodes.new("ShaderNodeMapping"); tc = nt.nodes.new("ShaderNodeTexCoord")
mapn.inputs["Rotation"].default_value[2] = math.radians(100)
nt.links.new(tc.outputs["Generated"], mapn.inputs["Vector"]); nt.links.new(mapn.outputs["Vector"], env.inputs["Vector"])
nt.links.new(env.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
bg.inputs["Strength"].default_value = 1.0

# floor
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 8, 0)); fl = bpy.context.object
m = bpy.data.materials.new("floor"); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*S["floor"], 1)
m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6; fl.data.materials.append(m)

# camera
cam_z = CAM_Z
bpy.ops.object.camera_add(location=(0, 0, cam_z)); cam = bpy.context.object; sc.camera = cam
cam.data.lens = LENS; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_width = SENSOR; cam.data.sensor_height = SENSOR
cam.rotation_euler = (math.radians(90 - 5), 0, 0)   # slight downward tilt
cam.data.clip_start = 0.005; cam.data.clip_end = 1000.0
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = a.fstop
half_w = (SENSOR / 2 / LENS) * W / H  # horizontal half-extent per metre of depth

def place(asset, depth, lat, height, yaw):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f"{ASSETS}/{asset}/{asset}.gltf")
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(asset + "_root", None); bpy.context.collection.objects.link(root)
    for o in new:
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = height / max(hi.z - lo.z, 1e-6); root.scale = (s, s, s)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2; cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2; zmin = min(p.z for p in pts)
    root.location = (lat * half_w * depth - cx, depth - cy, -zmin)
    root.rotation_euler[2] = math.radians(yaw)

for it in S["items"]: place(*it)

# a key light so objects have some form independent of the HDRI
bpy.ops.object.light_add(type="AREA", location=((-0.3, -0.1, 0.5) if PHONE else (-1.2, -0.3, 2.0))); L = bpy.context.object; L.data.energy = 15 if PHONE else 200; L.data.size = 0.5 if PHONE else 2.0
L.rotation_euler = (math.radians(60), 0, math.radians(-25))

os.makedirs(a.out, exist_ok=True)
for k, d in enumerate(FOCUS):
    if a.only is not None and k != a.only: continue
    cam.data.dof.focus_distance = d
    sc.render.filepath = f"{a.out}/focal_position_{k:04d}.png"
    bpy.ops.render.render(write_still=True); print("RENDERED", k, d)
