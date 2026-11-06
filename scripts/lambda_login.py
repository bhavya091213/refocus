"""Open a visible browser with a persistent profile, go to Lambda Cloud sign-in, click Google.
The human completes the Google prompt (password/2FA); the session persists in .pw-profile."""
import sys, time, os
from playwright.sync_api import sync_playwright
shot = os.environ["SHOTDIR"]
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("D:/Refocus/.pw-profile", headless=False, channel="chrome" if os.path.exists(r"C:\Program Files\Google\Chrome\Application\chrome.exe") else None,
                                               viewport={"width":1280,"height":900}, args=["--disable-blink-features=AutomationControlled"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://cloud.lambda.ai/", wait_until="domcontentloaded", timeout=60000); time.sleep(5)
    print("url:", pg.url, "| title:", pg.title(), flush=True)
    pg.screenshot(path=shot + "/lam1.png")
    for label in ["Google", "Continue with Google", "Sign in with Google"]:
        loc = pg.get_by_text(label, exact=False).first
        if loc.count():
            loc.click(); time.sleep(6); print("clicked", label, "->", pg.url, flush=True); break
    pg.screenshot(path=shot + "/lam2.png")
    # wait up to 15 min for the human to finish; success = on cloud.lambda.ai dashboard (not login/google)
    for _ in range(180):
        u = pg.url
        if "cloud.lambda.ai" in u and not any(x in u for x in ("login", "signin", "accounts.google")):
            time.sleep(3); pg.screenshot(path=shot + "/lam3.png"); print("LOGGED IN:", u, flush=True); break
        time.sleep(5)
    else:
        print("timeout waiting for login", pg.url, flush=True)
    ctx.close()
