# Changelog

Scriptorium uses [semantic versioning](https://semver.org). The version is in `VERSION`, every
release is a git tag `vX.Y.Z` on `main`, and this file says what each one changed. The rule for
which number moves, written for the person deciding at release time:

- **MAJOR** — a desk has to change to keep working: a `publish.yaml` key renamed or removed, a
  tool's command line or exit codes changed, a skill's contract with the instance changed, a
  template's layout moved.
- **MINOR** — something a desk can adopt or ignore: a new skill, tool, manifest key, gate, or
  outlet kind; a doc that changes what the desk should do next.
- **PATCH** — a fix that changes no interface: a guard that now fires where it should, a
  converter that renders what it always meant to.

A desk pins the framework by submodule commit, so a tag is a name for a commit a desk can move
to on purpose, not something that moves a desk by itself.

Every change that a desk would notice gets a line under **Unreleased** in the same commit; a
release moves those lines under a version heading, bumps `VERSION`, tags, and publishes the
GitHub release with the same text.

## Unreleased

## 0.1.0 — 2026-09-15

The first tagged release, cut the day the framework moved to the `muffin-labs` organization.
It is `0.x` on purpose: the writing loop, the publishing transport and the shared-desk rules are
in daily use, and their interfaces still move.

- **The writing loop:** `draft`, `critique`, `style-audit`, `tune-style`, `rewrite`, `review`
  (the review artifact, with every proposed change anchored in the prose), `tags`, `talk`,
  `whats-on-the-desk`, and the book-scale set (`book-status`, `gmc`, `chapter-draft`,
  `chapter-audit`, `pov-audit`, `continuity-audit`).
- **Styles as steering:** a style is a folder — constitution, config, exemplars, an append-only
  corrections file — and `tune-style` is the gated pass that folds corrections in.
- **Publishing:** Substack (compose, surgical republish, two-way sync with a sealed baseline,
  verify against the live page block by block, cover, tags, Notes), LinkedIn Articles (the copy
  with *Originally published at*, the hero as the cover, figures with their alt and captions),
  and quire content-store sites (`md_to_site` → `bundle_pieces` → `store_publish`).
- **Scheduling:** `publish_at` with per-outlet `on_schedule`, native-scheduler records, a
  publication-day runbook, and the Note by scheduled task after the post is live.
- **Gates:** links, verified clearance, scripture loci, held-source quotations, CommonMark,
  pronouns, stage direction, cross-references, captions, outlets — `gates.py` runs them all.
- **The shared desk:** advisory leases, a generated dashboard from per-piece fragments,
  path-scoped commits, a session-derived port, a pre-push hook that runs CI on the exact commit.
- **Adoption:** `tools/new-desk` scaffolds a private instance from a fork of this repo, with CI.
