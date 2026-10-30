# Handoff: sort out David's scheduled tasks and dashboard (30 Oct 2026)

Paste the "Opening prompt" at the bottom into a Claude session running on the Mac mini, with this repo (davidlloyd73-cell/scratch) open.

## Goal
David (73, UK GP, Harrow) wants every daily task to actually run and to land in ONE place instead of scattered folders on the iMac, Mac mini, iCloud and Downloads. Tasks that fail silently are the main frustration.

## What is already done (all verified unless noted)
- Dashboard artifact (private): https://claude.ai/artifact/JtZdiNUN2h36aiycQC5JaK . Task "Daily dashboard builder" trig_01DdDgdNm3Pv95BxqbS9BFok, cloud, 08:35 London. Template + build script in this repo under dashboard/. History file is data/history.json inside the artifact. It collects GitHub, ICB pages and the AI brief fine; shares are stale (see below).
- Repos: davidlloyd73-cell/scratch (dashboard code, ops notes), davidlloyd73-cell/lloyd-dashboard-data (private, empty history file, intended as the single hub), davidlloyd73-cell/ai-daily-brief (website repo, Netlify auto-deploys from main).
- Cloud task "Morning Rush (cloud)" trig_011YZ8c8UjBKyNVdcroegbgz, 06:00, currently DISABLED. Test run 30 Oct (session cse_013sJK7kP8jRE2NCv6VVsS9W) wrote Issue 164 but the push failed with 403: a scheduled cloud run can only push to repos listed as SOURCES on the task, and add_repo inside the run did not grant that. The task has sources:[] and create_trigger/update_trigger cannot set sources. Fix = add davidlloyd73-cell/ai-daily-brief as a repository source with push access on this routine in the claude.ai routines page (David, in the UI), then re-enable and fire once. Until then the old Mac Rush task stays the live one.

## Root causes found
1. From about 11 Oct every `git push` from the Mac to ai-daily-brief failed with HTTP 403 (token in gh-token.txt lost write access). Editions were built locally and never published. Website shows AI brief to 11 Oct, Rush to 18 Oct (issue 163; the Mac wrote up to issue 173 on 29 Oct).
2. The old AI brief task reported "repo up to date" by comparing local files only. It never checked that the push reached GitHub. Same pattern in Rush and the Front Page editor (token files in three folders).
3. Mac tasks only run when that Mac is awake with Claude Desktop open (two tasks were suspended "device_absent"). Tasks are bound to different machines: iMac paths under /Users/davidlloyd, Mac mini paths under /Users/davidmini.
4. Dashboard shares: Google Finance via WebFetch returns cached quotes (26 Oct and older, some 25 Sep). Stooq, CNBC and search fallbacks gave nothing newer.
5. list_triggers "last_run SUCCEEDED" only means the task was dispatched, NOT that it worked. Judge by output (published file, verified push), never by that flag.

## Task inventory (trigger id, schedule, where it runs, state)
- Daily dashboard builder trig_01DdDgdNm3Pv95BxqbS9BFok 08:35, cloud, on
- Morning Rush (cloud) trig_011YZ8c8UjBKyNVdcroegbgz 06:00, cloud, on (new)
- Morning rush daily email trig_01PzwHW49iNtcKRmxAQdJm9k 06:00, Mac (device-bound), on: STILL THE LIVE ONE. It writes issues fine (173 on 29 Oct) but its push gets 403. Do not disable until the cloud one is proven. Fixing the Mac git login fixes both this and the AI brief.
- Ai daily brief site trig_015N8z89UWAd3KLotqeNFzuX 06:20, Mac (iMac folder ~/Code/ai-daily-brief), on. Needs the prompt edits in ops/ai-daily-brief-mac-task-changes.md (needs approval on the Mac). Cannot move to cloud yet: build.py rebuilds feed.xml from every audio file and fetches aidailybrief.ai itself; TTS (edge-tts) needs network.
- Daily osa brief trig_01QwRGBuQPCNxHK8eZdXnsrR 07:10, Mac mini only. DO NOT TOUCH its protocol. SleepWell/OSA/AcuPebble/CPAP figures must never appear in the dashboard or any other task's output; canonical only in the private repo sleepwell-harrow.
- Daily github digest trig_01GnY1gn2HrbKyQShby6Npdr 07:00, iMac iCloud folder: superseded by the dashboard GitHub panel
- Precision portfolio daily brief trig_01QNv2CW36evnbZ9r2ZQKruL 07:45 weekdays, iMac: superseded by the dashboard shares panel (once prices are fixed)
- Daily claude autoresearch literature trig_01VBcqYKqGSvy5edRdvu7NiQ 07:20, iMac Downloads: nothing downstream uses it now
- Harrow referral pathway digest trig_01FdDBZHRP2iNYaekv7sJjZV Mondays 08:10: superseded by the dashboard ICB panel
- Off already: Notebooklm daily digest, Front Page night editor, Weekly downloads digest, Monday gp briefing, Morning inbox and bills sweep, Morning brief (weekdays 8am), BST adjuster (one-off 27 Mar 2027)

## Decisions David has made
- Dashboard: private repo for history, run old tasks in parallel for a week, read the AI brief from the existing site.
- Move Morning Rush to cloud (done), keep AI brief builder on a Mac for now, Mac mini is the single Mac host.

## Progress 30 Oct, late morning (cloud session linked to the Mac mini)
- Item 5 DONE: task health panel. Template (dashboard/template.html) now renders a "Did everything run?" table from data.health; the live artifact's template/dashboard.html was republished with it (version 1793357721-1e34) and the dashboard task prompt gained step 3g plus the health JSON shape. First live fill is the 08:35 run on 31 Oct.
- Confirmed from GitHub: ai-daily-brief main is still at Rush Issue 163 (18 Oct). Nothing has been pushed since.
- Confirmed from the task list: every iMac-bound task (Rush email, GitHub digest, portfolio) "ran" on 30 Oct but finished in 4 to 5 seconds, i.e. the iMac was asleep or the app closed. There is no Issue 174 today.
- Items 1 and 3 CANNOT be done from a session linked to the Mac mini: the Daily Email folder, the ai-daily-brief clone and the token files all live under /Users/davidlloyd on the iMac, and the device bridge is a sandbox, not the Mac's own Terminal, so `gh auth login` must be run by David on that machine. Blocked on David: (a) add ai-daily-brief as a push source on "Morning Rush (cloud)" in the routines UI; (b) run the catch-up commands in ops/ai-daily-brief-mac-task-changes.md on the iMac; (c) an Alpha Vantage key for item 2.

## Still to do
1. On the Mac mini: make git push to ai-daily-brief work with the Mac's own login (run `gh auth login` or use GitHub Desktop credentials; test with `git ls-remote` and a dry push). This single fix unblocks both the Rush and the AI brief tasks. Then push the backlog (see item 3).
2. Shares: get a free Alpha Vantage key from David, store it in the dashboard task prompt; the task then fetches daily closes (about 100 days) so the trend charts fill at once. Without a key, prices stay stale.
3. On the Mac: push the unpublished AI brief editions (12 to 27 Oct) and apply the prompt edits; copy the missing Rush editions 164 to 172 from the Daily Email folder into ai-daily-brief/rush/src and push.
4. Consolidate: one hub for outputs (the dashboard artifact plus lloyd-dashboard-data), no more per-task Downloads/iCloud folders. Keep a Mac only for work that needs its own disk or Chrome profile (OSA brief and NotebookLM, AI brief audio).
5. Add a daily "health" panel to the dashboard: for every task, did it publish today, yes/no, with the last verified output date. A task that did not run must be visible.
6. After a week of green parallel running, disable superseded tasks (portfolio, GitHub digest, referral digest, autoresearch).

## Rules to keep
- Never print or commit tokens. Never recommend buying or selling; keep "Information only, not financial advice".
- Never invent data; mark a missing feed visibly.
- UK English, no emojis, plain direct tone. David is a clinician, not a developer: explain in plain words and ask only decisions that are his.
- Never delete and recreate a device-bound task (loses history); change prompts through approval on that Mac.

## Opening prompt to paste on the Mac mini
"Read ops/HANDOFF.md in this repo and carry on from 'Still to do'. Start by checking the cloud Morning Rush test run result, then work through the list. Report back to me in plain words after each step, and ask only when a decision is genuinely mine."
