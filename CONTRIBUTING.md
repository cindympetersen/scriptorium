# Contributing

Scriptorium is meant to be forked. Your desk mounts your fork, you tune the framework as you
write, and some of what you tune is worth sending back. This page is how that trip works, in
both directions.

## The shape: a fork with two remotes

Inside your desk, `framework/` is your fork with `origin` pointing at it and `upstream` pointing
here (`tools/new-desk` sets both). Framework changes made from inside the desk — by you or by
Claude Code working on a piece — are committed **in `framework/`, by path**, and pushed to your
fork. Nothing about that needs anyone's permission. Contributing is the second step: choosing
which of those commits should also become upstream's.

```bash
cd ~/code/writing-desk/framework
git fetch upstream
git switch -c my-change upstream/main       # branch from upstream, not from your fork's drift
git cherry-pick <the commits worth sharing>  # or make the change fresh on the branch
python3 tools/ci_check.py                    # the same command CI runs
git push origin my-change
gh pr create --repo muffin-labs/scriptorium --head YOU:my-change
```

## What belongs upstream, and what stays in the fork

**Upstream takes anything that makes the framework better for a desk it has never seen.** A
skill that does a job every desk has, a tool that refuses a mistake every desk can make, a guard
with the failure it prevents written next to it, a doc that says something true more plainly, a
platform port. The Linux and Windows clipboard transports are the standing example: wanted,
small, and unwritten ([README, *Platform support*](README.md#platform-support--macos-only-today-and-contributions-are-welcome)).

**Upstream never takes:**

- **Your writing or your voice.** No prose from your pieces, no lines from a tuned
  `styles/<name>/style.md`, no exemplars, no corrections. `tools/voice_privacy.py` checks that
  no instance voice's text has reached the framework, and your desk's suite runs it against
  **your** voices before a push leaves your machine — upstream's CI cannot see your voices, so
  the check that protects you is the one on your side. A PR found to carry voice text is closed,
  not edited. Starter styles here are generic on purpose.
- **Your instance's specifics.** Outlet URLs, publication names, account handles, AWS
  profiles, local paths. Those live in the desk's `publishing/` and are passed to tools as
  arguments; the framework holds no URLs.
- **A change to a skill's contract that only your desk needs.** Tune it in your fork. If it
  turns out to be general, propose it as an option with the default unchanged.

If a change is useful but shaped for your desk, the usual fix is a small generalization — a
config key, an argument, an outlet setting — rather than the desk-shaped version.

## What a pull request carries

One change per PR, and the PR is the record of why it exists, so the next person can find the
reason without the conversation that produced it:

1. **The failure it prevents, or the job it does**, in the description — in one paragraph, with
   the measurement where there is one. This house writes guards with the incident beside them
   (*measured 2026-09-11 on post 215690614: …*), because a rule with no recorded reason gets
   switched off the first time it is inconvenient.
2. **A line under `Unreleased` in [`CHANGELOG.md`](CHANGELOG.md)**, in the same commit, saying
   what a desk would notice — and which number it moves: **MAJOR** if a desk has to change to
   keep working, **MINOR** if a desk can adopt or ignore it, **PATCH** if no interface changes.
   The release is cut here; the classification is yours to propose.
3. **The docs that describe the changed thing, changed in the same PR.** A skill's `SKILL.md`,
   the doc under `docs/` that covers it, the README line if the README names it. A tool that
   gained a flag with no doc that mentions the flag is half a change.
4. **A test where a refusal was added or changed.** The suite (`tools/test_suite.py`) runs on
   fixture pieces under `tools/fixtures/`, never on real writing; a guard is worth a check that
   it fires and a check that it stays quiet.
5. **Green CI.** `python3 tools/ci_check.py` is the command GitHub runs on every PR; run it
   before pushing, and never `git push --no-verify` around the pre-push hook that runs it for you.

Commit messages say what changed and why, in the house's plain register: *"md_to_substack: an
image's alt text is not clearance scaffold"* rather than *"fix bug"*.

## How a PR is handled

- A maintainer reads it against the list above and against the desk it was not written for. The
  usual response to a good change shaped for one desk is *"generalize this one thing and it's
  in"*, not a rewrite by the maintainer.
- Small, self-contained PRs merge fast. A change that touches a skill's contract, the manifest
  format, or the publishing transport gets an issue first, because those are the MAJOR bumps
  and every desk pays for them.
- Merged changes go out in the next tagged release ([`CHANGELOG.md`](CHANGELOG.md)); a desk
  pulls `upstream main` or moves its submodule to the tag when it wants them.

## Opening an issue instead

If you have the failure but not the fix, an issue with the measurement is as welcome as a PR:
what you ran, what it did, what it should have done, on which platform. A reproducible refusal
that fires wrong is the most useful bug report this repo gets.

## Licence

MIT. By contributing you agree your contribution is licensed the same way.
