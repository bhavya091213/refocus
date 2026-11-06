"""Remote-controlled visible browser. Reads commands from D:/Refocus/logs/cmd.jsonl, one JSON per line:
 {"do":"goto","url":..} {"do":"click","x":..,"y":..} {"do":"click_text","text":..} {"do":"type","text":..}
 {"do":"press","key":"Enter"} {"do":"scroll","dy":400} {"do":"shot"} {"do":"quit"}
After every command it writes the screenshot to <SHOTDIR>/latest.png and a line to logs/remote_browser.log."""
import json, os, time
from playwright.sync_api import sync_playwright
SHOT = os.environ["SHOTDIR"] + "/latest.png"; CMD = "D:/Refocus/logs/cmd.jsonl"
open(CMD, "a").close(); done = len(open(CMD).read().splitlines())
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("D:/Refocus/.pw-profile", headless=False, viewport={"width":1100,"height":800},
                                               args=["--disable-blink-features=AutomationControlled"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://cloud.lambda.ai/", wait_until="domcontentloaded"); time.sleep(4)
    pg.screenshot(path=SHOT); print("ready", pg.url, flush=True)
    while True:
        lines = open(CMD).read().splitlines()
        for ln in lines[done:]:
            done += 1
            try:
                c = json.loads(ln); d = c["do"]
                if d == "goto": pg.goto(c["url"], wait_until="domcontentloaded", timeout=60000)
                elif d == "click": pg.mouse.click(c["x"], c["y"])
                elif d == "click_text": pg.get_by_text(c["text"], exact=c.get("exact", False)).first.click(timeout=10000)
                elif d == "type": pg.keyboard.type(c["text"], delay=40)
                elif d == "press": pg.keyboard.press(c["key"])
                elif d == "scroll": pg.mouse.wheel(0, c["dy"])
                elif d == "quit": ctx.close(); raise SystemExit
                time.sleep(2.5); pg.screenshot(path=SHOT)
                print("ok", d, pg.url[:90], flush=True)
            except SystemExit: raise
            except Exception as e:
                print("ERR", ln, str(e)[:200], flush=True)
                try: pg.screenshot(path=SHOT)
                except Exception: pass
        time.sleep(0.4)
