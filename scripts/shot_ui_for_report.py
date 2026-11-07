"""Screenshots of the click-to-refocus viewer for the report (serves viewer/ locally on :8766)."""
import subprocess, sys, time
from playwright.sync_api import sync_playwright
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766", "--bind", "127.0.0.1"], cwd="D:/Refocus/viewer", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
OUT = "D:/Refocus/report/"
try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); pg = b.new_context(viewport={"width": 1200, "height": 1500}).new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:8766/", wait_until="networkidle")
        idx = pg.evaluate("[...document.querySelectorAll('#stackSel option')].map(o=>o.textContent)"); print(idx)
        sel = next(i for i, t in enumerate(idx) if "acro" in t)
        pg.select_option("#stackSel", str(sel)); time.sleep(1.5)
        box = pg.locator("#wrap").bounding_box(); print(box)
        def click(fx, fy, name):
            pg.mouse.click(box["x"] + fx * box["width"], box["y"] + fy * box["height"]); time.sleep(1.2)
            pg.screenshot(path=OUT + name, clip={"x": 0, "y": 0, "width": 1200, "height": box["y"] + box["height"] + 110})
            print(name, pg.inner_text("#posNum"), pg.inner_text("#posNote"))
        click(0.22, 0.55, "ui_click_duck.png")      # duck (near)
        click(0.76, 0.28, "ui_click_cat.png")       # cat (far)
        pg.check("#depthChk"); time.sleep(1.0)
        pg.screenshot(path=OUT + "ui_depth.png", clip={"x": 0, "y": 0, "width": 1200, "height": box["y"] + box["height"] + 110})
        pg.uncheck("#depthChk")
        click(0.5, 0.88, "ui_click_flat.png")       # blank floor, low texture
        print("errors:", errs or "none"); b.close()
finally:
    srv.terminate()
