#!/usr/bin/env python3
"""Fetch daily share closes from Alpha Vantage and publish data/prices.json to the website repo.

Runs on a Mac with its own internet connection (the cloud dashboard task shares a network
address that Alpha Vantage throttles). No third-party packages. The key is read from
$ALPHAVANTAGE_KEY or ~/.config/lloyd-prices/alphavantage.key and is never printed.

Usage:
  python3 fetch_prices.py              fetch, write, commit and push, then verify the push
  python3 fetch_prices.py --dry-run    fetch and print a summary, change nothing
  python3 fetch_prices.py --notify     as the first form, and show a Mac notification on failure

Exit codes: 0 ok (or nothing changed), 2 nothing could be fetched, 3 push not verified.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# (ticker, owned). Owned names get the indexed 90-day line chart on the dashboard.
TICKERS = [("GOOG", True), ("NVDA", True), ("ASML", True), ("MRNA", True),
           ("NTLA", False), ("CRSP", False), ("BEAM", False), ("VRTX", False),
           ("RXRX", False), ("LLY", False)]
REPO_URL = "https://github.com/davidlloyd73-cell/ai-daily-brief"
DEFAULT_CLONE = Path.home() / "Code" / "ai-daily-brief-data"
KEY_FILE = Path.home() / ".config" / "lloyd-prices" / "alphavantage.key"
OUT_REL = "data/prices.json"
SPACING_SECONDS = 15      # free tier allows only a few requests a minute
MIN_ROWS = 31             # need 30 trading days back for the 30-day change
CHART_DAYS = 90


class FetchError(Exception):
    pass


def read_key():
    key = os.environ.get("ALPHAVANTAGE_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    if not key:
        sys.exit(f"No Alpha Vantage key. Put it in {KEY_FILE} or set ALPHAVANTAGE_KEY.")
    return key


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lloyd-prices/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_series(ticker, key, get_json=http_json):
    """Return [(date_str, close_float), ...] newest first, or raise FetchError."""
    q = urllib.parse.urlencode({"function": "TIME_SERIES_DAILY", "symbol": ticker,
                                "outputsize": "compact", "apikey": key})
    try:
        payload = get_json("https://www.alphavantage.co/query?" + q)
    except Exception as e:  # network errors must not leak the key in the URL
        raise FetchError(f"{type(e).__name__} while fetching {ticker}") from None
    rows = payload.get("Time Series (Daily)")
    if not rows:
        msg = payload.get("Information") or payload.get("Note") or payload.get("Error Message") or "no data"
        raise FetchError(str(msg)[:160])
    out = []
    for d, v in rows.items():
        try:
            close = float(v["4. close"])
        except (KeyError, TypeError, ValueError):
            raise FetchError(f"{ticker}: unreadable close on {d}") from None
        if not close > 0:
            raise FetchError(f"{ticker}: non-positive close on {d}")
        out.append((d, close))
    out.sort(key=lambda x: x[0], reverse=True)
    if len(out) < MIN_ROWS:
        raise FetchError(f"{ticker}: only {len(out)} rows")
    return out


def prev_weekday(day):
    d = day - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def short_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')}"


def entry_from_series(ticker, owned, series):
    last, prev, ago30 = series[0][1], series[1][1], series[30][1]
    return {
        "t": ticker, "cur": "$", "owned": owned,
        "last": round(last, 2),
        "chg": round((last / prev - 1) * 100, 2),
        "m30": round((last / ago30 - 1) * 100, 1),
        "series": [round(c, 2) for _, c in reversed(series[:30])],
        "asof_date": series[0][0],
        "closes": {d: c for d, c in series[:CHART_DAYS]},   # trimmed before saving
    }


def build_document(results, previous, now, errors):
    """results: {ticker: (owned, series)}. previous: last saved document or None."""
    entries = {}
    for t, (owned, series) in results.items():
        entries[t] = entry_from_series(t, owned, series)
    if previous:   # keep an old entry for any ticker that failed today, flagged by its own date
        for old in previous.get("tickers", []):
            if old["t"] not in entries:
                old = dict(old)
                old["closes"] = {}
                entries[old["t"]] = old
    if not entries:
        return None
    market_date = max(e["asof_date"] for e in entries.values())
    # chart dates: the newest 90 dates from the ticker with the most history
    base = max((e for e in entries.values() if e["closes"]), key=lambda e: len(e["closes"]), default=None)
    dates = sorted(base["closes"])[-CHART_DAYS:] if base else []
    tickers = []
    for t, owned in TICKERS:
        e = entries.get(t)
        if not e:
            continue
        idx = []
        if e["owned"] and e["closes"] and dates:
            vals = [e["closes"].get(d) for d in dates]
            first = next((v for v in vals if v is not None), None)
            idx = [round(v / first * 100, 2) if (v is not None and first) else None for v in vals]
        elif e["owned"]:
            idx = e.get("idx", [])
        tickers.append({
            "t": t, "cur": "$", "owned": owned, "last": e["last"], "chg": e["chg"], "m30": e["m30"],
            "series": e["series"], "idx": idx,
            "asof": short_date(e["asof_date"]), "asof_date": e["asof_date"],
            "stale": e["asof_date"] < market_date,
        })
    expected = prev_weekday(now.date()).isoformat()
    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Alpha Vantage TIME_SERIES_DAILY (unadjusted closes)",
        "market_date": market_date, "expected_asof": expected,
        "market_stale": market_date < expected,
        "dates": dates, "tickers": tickers, "errors": errors,
    }


def same_ignoring_generated(a, b):
    if not a or not b:
        return False
    x, y = dict(a), dict(b)
    x.pop("generated", None)
    y.pop("generated", None)
    return x == y


def run(cmd, cwd, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def ensure_clone(clone):
    if (clone / ".git").exists():
        run(["git", "pull", "--ff-only", "-q", "origin", "main"], clone)
        return
    clone.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", REPO_URL, str(clone)], clone.parent)
    run(["git", "sparse-checkout", "set", "data"], clone)


def publish(doc, clone):
    """Write, commit, push to main and verify. Returns 'unchanged' or 'pushed'."""
    ensure_clone(clone)
    out = clone / OUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(out.read_text()) if out.exists() else None
    if same_ignoring_generated(doc, old):
        return "unchanged"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    run(["git", "add", OUT_REL], clone)
    run(["git", "-c", "user.name=Prices bot", "-c", "user.email=noreply@anthropic.com",
         "commit", "-q", "-m", f"Prices to {doc['market_date']}"], clone)
    r = run(["git", "push", "-q", "origin", "HEAD:main"], clone, check=False)
    if r.returncode != 0:     # another push got in first: rebase once and retry
        run(["git", "pull", "--rebase", "-q", "origin", "main"], clone)
        run(["git", "push", "-q", "origin", "HEAD:main"], clone)
    head = run(["git", "rev-parse", "HEAD"], clone).stdout.strip()
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], clone).stdout.split()[:1]
    if not remote or remote[0] != head:
        raise RuntimeError("push not verified: origin/main does not match the local commit")
    return "pushed"


def notify(message):
    try:
        subprocess.run(["osascript", "-e", f'display notification "{message}" with title "Prices"'], timeout=10)
    except Exception:
        pass


def main(argv=None, get_json=http_json, sleep=time.sleep, now=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--clone-dir", default=str(DEFAULT_CLONE))
    ap.add_argument("--key", default=None, help="for tests only; normally read from the key file")
    args = ap.parse_args(argv)
    key = args.key or read_key()
    now = now or dt.datetime.now(dt.timezone.utc)
    clone = Path(args.clone_dir)

    results, errors = {}, {}
    for i, (t, owned) in enumerate(TICKERS):
        if i:
            sleep(SPACING_SECONDS)
        try:
            results[t] = (owned, fetch_series(t, key, get_json))
            print(f"{t}: ok, newest {results[t][1][0][0]}")
        except FetchError as e:
            errors[t] = str(e)
            print(f"{t}: FAILED ({e})")
    previous = None
    out = clone / OUT_REL
    if out.exists():
        try:
            previous = json.loads(out.read_text())
        except ValueError:
            previous = None
    doc = build_document(results, previous, now, errors)
    if not results or doc is None:
        msg = "Could not fetch any prices today."
        print(msg)
        if args.notify:
            notify(msg)
        return 2
    if args.dry_run:
        print(f"market date {doc['market_date']}, {len(doc['tickers'])} tickers, errors: {len(errors)}")
        for e in doc["tickers"]:
            print(f"  {e['t']:5} {e['last']:>9} day {e['chg']:>6}% 30d {e['m30']:>6}% as of {e['asof']}"
                  f"{' STALE' if e['stale'] else ''}")
        return 0
    try:
        status = publish(doc, clone)
    except RuntimeError as e:
        print(f"PUBLISH FAILED: {e}")
        if args.notify:
            notify("Prices fetched but not published.")
        return 3
    print(f"Published: {status} (market date {doc['market_date']}, {len(errors)} ticker errors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
