import csv, os, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

SITES = {
    "Bird Ludlam": "https://www.google.com/maps/place/?q=place_id:ChIJ_aw-6Mu52YgRaJw8qbARWXc",
}

PATTERNS = [
    re.compile(r"(\d{1,3})\s*/\s*(\d{1,3})\s*available", re.I),
    re.compile(r"(\d{1,3})\s+of\s+(\d{1,3})\s+(?:\w+\s+)?available", re.I),
    re.compile(r"kW[^\d]{0,40}?(\d{1,3})\s*/\s*(\d{1,3})"),
]

def parse(text):
    for p in PATTERNS:
        m = p.search(text)
        if m:
            a, t = int(m.group(1)), int(m.group(2))
            if 0 <= a <= t <= 200:
                return a, t
    return None

def main():
    os.makedirs("debug", exist_ok=True)
    new_file = not os.path.exists("data.csv")
    now = datetime.now(timezone.utc)
    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(locale="en-US", timezone_id="America/New_York",
                                  viewport={"width": 1400, "height": 900})
        for name, url in SITES.items():
            page = ctx.new_page()
            status, avail, total = "ok", "", ""
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_selector("text=kW", timeout=20000)
                except Exception:
                    pass
                page.wait_for_timeout(4000)
                text = page.inner_text("body")
                labels = page.eval_on_selector_all("[aria-label]", "els => els.map(e => e.getAttribute('aria-label')).join('\\n')")
                result = parse(text + "\n" + labels)
                if result:
                    avail, total = result
                else:
                    status = "not_found"
                    page.screenshot(path=f"debug/{name}.png")
                    open(f"debug/{name}.txt", "w").write(text[:3000])
            except Exception as e:
                status = "error: " + str(e)[:150]
            rows.append([now.isoformat(), now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M"),
                         name, avail, total, status])
            page.close()
        browser.close()
    with open("data.csv", "a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["polled_utc", "polled_miami", "site", "available", "total", "status"])
        w.writerows(rows)
    print(rows)

if __name__ == "__main__":
    main()
