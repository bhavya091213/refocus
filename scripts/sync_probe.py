import sys, time
from playwright.sync_api import sync_playwright
URL = "https://ln5.sync.com/dl/dc6d99c50#ra9336yd-w9u958dw-w4s4xnjv-54qd4drj"
out = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width":1400,"height":1000}).new_page()
    pg.goto(URL, wait_until="networkidle", timeout=90000)
    time.sleep(8)
    pg.screenshot(path=out + "/sync1.png")
    open(out + "/sync1.txt","w",encoding="utf-8").write(pg.inner_text("body"))
    print(pg.title()); print(pg.inner_text("body")[:3000])
    b.close()
