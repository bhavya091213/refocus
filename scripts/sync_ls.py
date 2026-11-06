import sys, time
from playwright.sync_api import sync_playwright
URL = "https://ln5.sync.com/dl/dc6d99c50#ra9336yd-w9u958dw-w4s4xnjv-54qd4drj"
path = sys.argv[1:]   # folder names to click into
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width":1400,"height":1000}).new_page()
    pg.goto(URL, wait_until="networkidle", timeout=90000); time.sleep(6)
    for name in path:
        pg.get_by_text(name, exact=True).first.click(); time.sleep(5)
    txt = pg.inner_text("body")
    print("\n".join(l for l in (x.strip() for x in txt.splitlines()) if l))
    b.close()
