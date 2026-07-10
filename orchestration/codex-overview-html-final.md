Built [.reports/overview.html](/home/jason/PycharmProjects/adversarial-spec/.reports/overview.html) and updated [.reports/report-state.json](/home/jason/PycharmProjects/adversarial-spec/.reports/report-state.json).

Verification passed:
- JSON assert for `overview` + `recent`
- Required strings/block ids, `recent.html` link, feedback POST, no decision widgets
- Zero `http://` / `https://` matches
- Playwright soft gate skipped: `playwright` is unavailable locally, and the handoff forbids install/network work

`git status` shows both report files as untracked because `.reports/` is untracked.