"""Download files from the dataset's sync.com share via a real browser (the share is client-side encrypted).
usage: sync_dl.py <outdir> <folder> <file> [<file> ...]"""
import sys, time, os
from playwright.sync_api import sync_playwright
URL = "https://ln5.sync.com/dl/dc6d99c50#ra9336yd-w9u958dw-w4s4xnjv-54qd4drj"
outdir, folder, files = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(outdir, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1400,"height":1000}, accept_downloads=True)
    pg = ctx.new_page()
    pg.goto(URL, wait_until="networkidle", timeout=90000); time.sleep(6)
    pg.get_by_text(folder, exact=True).first.click(); time.sleep(6)
    for fname in files:
        dest = os.path.join(outdir, fname)
        if os.path.exists(dest):
            print("skip (exists):", fname, flush=True); continue
        row = pg.locator("tr", has=pg.get_by_text(fname, exact=True)).first
        row.scroll_into_view_if_needed()
        row.locator("button").last.click(); time.sleep(1)
        t0 = time.time()
        with pg.expect_download(timeout=0) as dl:
            pg.get_by_role("menuitem", name="Download").first.click()
        d = dl.value
        print("downloading", fname, "->", d.suggested_filename, flush=True)
        d.save_as(dest + ".part"); os.replace(dest + ".part", dest)
        sz = os.path.getsize(dest)/1e6
        print(f"done {fname} {sz:.0f} MB in {time.time()-t0:.0f}s ({sz/(time.time()-t0):.1f} MB/s)", flush=True)
    b.close()
