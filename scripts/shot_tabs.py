import sys, time
from playwright.sync_api import sync_playwright
key = open("D:/Refocus/dashboard/token.txt").read().strip(); outdir = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_context(viewport={"width": 1000, "height": 1000}).new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(f"http://127.0.0.1:8791/?key={key}", wait_until="networkidle"); time.sleep(3)
    for t in sys.argv[2:]:
        pg.click(f".tab[data-t='{t}']"); time.sleep(3)
        pg.screenshot(path=f"{outdir}/tab_{t}.png", full_page=True)
    print("JS errors:", errs or "none")
    b.close()
