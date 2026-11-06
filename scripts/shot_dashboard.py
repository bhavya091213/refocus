import sys, time
from playwright.sync_api import sync_playwright
key = open("D:/Refocus/dashboard/token.txt").read().strip(); out = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_context(viewport={"width": 1000, "height": 1400}).new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(f"http://127.0.0.1:8791/?key={key}", wait_until="networkidle"); time.sleep(6)
    pg.locator("details.gpu[data-g='0'] > summary").click(); time.sleep(7)
    el = pg.locator("#gpus").locator("xpath=ancestor::div[contains(@class,'card')]"); el.screenshot(path=out)
    print("JS errors:", errs or "none")
    b.close()
