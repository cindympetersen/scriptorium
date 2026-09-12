# Alt text and captions

**The one statement of the rule.** It used to be written only inside the `publish` skill, which
runs at compose time — while alt text is *written* at draft time and *read* on the review
artifact. Whoever needed the rule was the least likely to meet it. This file is what the skills
point at.

## The rule

**Describe what the image shows, and transcribe any text that is *in* the image, in quotation
marks.**

Both halves are required, and the second is the one that gets forgotten:

- **Describe** — what a sighted reader gets from looking. The subject, what it is doing, the
  arrangement that carries the meaning. Not the file, not the figure number.
- **Transcribe** — every word rendered *inside* the picture: a title, both axis labels, a legend,
  an annotation, a caption drawn into the art. In quotation marks, so a listener can tell the
  image's words from your description of them. **WCAG 1.1.1**: text presented within an image has
  to be available as text. A sighted reader getting four phrases off the picture means a
  screen-reader user must get them too, and it is not optional.

## What alt text is not

| not this | why |
|---|---|
| **A caption** | The caption sits beside the image for everyone. Alt replaces the image for someone who cannot see it, and a page that has both should not say the same thing twice. |
| **A figure number** | *"Figure 7a: two attributes"* names the slide. It does not say a single thing about what is on it. |
| **A citation** | *"Iain McGilchrist, The Master and His Emissary (Yale, 2009)"* describes nothing. A source line is not a description, and putting one in the alt leaves a listener with no image at all. |
| **A restatement of the prose** | If the paragraph already says it, the alt still has to describe the *picture* — the reader who cannot see it is reading that paragraph too. |

## Captions — what the image represents

**The alt says what the image shows. The caption says what it means here** — what the image
stands for in *this* piece, said in the piece's own voice. A sighted reader already has the
picture; the caption is the line that turns it toward the argument.

| a caption is not | why |
|---|---|
| **A description** | That is the alt's job. A caption that re-describes the image says it twice to every sighted reader, and a screen reader says it twice to everyone else. |
| **A provenance note** | *Generated, not a photograph* is a fact about the file. It is recorded in `publish.yaml` beside `cover:`, where the tools and the review read it — and, where an image could be taken for a real person, in a footnote or the publication's own disclosure. Spent on a caption it tells the reader nothing about the piece. |
| **A disclaimer** | *Not a likeness of …* answers a worry instead of saying anything. If a photorealistic image risks being read as a particular person, that is a problem for the image choice or the prose, not a warning label under the picture. |
| **A line from the piece** | A caption that quotes the body spends that line before the reader reaches it. Measure the shared words rather than judging by ear. |

**The constraint that still holds:** neither the caption nor the alt may *claim* a photograph or a
likeness the image is not. Saying what an image represents never needs that claim, which is why the
rule is stated positively.

**It is house prose too**, so the voice's sweeps govern it, and it is re-swept after it changes.

### Every figure gets one, by default

**A figure carries a caption unless there is a reason it does not.** Not only the hero — every
image in the body. (An author's ruling, 2026-09-11, on a redraft whose one figure had alt text
and nothing else; the wording is in that instance's own ledger.)

The reason it is a default rather than a judgment each time: readers stop at pictures before
they stop at paragraphs, so the caption is often the only sentence of yours they meet near a
figure. A drafting pass that writes alt text and stops has handed the screen-reader user a
description and the sighted reader nothing.

Captions live in `publish.yaml` under `captions:`, keyed by the image's local path, beside
`cover_caption:` for the hero. `md_to_substack` emits them on compose; `substack_captions.py`
sets them on a post composed before that existed. The caption rules above govern them — what
the image represents in *this* piece, never a re-description, a provenance note, or a line
lifted from the body.

## Length

As long as the image is informative and no longer. A photograph is usually a sentence. **A chart
is usually several**, because a chart is mostly text and the text has to come across: title,
axes, legend, the labelled points. If a figure genuinely needs a paragraph, it needs a paragraph
— that is the image being complicated, not the alt being indulgent.

## Decorative images

An image that carries no information takes an **empty** alt (`![](…)`), deliberately, so a screen
reader skips it. This desk has none: every image in the corpus is load-bearing. An empty alt on
a load-bearing image is a bug, and the review artifact flags it in the warning colour.

## It is house prose, and the sweeps govern it

Alt text lives in `draft.md`, so the britishism sweep, the pronoun sweep and every other check
cover it — **but only if they run after it was written.** The first version of one hero's alt said
*labelled* against a spelling rule that names `labeled` explicitly; it went in after the last
sweep and nothing caught it but the author. **Re-run the sweeps after adding or changing an
image.** A passage written after a check does not inherit that check's clean bill.

## Where to read it back

The **review artifact** shows every image with its alt text as prose, labelled, under the picture
— because no other surface an author reads displays it: not `draft.md`, where it is buried inside
`![…](…)`; not Substack; not the live post. It is also **anchorable**, so a review finding can
propose better alt text and `review_artifact.py --apply` writes it like any other change.

## Measured

- **2026-09-10** — a hero's alt omitted the four phrases drawn into the image. Fixed; the rule's
  transcription half comes from that.
- **2026-09-10** — 23 of 34 live posts carried **no** hero alt at all, while the desk held good
  alt text for 21 of them. They lost it to the path they were composed by, not to Substack.
- **2026-09-10** — the two figure-heavy pieces carried **eleven** alts that were slide captions
  rather than descriptions, one of them a bare citation. Rewritten by reading each figure.
- **2026-09-10** — a hero was captioned with a description and a disclaimer (*"… An imagined scene,
  not a likeness of …"*), because the skills said only that a caption "must not imply a photograph",
  and read literally that produces a warning label. The author: *"the caption should talk about what
  the image represents."* The *Captions* section comes from that, and the header gate now warns on a
  caption that reads as provenance or repeats the alt.
