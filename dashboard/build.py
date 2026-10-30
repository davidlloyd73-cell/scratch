#!/usr/bin/env python3
"""Embed a data JSON into template.html. With no argument, builds a layout preview from generated example data."""
import json, sys, math, random, datetime as dt
from pathlib import Path

here = Path(__file__).parent
tpl = (here / "template.html").read_text()

def example():
    rnd = random.Random(7)
    today = dt.date(2026, 10, 30)
    days90 = [(today - dt.timedelta(days=89 - i)).isoformat() for i in range(90)]
    days30 = days90[-30:]
    def walk(start, drift, vol):
        v, out = start, []
        for _ in range(90):
            v *= 1 + drift + rnd.gauss(0, vol)
            out.append(v)
        return out
    spec = [("GOOG", "$", True, 314, .002, .012), ("NVDA", "$", True, 216, .003, .02), ("ASML", "$", True, 1590, .001, .016),
            ("MRNA", "$", True, 226, -.001, .03), ("NTLA", "$", False, 11.75, .0, .04), ("CRSP", "$", False, 53, .002, .035),
            ("BEAM", "$", False, 24, -.001, .035), ("LLY", "$", False, 1279, .002, .014), ("VRTX", "$", False, 488, -.001, .015),
            ("RXRX", "$", False, 3.5, .0, .05)]
    tickers = []
    for t, cur, owned, last, dr, vol in spec:
        raw = walk(last, dr, vol)
        scale = last / raw[-1]
        raw = [x * scale for x in raw]
        tickers.append({"t": t, "cur": cur, "owned": owned, "last": raw[-1], "chg": (raw[-1] / raw[-2] - 1) * 100,
                        "m30": (raw[-1] / raw[-31] - 1) * 100, "series": raw[-30:], "idx": [x / raw[0] * 100 for x in raw],
                        "asof": "29 Oct", "stale": False})
    def perday(keys, mx):
        return [dict({"d": d}, **{k: (rnd.randint(0, mx) if rnd.random() > .3 else 0) for k in keys}) for d in days30]
    icb_rows = [("NWL ICB professionals", .1), ("NCL GP website", .25), ("CLCH Harrow", .08), ("CNWL mental health", .06)]
    rows = []
    for name, p in icb_rows:
        rows.append({"name": name, "days": {d: ("changed" if rnd.random() < p else "same") for d in days30}})
    rows[0]["days"][days30[-9]] = "gap"
    return {
        "example": True, "dateLong": "Friday 30 October 2026", "built": "30 Oct 2026, 08:35",
        "kpis": [{"v": "4 of 6", "l": "panels current"}, {"v": "3", "l": "NICE items this week"}, {"v": "1", "l": "referral page changed"}, {"v": "+0.8%", "l": "owned shares, day"}],
        "shares": {"fresh": {"state": "today", "label": "Today", "note": "Example prices; the live build records the as-of date per ticker and greys anything older than one trading day."},
                   "dates": days90, "tickers": tickers,
                   "catalysts": [{"t": "NTLA", "what": "Example: BLA submission completion", "when": "Expected November"}]},
        "nice": {"fresh": {"state": "today", "label": "Today"}, "perDay": perday(["guideline", "ta", "qs"], 2),
                 "items": [{"title": "Example: Hypertension in adults (update)", "type": "Guideline", "date": "2026-10-28", "url": "https://www.nice.org.uk/guidance/published", "why": "Changes first-line choice in some groups."},
                           {"title": "Example: Tirzepatide for chronic weight management", "type": "TA", "date": "2026-10-26", "url": "https://www.nice.org.uk/guidance/published", "why": "Affects primary care prescribing criteria."}]},
        "news": {"fresh": {"state": "old", "label": "Pulse stale", "note": "Example: GPonline and BMJ current, Pulse last story two days old."},
                 "perDay": perday(["pulse", "gponline", "bmj"], 3),
                 "topics": [{"name": "Contract and funding", "n": 9}, {"name": "Workload and access", "n": 7}, {"name": "AI and digital", "n": 6}, {"name": "Prescribing", "n": 4}, {"name": "Workforce", "n": 3}],
                 "items": [{"src": "Pulse", "title": "Example: GP contract consultation opens", "url": "https://www.pulsetoday.co.uk/news/", "date": "2026-10-29"},
                           {"src": "GPonline", "title": "Example: Practices report rising online requests", "url": "https://www.gponline.com/news", "date": "2026-10-29"},
                           {"src": "BMJ", "title": "Example: Trial of ambient scribes in primary care", "url": "https://www.bmj.com/", "date": "2026-10-28"}]},
        "icb": {"fresh": {"state": "today", "label": "Today"}, "days": days30, "rows": rows,
                "today": [{"name": "NCL GP website", "url": "https://gps.northcentrallondon.icb.nhs.uk", "status": "changed", "note": "Example: new MSK referral form."},
                          {"name": "NWL ICB professionals", "url": "https://www.nwlondonicb.nhs.uk/professionals", "status": "no change", "note": "Content migrating to the NCL site."}]},
        "github": {"fresh": {"state": "old", "label": "Partly collected", "note": "Example: NHS org endpoints answered, search was rate limited."},
                   "perDay": perday(["claude", "nhs", "clin"], 2),
                   "items": [{"name": "example/mcp-fhir", "url": "https://github.com/", "stars": 1420, "line": "Example: FHIR MCP server."},
                             {"name": "nhsdigital/example-api", "url": "https://github.com/nhsdigital", "stars": 38, "line": "Example: NHS API sample, judged on substance."},
                             {"name": "example/scribe-eval", "url": "https://github.com/", "stars": 310, "line": "Example: ambient scribe benchmark."}]},
        "aidb": {"fresh": {"state": "today", "label": "Today"}, "title": "Example edition title", "idea": "Example one-idea summary in two sentences. It would carry the day's argument.",
                 "other": "Example counterpoint paraphrased from the Better Offline side, attributed, with no invented quotes.",
                 "gp": [{"title": "Example GP's Corner note", "body": "Example practical reading for UK general practice."}],
                 "claims": [{"name": "Open", "n": 14, "c": "var(--s1)"}, {"name": "Resolved, held", "n": 5, "c": "var(--s3)"}, {"name": "Resolved, failed", "n": 3, "c": "var(--s8)"}],
                 "url": "https://davids-ai-brief.netlify.app/", "src": "https://aidailybrief.ai/"},
        "archive": ["2026-10-29", "2026-10-28"],
    }

if len(sys.argv) > 1:
    data = json.loads(Path(sys.argv[1]).read_text())
else:
    data = example()
out = tpl.replace("/*DATA*/", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
dest = here / ("dashboard.html" if len(sys.argv) > 1 else "preview.html")
dest.write_text(out)
print(dest, len(out))
