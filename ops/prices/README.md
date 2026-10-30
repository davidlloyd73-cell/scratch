# Daily share prices for the dashboard

A small script that runs on the Mac mini once a day, fetches the last 100 days of closing prices for the ten shares from Alpha Vantage, and publishes one file:

    https://davids-ai-brief.netlify.app/data/prices.json

The cloud dashboard task reads that file instead of scraping pages. No AI is involved: it either works or it visibly does not.

## Why it runs on a Mac

The cloud task's network address is shared and Alpha Vantage refused its first request ("25 requests per day reached" on a brand-new key). A Mac uses its own home connection.

## One-time setup on the Mac mini

1. Get the code (the repo is already on the Mac if it was cloned for the handoff):

   ```bash
   cd ~/Code && git clone https://github.com/davidlloyd73-cell/scratch 2>/dev/null || git -C ~/Code/scratch pull
   ```

2. Save the Alpha Vantage key where only this Mac can read it. Never commit it, and never put it in a task prompt:

   ```bash
   mkdir -p ~/.config/lloyd-prices && chmod 700 ~/.config/lloyd-prices
   printf '%s' 'PASTE-THE-KEY-HERE' > ~/.config/lloyd-prices/alphavantage.key
   chmod 600 ~/.config/lloyd-prices/alphavantage.key
   ```

3. Dry run. It fetches and prints a table and changes nothing. It takes about 2.5 minutes because it waits 15 seconds between shares:

   ```bash
   python3 ~/Code/scratch/ops/prices/fetch_prices.py --dry-run
   ```

   Check the dates are the last US trading day and the numbers look right.

4. Real run. This clones a small copy of the website repo (data folder only) to `~/Code/ai-daily-brief-data`, writes `data/prices.json`, pushes to main and checks the push arrived. It needs the Mac's GitHub login, which already works:

   ```bash
   python3 ~/Code/scratch/ops/prices/fetch_prices.py
   ```

   About two minutes later the file should be live at the URL above.

5. Daily timer (06:45). Edit the two `/Users/davidmini/...` paths in the plist if the username or folder differs, then:

   ```bash
   cp ~/Code/scratch/ops/prices/com.lloyd.prices.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.lloyd.prices.plist
   ```

   Log: `~/Library/Logs/lloyd-prices.log`. A failure shows a Mac notification.

## What the file holds

`dates` (90 trading days), and per share: `last`, `chg` (day %), `m30` (30-day %), `series` (30 closes), `idx` (owned shares only, indexed to 100), `asof`, `stale`. Also `market_date`, `expected_asof`, `market_stale` and `errors` (a share that failed keeps its old values and is marked stale).

## Free-tier limits

Alpha Vantage's free key allows 25 requests a day. One run uses 10. Do not run it more than twice a day.

## Tests

```bash
cd ~/Code/scratch/ops/prices && python3 -m unittest -v test_fetch_prices
```

## After it is working

Tell the cloud dashboard task to read `https://davids-ai-brief.netlify.app/data/prices.json` first (step 3a), and delete the key from that task's prompt.
