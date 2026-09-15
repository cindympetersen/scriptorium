# Publishing — one desk, many outlets

**Status: proposed.** Nothing here is built. This is the design to agree before any
site changes; it supersedes nothing until it does.

## What this is for

A piece is finished on the desk. It has to reach every place it belongs — one or more
websites, a Substack, LinkedIn — with the same words, correct canonical links, and no
half-published state where it is live in one place and 404 in another.

Most of that machinery already exists: [`BUNDLE.md`](BUNDLE.md) is the interchange
format, `publish.yaml` names outlets, `md_to_site.py` exports, `outlet_audit.py` checks
both directions. What this document adds is (a) a delivery model where updating content
does not rebuild a site, (b) talks as a first-class content type, and (c) LinkedIn.

## The decision that shapes everything else

> Content should be live seconds after publishing, without a build.

That single requirement rules out the current model, and it rules out a build-time
content layer as the live path. Velite reads files out of a repo during `next build`;
so does a vendored bundle. Both mean *edit → commit → push → build → live*, which is
minutes at best and a git operation at worst.

It also pulls against a value already written into the alignment site's
`next.config.mjs`:

> Pure static HTML. The publication should outlive any particular host: this output
> redeploys to Cloudflare Pages, Netlify, GitHub Pages, S3 or a thumb drive without a
> code change.

Both things are worth having, and they are not actually in conflict once you stop
treating the static export as the *live* artifact and start treating it as an
*archive* you can produce at any time. See [Snapshots](#snapshots-keeping-the-thumb-drive-property).

## Shape

```
  desk (private)                    store (public)                 readers
┌────────────────────┐          ┌────────────────────┐         ┌──────────────┐
│ pieces/<name>/     │          │  index.json        │         │ muffinlabs   │
│   draft.md         │  publish │  pieces/<slug>.json│  fetch  │ alignmentf.  │
│   publish.yaml     │ ───────► │  talks/<slug>/     │ ──────► │ (any site)   │
│   outlets: [...]   │          │  images/<slug>/    │         └──────────────┘
└────────────────────┘          └────────────────────┘
         │                                                     ┌──────────────┐
         └──────────────── browser-driven ───────────────────► │ substack     │
                           (compose, human ships)              │ linkedin     │
                                                               └──────────────┘
```

Two kinds of destination, and the difference is not incidental:

- **Stores** are written to. Publishing is a file upload; the site reads. Idempotent,
  reversible, auditable.
- **Surfaces** are driven. Substack and LinkedIn have no usable write API, so a browser
  composes the post and **a human clicks the final button**. That rule is already in the
  `publish` skill and does not change here: outward-facing publication is not delegated.

## The content store

An **S3-compatible bucket behind a CDN**. S3's API is the closest thing to an open
standard in this space — the same client works against AWS S3, Cloudflare R2, Backblaze
B2 or a self-hosted MinIO, so the store is not a vendor lock-in even though it is a
hosted service today.

```
<store>/
  index.json                     # every published piece, per outlet
  pieces/<slug>.json             # one piece: front matter + markdown body + plain text
  talks/<slug>/deck.html         # standalone deck
  talks/<slug>/notes.json        # per-slide speaker notes
  talks/<slug>/assets/…
  images/<slug>/…webp
```

### Rendering: one shared component package, markdown in the bundle

**Decided 2026-09-10.** The bundle carries markdown, and every site renders it through
a single shared React package rather than each site owning a renderer.

The problem is real either way. Today alignmentfellowship renders through velite with
`remark-gfm`, and muffinlabs has a hand-rolled renderer that handles headings, lists and
whole-line bold **and nothing else** — no images, no links, no inline emphasis, no
footnotes. The same bundle renders correctly on one site and badly on the other.

Two ways to fix that: render once in the exporter and ship HTML, or render in one place
that every site imports. The shared package wins because every consumer is now React on
Vercel — including the member app — so rendering can use real components (`next/image`,
internal link handling, footnote markup) instead of injected HTML. Markdown also stays
the only stored form, which keeps a future non-React destination possible.

The cost is cross-repo versioning: three consumers in two GitHub orgs, so the package
needs a real home and a real release, not a copied file.

Consequences worth stating plainly:

- Every site displays identical output, because it is literally the same components.
- The muffinlabs blocker is dissolved without adding velite to it, and without either
  site keeping a renderer of its own.
- Footnotes, images and links are settled in one place, so a fix lands everywhere at
  once instead of being fixed twice and drifting a third time.
- Markdown remains the only stored form. A future destination that is not React — an
  email, a print edition, an archive — still has something to render from.

The trade: a rendering change now means a package release and a redeploy of each site,
where shipping HTML from the exporter would have meant re-publishing pieces instead.
That is the honest cost of choosing components over bytes, and it is the reason the
package needs a real home and a version, not a file copied between repos.

## Snapshots: keeping the thumb-drive property

Runtime content and host-independence are reconcilable if portability is an artifact
rather than a constraint:

```bash
python3 framework/tools/snapshot.py <store> ./snapshot
```

Walks the store and writes a complete static site — every piece as HTML, every image,
an index. That output deploys to Netlify, GitHub Pages, S3 or a thumb drive with no
code change, exactly as the current export does. The difference is that it is produced
on demand, for archival or for the day a host disappears, instead of being the only way
the site can work.

**This is the honest cost of the decision:** the live site now needs a server (or at
least a runtime fetch), where today it needs nothing. In exchange, a typo fix is live in
seconds. If that trade ever looks wrong, the snapshot is the way back.

## Talks

A talk is a piece whose reader is a room. It has three artifacts and they have different
homes:

| artifact | source of truth | why |
|---|---|---|
| the script | desk (`draft.md`) | it is prose, and it is what the speaker says |
| speaker notes | desk | authored with the script, not with the slides |
| the deck | **Claude Design** (`.dc.html`) | designed visually; the desk cannot express layout |

The flow, as it stands since 2026-09-14 — **the draft owns every word on a slide, every figure
and the speaker notes; the canvas owns layout, and nothing else.** The first talk's deck forked
because nothing held that line: the canvas was drawn from the slide briefs by hand, the design
pass moved two figures' axes and reworded notes, the desk corrected the script, and neither
could regenerate the other. `tools/md_to_dc.py` holds it now:

1. The talk is drafted on the desk — `draft.md`, figures from `assets/figures.py`.
2. `md_to_dc.py generate <talk>` writes the canvas from the draft: one `.dc.html` artboard per
   slide in the house markup (the first deck's, with every text element tagged by role and every
   slide by a stable key), `canvas.json` laying them out a row per movement with each
   `<!-- design: … -->` note as a sticky note above its slide, and a downsampled preview of each
   figure. The `design` skill seeds and publishes that as the canvas the designer opens.
3. The design pass happens in the canvas — layout, type, spacing, the accent — and is saved there.
4. When the script changes: the saved canvas is read back (the design helper's `--extract`),
   `md_to_dc.py resync` replaces the words, figures and notes in place and keeps every layout
   edit, and the result is re-seeded to the same canvas. A slide whose shape changed (a bullet
   gained, a figure added) is regenerated and the report says so.
5. `md_to_dc.py verify` compares any canvas — extracted artboards or a composed deck — to the
   draft slide by slide and exits 1 on drift. It runs before anything ships.
6. `md_to_dc.py compose` assembles the artboards into the one-file `deck.dc.html` the site builds
   from, with the full-resolution figures beside it, and **refuses on drift**; then
   `dc_to_deck.py` lifts the slides out of the authoring wrapper, emits plain `<deck-stage>`
   markup, drops the design runtime, and writes `notes.json` for a phone remote.
7. The deck and notes go into the bundle and then the store.

Two rules the conversion keeps, both learned the hard way:

- **Assets are verified, not assumed.** A design asset larger than the read limit comes
  back truncated. A PNG without an `IEND` chunk is a truncated download, and the build
  must refuse it rather than ship a broken slide.
- **The design runtime never ships.** `support.js` needs React and exists to serve the
  authoring canvas. `deck-stage.js` has no such dependency and documents a plain-HTML
  usage; that is what gets published.

A canvas from before this tool (the first talk's) carries no keys; `verify` matches it by
position and still finds a figure drawn out of the deck or a note reworded — which is how the
fork was measured: seven of thirty slides.

Presenter tooling — speaker view, phone pairing, slide sync — is a *site* feature, not
content. It reads `notes.json` from the store like anything else.

## Outlets

Unchanged in principle: a piece goes only where its `publish.yaml` names, and `publish`
refuses to guess. What changes is that a store outlet is a write, not a deploy.

| outlet | kind | canonical for | how |
|---|---|---|---|
| `muffinlabs` | store | professional pieces | write to store; site reads |
| `alignmentfellowship` | store | theological pieces | write to store; site reads |
| `substack` | surface | — | browser compose, human publishes |
| `substack-muffinlabs` | surface | — | same; subdomain still unchosen |
| `linkedin` | surface | — | browser compose, human publishes |

### LinkedIn

Constraints, none of them negotiable by tooling:

- **No write API.** Articles have none; even a share needs an approved app and OAuth.
  So it is browser-driven, like Substack, for the same reason.
- **An Article carries the text; a Post announces it.** For an essay the Article is the
  surface, with a Post linking it.
- **LinkedIn emits no `rel=canonical`.** "Link to the canonical" means a visible line in
  the body — *Originally published at <url>* — not a tag. Publish the canonical first
  and let it be indexed before the copy goes up.
- **The final click is never delegated.**

## The audit

`outlet_audit.py` gains a third check, because the store makes a new failure possible:

- **forward** — every published piece resolves on every outlet it declares
- **reverse** — every URL an outlet lists is a piece the desk knows about
- **store** — every piece in `index.json` is served by every site that reads it, and the
  digest the site serves matches the digest in the store

The third one matters because a stale CDN edge is invisible: the store is correct, the
site is wrong, and nothing fails. Comparing digests is what catches it.

## Sequence

1. Agree this document.
2. ~~Bundle spec v2: talks as a content type, and a `pieces/<slug>.json` shape the
   shared renderer and the sites agree on.~~ **Done 2026-09-10.** A talk is a piece
   with a `talk` block, not a second type — see `BUNDLE.md`. quire v0.5.0 carries the
   type and validates it; the presenter protocol moved there in v0.4.0.
3. ~~Stand up the store and the shared read client; point one site at it.~~
   **Done 2026-09-10.** S3 + CloudFront (`DeskContentStore`, defined in the desk's
   `infra/`), quire's `quire/store` client, and muffinlabs reading its talk from the
   store. `talk_bundle.py` assembles a bundle; `store_publish.py` uploads it,
   idempotently, and invalidates what moved.
4. ~~Move the second site; retire the vendored-bundle path.~~ **Done 2026-09-10.**
   alignmentfellowship reads all 32 writings and their images from the store;
   `content/writings`, `public/images`, velite and `import-bundle.sh` are gone.
   `bundle_pieces.py` did the conversion. It cost `output: 'export'` — a static export
   can only read the store at build time, which takes the dependency and gains none of
   the speed — so **item 5 is now load-bearing**, not optional: the portability promise
   that flag used to keep now rests entirely on the bundle and a snapshot.
5. ~~`snapshot.py`, so the portability promise is real before anyone relies on it.~~
   **Done 2026-09-10.** `tools/snapshot.py <out>` writes the whole store back out as a
   bundle on disk — front matter + markdown, images, decks — and verifies as it goes:
   a download nobody has checked is a promise, not a backup. Proven by round trip:
   alignmentfellowship's 32 vendored files, recovered from git, match the snapshot
   exactly once the documented `/images` → `../images` rewrite is accounted for.
   `--verify-only` re-checks an existing snapshot and exits non-zero on a fault.
6. ~~LinkedIn outlet.~~ **Built and driven 2026-09-10**, against a labelled test draft. `tools/md_to_linkedin.py`
   composes the Article copy and refuses without a recorded, live canonical;
   `skills/linkedin-article` carries the flow; `outlet_audit.py` now refuses to guess a
   LinkedIn URL (`derive: false`), reports a published piece whose copy was never recorded,
   and knows LinkedIn's not-found page when a dead Article redirects to it. What is left is
   measured, not built — and on 2026-09-10 it was measured: the whole compose ran in the
   built-in pane (Eric's decision that day: the Article editor is in scope, pane preferred),
   59/59 blocks byte-identical, a figure uploaded to LinkedIn's CDN with its 740-character
   alt text surviving a reload. What remains is a real piece, whose canonical is live — none
   is yet. The instance's outlet entry:

   ```yaml
   linkedin:
     reader_base: https://www.linkedin.com/pulse/
     manifest_url_key: linkedin_url
     # LinkedIn appends an id to every Article slug, so a URL can only ever be RECORDED.
     derive: false
     # A dead Article answers 301 to a real page that returns 200. Measured 2026-09-10.
     not_found_markers: [article_not_found]
   ```

### One thing a snapshot does not fix

A snapshotted deck was served with `python -m http.server` and rendered: 30 slides, all
four figures. It is genuinely standalone — except that the deck's `<helmet>` pulls a
webfont from Google, inherited from the Claude Design export. It degrades to a system
face rather than breaking, so the publication survives; but "runs from a thumb drive with
the network unplugged" is not quite true of a deck, and saying so is cheaper than
discovering it during an outage. Inlining the font at conversion time would close it.

## The properties this has to serve

As of 2026-09-10 the web outlets are all Next.js on Vercel, which is what makes a single
shared renderer and on-demand revalidation practical:

| property | repo | role |
|---|---|---|
| muffinlabs.ai | `muffin-labs/muffinlabs-web` | canonical for professional pieces; carries talks |
| alignmentfellowship.org | `alignmentfellowship/website` | canonical for theological pieces; the record |
| the member app | `alignmentfellowship/app` | not a publishing target yet, but a third consumer of the renderer |

muffinlabs was on AWS Amplify until 2026-09-10 and is now on Vercel, which is the change
that made the delivery decision above available. The member app is listed because it
will want the same prose components, and a package with three consumers is designed
differently from one with two.

## Site hosting is a separate question

The store is the shared asset, and sites read it over HTTPS. **Where a site runs has no
bearing on where content lives** — which is why consolidating hosting is not a
prerequisite for any of this, and should be decided on its own merits.

One thing this design does constrain: content fetched at request time needs compute at
the edge. A site that is a pure static export cannot do it, so the choice of host has to
be one that renders per request. That is a point in favour of hosts with first-class
incremental rendering, and a point against any host whose server-side story is shaky.

## Open questions

- ~~Which store.~~ **Decided 2026-09-10: AWS S3 + CloudFront.** At this scale both were
  free — the store is about 25 MB, and the difference worked out near a tenth of a cent
  a month — so cost decided nothing and the operational argument won: no second cloud,
  no second credential set, and the same account that already runs the presenter API.
  CloudFront's flat-rate plans (Free: 1M requests and 100 GB/month; Pro: $15/month flat
  to 50 TB, no overages) also blunt the egress risk that used to make R2 the obvious
  answer. Because the client is written against the S3 API, moving to R2 later is a
  bucket sync and an endpoint change.
- ~~Where the rendering lives.~~ **Decided 2026-09-10: a shared React package**, since
  every consumer is now React on Vercel. What is still open is where that package lives
  and how it ships. The consumers span two GitHub orgs — `muffin-labs` and
  `alignmentfellowship` — plus the member app, so it needs to be installable across
  orgs: a public repo consumed as a git dependency, or a published package. A private
  registry would add an auth story to three repos to protect components that contain
  nothing secret.
- ~~**Velite's remaining role.**~~ **Settled 2026-09-10: retired.** Its job was
  validating front matter against the bundle spec, and quire's `validatePiece` does
  that now — at the point of reading, for every site rather than one. alignmentfellowship
  no longer depends on it.
  Keeping both means two schemas that can disagree, which is the failure the bundle
  exists to prevent.
- **Migration of 42 pieces.** Re-export is mechanical, but every published URL must keep
  resolving, and some slugs already diverge between outlets.
