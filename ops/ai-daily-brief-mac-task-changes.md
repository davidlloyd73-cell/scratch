# Changes to the "Ai daily brief site" scheduled task (Mac only)

The task is locked to the Mac, so these edits need approving there (Claude desktop app, open the task, edit the prompt) or in a Cowork chat linked to that Mac.

## Why

From about 11 Oct every push to GitHub failed with HTTP 403 (the token in gh-token.txt lost write access). The task kept building editions on the Mac but they never reached the website. Yesterday's run reported "nothing new, repo is up to date" because it only compared local files, never whether the push worked.

## Edits

1. **Add an unpushed check after the pull.** Run `git fetch origin main && git rev-list --count origin/main..HEAD`. If above 0, earlier editions never reached GitHub: push them and say how many went out. Only finish quietly when nothing is unbuilt AND the count is 0.
2. **Prefer the Mac's own git login over the token file.** First try `git ls-remote origin refs/heads/main`. If it works, use plain `git pull --ff-only origin main` and `git push origin HEAD:main`. Fall back to gh-token.txt only if it does not. If neither works, send a PushNotification saying the task cannot authenticate to GitHub.
3. **Verify the push.** After pushing, run `git fetch origin main` and check `git rev-parse HEAD` equals `git rev-parse origin/main` and that `git rev-list --count origin/main..HEAD` is 0. A commit not on origin/main is a failed run whatever the push exit code said, and sends a PushNotification.
4. **Report** "pushed and verified: yes/no" and how many previously unpushed commits went out.

## One-off catch-up on the Mac

Run once in Terminal on the Mac that holds the clone. First check what is waiting:

```bash
cd ~/Code/ai-daily-brief && git fetch origin main && git status -sb && git log --oneline origin/main..HEAD
```

If it lists the 12 to 27 Oct editions, push them (needs a login that can write to the repo):

```bash
cd ~/Code/ai-daily-brief && git push origin HEAD:main
```

If that is refused with 403, create a new fine-grained GitHub token (Contents: read and write on ai-daily-brief only) and put it in gh-token.txt in that folder.
