"""Smoke test: python D:/Refocus/.venv-pw/Scripts/python.exe -I viewer/test_viewer.py  (server on :8765 must be running)"""
import sys
from playwright.sync_api import sync_playwright
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 1000})
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8765/"); pg.wait_for_function("document.querySelectorAll('#strip button').length==9")
    res = {}
    sel = pg.eval_on_selector_all("#stackSel option", "o=>o.map(x=>x.value+':'+x.text)"); print(sel)
    def click(fx, fy):
        box = pg.locator("#view").bounding_box(); pg.mouse.click(box["x"] + fx * box["width"], box["y"] + fy * box["height"]); pg.wait_for_timeout(450)
        return pg.inner_text("#posNum")
    pg.select_option("#stackSel", index=5)   # blender_macro
    pg.wait_for_timeout(600)
    # the macro scene: duck (left-top), apple (lower right), bust, cat (bottom right)  -> expect different positions
    pts = [(0.22, 0.54), (0.74, 0.52), (0.47, 0.40), (0.76, 0.76)]
    for i, (fx, fy) in enumerate(pts):
        res[(fx, fy)] = click(fx, fy); print("macro click", fx, fy, "->", res[(fx, fy)])
        if i == 1: pg.screenshot(path=OUT + "/viewer_macro.png")
    pg.check("#depthChk"); pg.wait_for_timeout(500); pg.screenshot(path=OUT + "/viewer_depth.png"); pg.uncheck("#depthChk")
    pg.select_option("#stackSel", index=0); pg.wait_for_timeout(600); print("real click", click(0.3, 0.3), click(0.5, 0.75)); pg.screenshot(path=OUT + "/viewer_real.png")
    print("distinct positions in macro:", len(set(res.values())))
    print("console errors:", errs); b.close()
