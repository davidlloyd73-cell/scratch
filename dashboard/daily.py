#!/usr/bin/env python3
"""Lloyd Morning Dashboard: collect every source directly, then build the page.

  python3 dashboard/daily.py collect --work W   reads the sources, writes W/collected.json and W/brief.md
  python3 dashboard/daily.py build   --work W   merges W/collected.json, W/history.json and the optional
                                                W/judged.json into W/dashboard.html and W/history.out.json

Standard library only. Nothing here guesses: a source that cannot be read is marked "none" on the page.
The model's only jobs are the judgement calls listed in brief.md, and the page builds without them.
"""
import argparse, datetime as dt, hashlib, html, json, re, subprocess, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
LONDON = ZoneInfo("Europe/London")
UA = "lloyd-dashboard/1.0 (personal daily dashboard)"
SITE_REPO = "https://github.com/davidlloyd73-cell/ai-daily-brief"
OWNED = ["GOOG", "NVDA", "ASML", "MRNA"]
ICB_PAGES = [
    ("West and North London GP site", "https://gps.westandnorthlondon.icb.nhs.uk/"),
    ("NWL ICB professionals, legacy", "https://www.nwlondonicb.nhs.uk/professionals"),
    ("CLCH Harrow", "https://clch.nhs.uk/health-professionals/harrow"),
]
GH_ORGS = [("anthropics", "claude"), ("modelcontextprotocol", "claude"), ("nhsdigital", "nhs"), ("nhsuk", "nhs"), ("nhsengland", "nhs")]
TOPICS = [
    ("Contract and funding", r"contract|fund|pay\b|budget|£|money|finance|global sum|des\b|qof"),
    ("Workload and access", r"workload|access|appointment|waiting|triage|8am|list|demand|premises|winter"),
    ("AI and digital", r"\bai\b|artificial|digital|scribe|record|app\b|online|data|software|it system"),
    ("Prescribing and safety", r"prescri|drug|medicin|mhra|safety|alert|vaccin|dose|shortage|levemir|statin|antibiotic"),
    ("Workforce", r"workforce|recruit|locum|staff|partner|trainee|arrs|physician associate|strike|bma|gmc|unemploy"),
    ("Public health", r"public health|screening|smoking|obesity|outbreak|flu\b|covid|measles|prevention"),
    ("Clinical research", r"trial|study|research|randomi|cohort|evidence"),
]


# ---------- small helpers ----------
def today():
    return dt.datetime.now(LONDON).date()


def short(d):
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    return f"{d.day} {d.strftime('%b')}"


def fetch(url, timeout=30, accept=None):
    """Return (status, text). Never raises; status 0 means no connection."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept or "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # network refusal, timeout, TLS
        return 0, str(e)


def page_lines(raw):
    """Readable text of a page's main content, one line per text node."""
    t = re.sub(r"(?is)<(script|style|nav|header|footer|noscript|svg)\b.*?</\1>", " ", raw)
    m = re.search(r"(?is)<main\b.*?</main>", t)
    if m:
        t = m.group(0)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    out = []
    for line in t.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) > 2:
            out.append(line[:240])
    return out


def last_us_trading_day(d):
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def run(cmd, cwd=None, timeout=180):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


# ---------- collectors: each returns a dict and never raises ----------
WMO_FROM_MET = [("thunder", 95), ("heavysnow", 75), ("lightsnow", 71), ("snow", 73), ("sleet", 67), ("heavyrainshowers", 82),
                ("lightrainshowers", 80), ("rainshowers", 81), ("heavyrain", 65), ("lightrain", 61), ("rain", 63),
                ("drizzle", 51), ("fog", 45), ("partlycloudy", 2), ("fair", 1), ("clearsky", 0), ("cloudy", 3)]


def met_code(sym):
    for key, code in WMO_FROM_MET:
        if key in (sym or ""):
            return code
    return 3


def wet(code, mm):
    """A day with real rainfall should not show a dry midday symbol."""
    return code if code >= 45 or mm < 1 else (63 if mm >= 5 else 61)


def weather_open_meteo():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=51.58&longitude=-0.34"
           "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
           "&wind_speed_unit=mph&timezone=Europe%2FLondon&forecast_days=6")
    st, body = fetch(url)
    if st != 200:
        return None, f"Open-Meteo answered {st}"
    j = json.loads(body)
    c, d = j["current"], j["daily"]
    days = [{"d": d["time"][i], "max": d["temperature_2m_max"][i], "min": d["temperature_2m_min"][i],
             "pop": d["precipitation_probability_max"][i] or 0, "code": d["weather_code"][i]} for i in range(len(d["time"]))]
    return {"now": {"t": c["temperature_2m"], "feels": c["apparent_temperature"], "code": c["weather_code"],
                    "wind": c["wind_speed_10m"]}, "days": days[:6]}, "Open-Meteo forecast"


def weather_met_no():
    st, body = fetch("https://api.met.no/weatherapi/locationforecast/2.0/complete?lat=51.58&lon=-0.34")
    if st != 200:
        return None, f"MET Norway answered {st}"
    ts = json.loads(body)["properties"]["timeseries"]
    first = ts[0]["data"]
    det = first["instant"]["details"]
    t, wind_ms = det["air_temperature"], det.get("wind_speed", 0)
    kmh = wind_ms * 3.6
    feels = t if (t > 10 or kmh < 4.8) else 13.12 + 0.6215 * t - 11.37 * kmh ** 0.16 + 0.3965 * t * kmh ** 0.16
    sym = (first.get("next_1_hours") or first.get("next_6_hours") or {}).get("summary", {}).get("symbol_code", "")
    by = {}
    for e in ts:
        when = dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(LONDON)
        b = by.setdefault(when.date().isoformat(), {"temps": [], "mm": 0.0, "sym": None})
        b["temps"].append(e["data"]["instant"]["details"]["air_temperature"])
        for k in ("next_1_hours", "next_6_hours"):
            blk = e["data"].get(k)
            if not blk:
                continue
            b["mm"] += blk.get("details", {}).get("precipitation_amount", 0) or 0  # MET Norway gives no rain probability for the UK
            if b["sym"] is None or 10 <= when.hour <= 14:
                b["sym"] = blk.get("summary", {}).get("symbol_code") or b["sym"]
            break
    days = [{"d": d, "max": round(max(v["temps"]), 1), "min": round(min(v["temps"]), 1), "mm": round(v["mm"], 1),
             "code": wet(met_code(v["sym"]), v["mm"])} for d, v in sorted(by.items())][:6]
    return {"now": {"t": t, "feels": round(feels, 1), "code": met_code(sym), "wind": round(wind_ms * 2.23694, 1)},
            "days": days}, "MET Norway forecast"


def collect_weather():
    for fn in (weather_open_meteo, weather_met_no):
        try:
            w, src = fn()
        except Exception as e:
            w, src = None, f"{fn.__name__} failed: {e}"
        if w and w["days"]:
            return {"place": "Harrow", "fresh": {"state": "today", "label": "Today", "note": src}, **w}
    return None


def clone_site(work):
    dest = work / "adb"
    if dest.exists():
        rc, out = run(["git", "pull", "-q", "--depth", "1"], cwd=dest)
    else:
        rc, out = run(["git", "clone", "-q", "--depth", "1", "--single-branch", "--filter=blob:none", "--sparse", SITE_REPO, str(dest)], timeout=300)
        if rc == 0:
            rc, out = run(["git", "sparse-checkout", "set", "a", "data", "rush/src"], cwd=dest)
    return (dest if rc == 0 else None), out


def collect_shares(site):
    try:
        p = json.loads((site / "data" / "prices.json").read_text())
        assert p["market_date"] and p["expected_asof"] and len(p["dates"]) >= 60
        tick = p["tickers"]
        for x in tick:
            assert all(k in x for k in ("t", "last", "chg", "m30", "asof", "stale")) and len(x["series"]) >= 20
            if x["t"] in OWNED:
                assert len(x["idx"]) == len(p["dates"])
    except Exception as e:
        return {"fresh": {"state": "none", "label": "Not collected today", "note": f"The Mac mini prices file is missing or invalid ({type(e).__name__})."},
                "dates": [], "tickers": [], "catalysts": []}, None
    for x in tick:
        x["src"] = "Mac prices file"
    md = p["market_date"]
    current = md >= last_us_trading_day(today()).isoformat() and not p.get("market_stale")
    note = f"Read from the Mac mini prices file, generated {p['generated'][:10]}, market date {short(md)}."
    if p.get("errors"):
        note += " Fetch errors for: " + ", ".join(p["errors"]) + "."
    return {"fresh": {"state": "today" if current else "old", "label": f"Prices to {short(md)}", "note": note},
            "dates": p["dates"], "tickers": tick, "catalysts": []}, md


def md_section(text, heading):
    m = re.search(r"(?ms)^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)", text)
    return m.group(1).strip() if m else ""


def collect_aidb(site):
    eds = sorted(p.stem for p in (site / "a").glob("20??-??-??.md"))
    if not eds:
        return {"fresh": {"state": "none", "label": "Not collected today", "note": "No editions found in the website repository."}, "gp": [], "claims": []}, None
    newest = eds[-1]
    text = (site / "a" / f"{newest}.md").read_text()
    title = (re.search(r"(?m)^## (.+)$", text) or [None, ""])[1].strip()
    idea_sec = md_section(text, "The One Idea")
    idea = " ".join(l for l in idea_sec.splitlines() if l.strip() and not l.startswith("#"))
    other_lines = [l for l in md_section(text, "The Other Side").splitlines() if l.strip() and not l.startswith("Source:")]
    gp = []
    for m in re.finditer(r"(?ms)^### (.+?)\n+(.*?)(?=^### |\Z)", md_section(text, "GP's Corner")):
        gp.append({"title": m.group(1).strip(), "body": " ".join(m.group(2).split())[:400]})
    claims = {"open": 0, "held": 0, "failed": 0}
    try:
        for c in json.loads((site / "claims.json").read_text())["claims"] if (site / "claims.json").exists() else []:
            s = c.get("status", "open")
            claims["held" if s in ("vindicated", "held") else "failed" if s in ("failed", "refuted", "wrong") else "open"] += 1
    except Exception:
        pass
    t = today()
    floor = t - dt.timedelta(days=1)
    while floor.weekday() >= 5:  # the podcast is quiet at weekends
        floor -= dt.timedelta(days=1)
    fresh_ok = newest >= floor.isoformat()
    age = (t - dt.date.fromisoformat(newest)).days
    fresh = ({"state": "today", "label": f"Edition of {short(newest)}"} if fresh_ok else
             {"state": "old", "label": f"Latest edition {short(newest)}",
              "note": f"The newest edition in the website repository is {age} days old. The cloud task that builds it has not published a newer one."})
    src = (re.search(r"(?m)^source:\s*(\S+)", text) or [None, ""])[1]
    return {"fresh": fresh, "title": title, "idea": idea[:700], "other": " ".join(other_lines)[:600], "gp": gp[:3],
            "claims": [{"name": "Open", "n": claims["open"], "c": "var(--s1)"}, {"name": "Resolved, held", "n": claims["held"], "c": "var(--s3)"},
                       {"name": "Resolved, failed", "n": claims["failed"], "c": "var(--s8)"}],
            "url": "https://davids-ai-brief.netlify.app/", "src": src, "_claims": claims}, newest


def collect_rush(site):
    files = sorted((site / "rush" / "src").glob("morning-rush-20??-??-??.md"))
    if not files:
        return None
    newest = files[-1]
    m = re.search(r"Issue (\d+)", newest.read_text()[:600])
    return {"date": newest.stem[-10:], "issue": int(m.group(1)) if m else None}


def collect_nice():
    st, body = fetch("https://www.nice.org.uk/guidance/published")
    m = re.search(r'(?s)<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', body) if st == 200 else None
    if not m:
        return {"ok": False, "why": f"NICE answered {st}", "docs": []}
    docs = []
    for x in json.loads(m.group(1))["props"]["pageProps"]["results"]["documents"]:
        kinds = " ".join(x.get("niceGuidanceType") or []) + " " + " ".join(x.get("niceDocType") or [])
        typ = ("TA" if "Technology appraisal" in kinds else "Quality standard" if "Quality standard" in kinds else
               "Guideline" if "guideline" in kinds.lower() else (x.get("niceGuidanceType") or ["Guidance"])[0])
        docs.append({"ref": x.get("guidanceRef") or "", "title": x.get("titleNoHtml") or x.get("title") or "", "type": typ,
                     "date": (x.get("lastUpdated") or x.get("publicationDate") or "")[:10],
                     "new": (x.get("publicationDate") or "")[:10] == (x.get("lastUpdated") or "")[:10],
                     "url": x.get("url") or "https://www.nice.org.uk/guidance/published"})
    return {"ok": True, "docs": docs}


def collect_pulse():
    st, body = fetch("https://www.pulsetoday.co.uk/feed/")
    if st != 200:
        return {"ok": False, "why": f"Pulse feed answered {st}", "items": []}
    items = []
    for it in re.findall(r"(?s)<item>(.*?)</item>", body):
        def g(tag):
            m = re.search(rf"(?s)<{tag}>(.*?)</{tag}>", it)
            return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip() if m else ""
        try:
            d = dt.datetime.strptime(g("pubDate"), "%a, %d %b %Y %H:%M:%S %z").astimezone(LONDON).date().isoformat()
        except ValueError:
            continue
        link = g("link")
        if link.startswith("https://www.pulsetoday.co.uk/"):
            items.append({"src": "Pulse", "title": g("title"), "url": link, "date": d, "news": "/news/" in link})
    return {"ok": True, "items": items}


def collect_icb(old_text):
    out = []
    for name, url in ICB_PAGES:
        st, body = fetch(url)
        if st != 200:
            out.append({"name": name, "url": url, "status": "gap", "note": f"Could not be read today (answered {st}).", "lines": None, "added": []})
            continue
        lines = page_lines(body)[:200]
        before = old_text.get(name)
        added = [l for l in lines if l not in set(before)] if before else []
        added = [l for l in added if len(l) > 25]
        out.append({"name": name, "url": url, "status": "changed" if added else "same",
                    "note": ("New on the page: " + "; ".join(added[:2])[:260]) if added else
                            ("First direct reading, baseline taken." if before is None else "No change since the last reading."),
                    "lines": lines, "added": added[:12]})
    return out


def collect_github(shown_yesterday):
    repos, errs = {}, []
    for org, theme in GH_ORGS:
        q = urllib.parse.urlencode({"q": f"org:{org} fork:false archived:false", "sort": "updated", "order": "desc", "per_page": 12})
        st, body = fetch("https://api.github.com/search/repositories?" + q, accept="application/vnd.github+json")
        if st != 200:
            errs.append(f"{org} ({st})")
            continue
        for r in json.loads(body).get("items", []):
            repos[r["full_name"]] = {"name": r["full_name"], "url": r["html_url"], "stars": r["stargazers_count"], "theme": theme,
                                     "desc": (r.get("description") or "").strip(), "pushed": r["pushed_at"][:10], "created": r["created_at"][:10]}
    cutoff = (today() - dt.timedelta(days=3)).isoformat()
    picks = []
    for theme, n in (("claude", 3), ("nhs", 3)):
        pool = [r for r in repos.values() if r["theme"] == theme and r["pushed"] >= cutoff and r["name"] not in shown_yesterday
                and (r["desc"] or r["stars"] >= 50) and not r["name"].lower().endswith("/.github")]
        pool.sort(key=lambda r: (r["created"] >= cutoff, r["pushed"], r["stars"]), reverse=True)
        picks += pool[:n]
    for r in picks:
        line = (r["desc"] or "No description published.").rstrip(".") + f". Pushed {short(r['pushed'])}."
        if r["created"] >= cutoff:
            line += " New repository."
        if r["theme"] == "nhs" and r["stars"] < 20:
            line += " Low stars, shown because it is NHS work."
        r["line"] = line
    newc = {"claude": 0, "nhs": 0, "clin": 0}
    for r in repos.values():
        if r["created"] >= (today() - dt.timedelta(days=1)).isoformat():
            newc[r["theme"]] += 1
    return {"ok": bool(repos), "errors": errs, "picks": picks, "new": newc, "seen": len(repos)}


# ---------- collect ----------
def cmd_collect(work):
    work.mkdir(parents=True, exist_ok=True)
    hist = json.loads((work / "history.json").read_text()) if (work / "history.json").exists() else {}
    t = today()
    col = {"date": t.isoformat(), "collected_at": dt.datetime.now(LONDON).strftime("%H:%M"), "problems": []}

    col["weather"] = collect_weather()
    if not col["weather"]:
        col["problems"].append("weather: neither forecast service answered")

    site, err = clone_site(work)
    if site:
        col["shares"], col["market_date"] = collect_shares(site)
        col["aidb"], col["aidb_date"] = collect_aidb(site)
        col["rush"] = collect_rush(site)
    else:
        col["problems"].append("website repository could not be cloned: " + err[-200:])
        col["shares"], col["market_date"] = {"fresh": {"state": "none", "label": "Not collected today", "note": "Website repository unreachable."}, "dates": [], "tickers": [], "catalysts": []}, None
        col["aidb"], col["aidb_date"] = {"fresh": {"state": "none", "label": "Not collected today", "note": "Website repository unreachable."}, "gp": [], "claims": []}, None
        col["rush"] = None

    col["nice"] = collect_nice()
    col["pulse"] = collect_pulse()
    col["icb"] = collect_icb((hist.get("icb") or {}).get("text") or {})
    ydays = sorted((hist.get("github") or {}).keys())
    shown = set(((hist.get("github") or {}).get(ydays[-1], {}).get("stars") or {}).keys()) if ydays and ydays[-1] != t.isoformat() else set()
    col["github"] = collect_github(shown)
    for k in ("nice", "pulse", "github"):
        if not col[k]["ok"]:
            col["problems"].append(f"{k}: " + (col[k].get("why") or ", ".join(col[k].get("errors", []))))
    (work / "collected.json").write_text(json.dumps(col, indent=1))

    # brief for the model: only the judgement calls
    week = (t - dt.timedelta(days=7)).isoformat()
    b = [f"# Dashboard brief for {t.isoformat()}", "",
         "Everything below was read directly from its source a moment ago. The page builds without you; your job is only",
         "the optional judgement in judged.json (see the task prompt for its shape).", ""]
    b.append("## Problems")
    b += [f"- {p}" for p in col["problems"]] or ["- none"]
    b += ["", "## NICE: documents updated in the last 7 days (give a `why` for the ones a Harrow GP should know about)"]
    b += [f"- {d['ref']} | {d['type']} | {d['date']} | {'new' if d['new'] else 'updated'} | {d['title']}" for d in col["nice"]["docs"] if d["date"] >= week] or ["- none"]
    b += ["", "## Referral pages that changed (write one short practical note per changed page)"]
    ch = [p for p in col["icb"] if p["status"] == "changed"]
    for p in ch:
        b.append(f"### {p['name']}")
        b += [f"- {l}" for l in p["added"]]
    if not ch:
        b.append("- none changed")
    meta = hist.get("news_meta") or {}
    b += ["", "## Newsletters", f"- Last BMJ newsletter used: {meta.get('bmj_last', 'never')}", f"- Last NEJM email used: {meta.get('nejm_last', 'never')}",
          "- Pulse comes from its feed and needs nothing from you."]
    (work / "brief.md").write_text("\n".join(b) + "\n")
    print(f"collected for {t}: weather={'yes' if col['weather'] else 'NO'} shares={col['shares']['fresh']['state']} "
          f"aidb={col.get('aidb_date')} rush={col.get('rush')} nice={len(col['nice']['docs'])} pulse={len(col['pulse']['items'])} "
          f"icb={[p['status'] for p in col['icb']]} github={len(col['github']['picks'])} problems={len(col['problems'])}")


# ---------- build ----------
def topic_of(title):
    low = title.lower()
    for name, rx in TOPICS:
        if re.search(rx, low):
            return name
    return "Other"


def cmd_build(work):
    col = json.loads((work / "collected.json").read_text())
    hist = json.loads((work / "history.json").read_text()) if (work / "history.json").exists() else {}
    judged = {}
    if (work / "judged.json").exists():
        try:
            judged = json.loads((work / "judged.json").read_text())
        except Exception as e:
            col["problems"].append(f"judged.json was not valid JSON and was ignored ({e})")
    t = dt.date.fromisoformat(col["date"])
    T = t.isoformat()
    days30 = [(t - dt.timedelta(days=29 - i)).isoformat() for i in range(30)]
    days10 = days30[-10:]
    for k in ("shares", "github", "nice", "news", "health"):
        hist.setdefault(k, {})
    hist.setdefault("icb", {}).setdefault("days", {})
    hist["icb"].setdefault("summaries", {})
    hist["icb"].setdefault("text", {})
    hist.setdefault("news_meta", {})

    # shares
    shares = col["shares"]
    shares["catalysts"] = [c for c in judged.get("catalysts", []) if all(k in c for k in ("t", "what", "when"))][:4]
    if col.get("market_date"):
        hist["shares"][col["market_date"]] = {x["t"]: {"last": x["last"], "chg": x["chg"], "asof": col["market_date"]} for x in shares["tickers"]}

    # NICE
    nc = col["nice"]
    for d in nc["docs"]:
        key = {"Guideline": "guideline", "TA": "ta", "Quality standard": "qs"}.get(d["type"])
        if key and d["date"] in days30:
            hist["nice"].setdefault(d["date"], {"guideline": 0, "ta": 0, "qs": 0})
    for day in {d["date"] for d in nc["docs"] if d["date"] in days30}:
        cnt = {"guideline": 0, "ta": 0, "qs": 0}
        for d in nc["docs"]:
            key = {"Guideline": "guideline", "TA": "ta", "Quality standard": "qs"}.get(d["type"])
            if key and d["date"] == day:
                cnt[key] += 1
        old = hist["nice"].get(day, cnt)
        hist["nice"][day] = {k: max(cnt[k], old.get(k, 0)) for k in cnt}
    week = (t - dt.timedelta(days=7)).isoformat()
    whys, drop = judged.get("nice_why", {}), set(judged.get("nice_drop", []))
    n_items = [{"title": f"{d['ref']}: {d['title']}" if d["ref"] else d["title"], "type": d["type"], "date": d["date"], "url": d["url"],
                "why": whys.get(d["ref"]) or ("Newly published." if d["new"] else "Existing guidance, updated.")}
               for d in nc["docs"] if d["date"] >= week and d["ref"] not in drop][:6]
    nice = {"fresh": ({"state": "today", "label": "Today", "note": "Read directly from the NICE published list." + ("" if n_items else " Nothing new in the last seven days.")}
                      if nc["ok"] else {"state": "none", "label": "Not collected today", "note": f"The NICE list could not be read ({nc.get('why')})."}),
            "perDay": [dict({"d": d}, **hist["nice"].get(d, {"guideline": 0, "ta": 0, "qs": 0})) for d in days30], "items": n_items}

    # news: Pulse from its feed, BMJ and NEJM carried from newsletters
    extra = [x for x in (hist.get("news_extra") or []) + judged.get("news_extra", [])
             if x.get("src") in ("BMJ", "NEJM", "GPonline") and x.get("title") and re.fullmatch(r"\d{4}-\d\d-\d\d", x.get("date", ""))]
    seen, keep = set(), []
    for x in sorted(extra, key=lambda x: x["date"], reverse=True):
        if x["title"] not in seen and x["date"] >= (t - dt.timedelta(days=9)).isoformat():
            seen.add(x["title"])
            keep.append({"src": x["src"], "title": x["title"], "date": x["date"]})
    hist["news_extra"] = keep
    links = {"BMJ": "https://www.bmj.com/news", "NEJM": "https://www.nejm.org/toc/nejm/medical-journal", "GPonline": "https://www.gponline.com/news"}
    pulse = col["pulse"]["items"]
    recent = (t - dt.timedelta(days=3)).isoformat()
    p_pick = [x for x in pulse if x["news"] and x["date"] >= recent][:4] or [x for x in pulse if x["date"] >= recent][:3]
    items = [{k: x[k] for k in ("src", "title", "url", "date")} for x in p_pick]
    items += [dict(x, url=links[x["src"]]) for x in [k for k in keep if k["src"] == "BMJ"][:3] + [k for k in keep if k["src"] == "NEJM"][:2]]
    items.sort(key=lambda x: x["date"], reverse=True)
    for src in ("bmj", "nejm"):
        dates = [x["date"] for x in keep if x["src"].lower() == src]
        if dates:
            hist["news_meta"][f"{src}_last"] = max(dates)
    if pulse:
        hist["news_meta"]["pulse_last"] = max(x["date"] for x in pulse)
    per = {d: {"pulse": 0, "gponline": 0, "bmj": 0, "nejm": 0} for d in days10}
    for x in pulse:
        if x["date"] in per and x["news"]:
            per[x["date"]]["pulse"] += 1
    for x in keep:
        if x["date"] in per:
            per[x["date"]][x["src"].lower()] += 1
    for d in days10:
        old = hist["news"].get(d, {})
        for k in ("bmj", "nejm"):  # newsletters age out of the carried list, so keep the days already counted
            per[d][k] = max(per[d][k], old.get(k, 0))
        hist["news"][d] = per[d]
    tc = {}
    for x in items:
        tc[topic_of(x["title"])] = tc.get(topic_of(x["title"]), 0) + 1
    shown_bmj = [x["date"] for x in items if x["src"] == "BMJ"]
    pulse_ok = bool(p_pick)
    label = ("Pulse " + short(max(x["date"] for x in p_pick)) if pulse_ok else "Pulse not collected") + (f", BMJ {short(max(shown_bmj))}" if shown_bmj else "")
    news = {"fresh": {"state": "today" if pulse_ok else "old" if items else "none", "label": label,
                      "note": "Pulse is read from its own news feed. BMJ and NEJM items appear when the task can read their email newsletters. GPonline refuses automated readers and is no longer followed."},
            "perDay": [dict({"d": d}, **per[d]) for d in days10],
            "topics": [{"name": n, "n": tc.get(n, 0)} for n, _ in TOPICS] + [{"name": "Other", "n": tc.get("Other", 0)}], "items": items}

    # referral pages
    notes = judged.get("icb_notes", {})
    hist["icb"]["days"][T] = {}
    today_rows = []
    for p in col["icb"]:
        hist["icb"]["days"][T][p["name"]] = p["status"]
        if p["lines"] is not None:
            hist["icb"]["text"][p["name"]] = p["lines"]
        stored = hist["icb"]["summaries"].get(p["name"])
        note = notes.get(p["name"]) or (stored if p["status"] == "same" and stored else p["note"])
        if p["status"] == "changed" or not stored:
            hist["icb"]["summaries"][p["name"]] = note
        today_rows.append({"name": p["name"], "url": p["url"], "status": p["status"], "note": note})
    names = [p["name"] for p in col["icb"]]
    for stale in [k for k in hist["icb"]["text"] if k not in names]:
        del hist["icb"]["text"][stale]
    gaps, changed = [p for p in col["icb"] if p["status"] == "gap"], [p for p in col["icb"] if p["status"] == "changed"]
    icb = {"fresh": {"state": "none" if len(gaps) == len(names) else "old" if gaps else "today", "label": "Today" if not gaps else f"{len(gaps)} page(s) unreachable",
                     "note": (f"{len(changed)} page(s) changed since the last reading: " + ", ".join(p["name"] for p in changed) + ".") if changed else "No referral page changed since the last reading."},
           "days": days30, "rows": [{"name": n, "days": {d: hist["icb"]["days"].get(d, {}).get(n) for d in days30 if hist["icb"]["days"].get(d, {}).get(n)}} for n in names],
           "today": today_rows}

    # GitHub
    gh = col["github"]
    hist["github"][T] = {"stars": {r["name"]: r["stars"] for r in gh["picks"]}, "newByTheme": gh["new"]}
    github = {"fresh": ({"state": "today", "label": "Today", "note": f"Read live from GitHub: {gh['seen']} recently active repositories checked."
                         + (" Could not read: " + ", ".join(gh["errors"]) + "." if gh["errors"] else "")}
                        if gh["ok"] else {"state": "none", "label": "Not collected today", "note": "GitHub could not be read: " + ", ".join(gh["errors"])}),
              "perDay": [dict({"d": d}, **hist["github"].get(d, {}).get("newByTheme", {"claude": 0, "nhs": 0, "clin": 0})) for d in days10],
              "items": [{k: r[k] for k in ("name", "url", "stars", "line")} for r in gh["picks"]]}

    # AI brief
    aidb = col["aidb"]
    if aidb.get("_claims"):
        hist["claims"] = aidb.pop("_claims")

    # health: judged only by output that can be seen
    rush, md, ad = col.get("rush"), col.get("market_date"), col.get("aidb_date")
    rows = [{"name": "Daily dashboard builder", "where": "cloud", "due": "08:35 daily", "status": "yes", "lastOutput": T, "lastLabel": "This page",
             "run": col["collected_at"], "note": "Sources read directly at " + col["collected_at"] + "."},
            {"name": "Share prices file", "where": "Mac mini", "due": "06:45 daily", "status": "yes" if shares["fresh"]["state"] == "today" else "no",
             "lastOutput": md or "", "lastLabel": f"Prices to {short(md)}" if md else "", "run": "", "note": "Current to the last US trading day." if shares["fresh"]["state"] == "today" else "No file for the last US trading day."},
            {"name": "Morning Rush", "where": "cloud", "due": "06:00 daily", "status": "yes" if rush and rush["date"] == T else "no",
             "lastOutput": rush["date"] if rush else "", "lastLabel": f"Issue {rush['issue']}" if rush else "", "run": "",
             "note": (f"Issue {rush['issue']} is on the website." if rush and rush["date"] == T else f"Newest issue on the website is dated {short(rush['date'])}." if rush else "Website repository unreachable.")},
            {"name": "AI daily brief site", "where": "cloud", "due": "06:20 daily", "status": "yes" if aidb["fresh"]["state"] == "today" else "no",
             "lastOutput": ad or "", "lastLabel": f"Edition of {short(ad)}" if ad else "", "run": "",
             "note": "Up to date." if aidb["fresh"]["state"] == "today" else "No edition for the last podcast day yet; the source publishes some hours after it airs."},
            {"name": "Daily OSA brief", "where": "Mac mini", "due": "07:10 daily", "status": "unverified", "lastOutput": "", "lastLabel": "", "run": "",
             "note": "Private by design; its output is never read here."}]
    hist["health"][T] = {r["name"]: r["status"] for r in rows}
    checkable = [r for r in rows if r["status"] in ("yes", "no")]
    ok = sum(r["status"] == "yes" for r in checkable)
    health = {"fresh": {"state": "today" if ok == len(checkable) else "old" if ok else "none", "label": f"{ok} of {len(checkable)} published",
                        "note": "Each task is judged by its published output, read directly this morning." + (" Problems: " + "; ".join(col["problems"]) + "." if col["problems"] else "")},
              "rows": rows}

    weather = col.get("weather")
    panels = [weather["fresh"]["state"] if weather else "none", shares["fresh"]["state"], nice["fresh"]["state"], news["fresh"]["state"],
              icb["fresh"]["state"], github["fresh"]["state"], aidb["fresh"]["state"]]
    cur = sum(s == "today" for s in panels)
    # every earlier build was archived by the run that replaced it, so earlier build dates are the archive list
    prev = sorted(d for d in hist["health"] if d < T)
    hist["archive"] = sorted(set(hist.get("archive") or prev) | set(prev[-1:]))[-30:]
    archive = sorted(hist["archive"], reverse=True)
    # archive the page being replaced, but only if it is from an earlier day (a same-day rerun archives nothing)
    files = {"data/history.json": str(work / "history.out.json")}
    live = work / "live.html"
    if live.exists():
        m = re.search(r'"built":"(\d{1,2} \w{3} \d{4}),', live.read_text())
        try:
            live_date = dt.datetime.strptime(m.group(1), "%d %b %Y").date().isoformat() if m else None
        except ValueError:
            live_date = None
        if live_date and live_date < T:
            (work / "archive").mkdir(exist_ok=True)
            (work / "archive" / f"{live_date}.html").write_text(live.read_text())
            files[f"archive/{live_date}.html"] = str(work / "archive" / f"{live_date}.html")
            hist["archive"] = sorted(set(hist["archive"]) | {live_date})[-30:]
            archive = sorted(hist["archive"], reverse=True)
    (work / "publish_files.json").write_text(json.dumps(files, indent=1))
    data = {"dateLong": f"{t.strftime('%A')} {t.day} {t.strftime('%B %Y')}", "built": f"{t.day} {t.strftime('%b %Y')}, {col['collected_at']}",
            "kpis": [{"v": f"{cur} of {len(panels)}", "l": "panels current", "s": "today" if cur == len(panels) else "old" if cur else "none"},
                     {"v": f"{ok} of {len(checkable)}", "l": "tasks published", "s": health["fresh"]["state"]},
                     {"v": shares["fresh"]["label"], "l": "shares file", "s": shares["fresh"]["state"]},
                     {"v": short(ad) if ad else "None", "l": "latest AI brief edition", "s": aidb["fresh"]["state"]}],
            "health": health, "shares": shares, "nice": nice, "news": news, "icb": icb, "github": github, "aidb": aidb, "archive": archive}
    if weather:
        data["weather"] = weather

    # prune history to 60 days so the file stays small
    floor = (t - dt.timedelta(days=60)).isoformat()
    for k in ("shares", "github", "nice", "news", "health"):
        hist[k] = {d: v for d, v in hist[k].items() if d >= floor}
    hist["icb"]["days"] = {d: v for d, v in hist["icb"]["days"].items() if d >= floor}

    tpl = (HERE / "template.html").read_text()
    assert tpl.count("/*DATA*/") == 1, "template marker missing"
    (work / "dashboard.html").write_text(tpl.replace("/*DATA*/", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))
    (work / "history.out.json").write_text(json.dumps(hist, separators=(",", ":")))
    (work / "data.json").write_text(json.dumps(data, indent=1))
    failing = [r["name"] for r in rows if r["status"] == "no"]
    print(f"built {work / 'dashboard.html'}: {cur} of {len(panels)} panels current, {ok} of {len(checkable)} tasks published"
          + (f"; NOT PUBLISHED TODAY: {', '.join(failing)}" if failing else ""))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["collect", "build"])
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    (cmd_collect if a.mode == "collect" else cmd_build)(Path(a.work))
