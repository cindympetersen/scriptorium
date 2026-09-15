<!-- One change per PR. CONTRIBUTING.md has the whole list; this is the short form. -->

## What this changes, and why

<!-- The job it does or the failure it prevents. Where there is a measurement, give it:
     what you ran, what happened, what should have. -->

## What a desk will notice

<!-- One line, also added under `Unreleased` in CHANGELOG.md in this PR. -->

- [ ] CHANGELOG.md `Unreleased` has the line
- [ ] Which number it moves: **MAJOR** (a desk must change) / **MINOR** (a desk can adopt or ignore) / **PATCH** (no interface changes)

## Checks

- [ ] `python3 tools/ci_check.py` is green locally
- [ ] Docs that describe the changed thing are changed here too (SKILL.md, `docs/`, README)
- [ ] A refusal added or changed has a test that it fires and a test that it stays quiet
- [ ] No writing, voice text, outlet URL, account handle or local path from an instance
