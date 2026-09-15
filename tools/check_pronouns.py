#!/usr/bin/env python3
"""check_pronouns.py — the pronoun sweeps this desk kept doing by hand, as one tool.

WHY THIS EXISTS (2026-09-03).  Three pronoun rules live in the constitutions and all three
were being enforced by ad-hoc greps typed fresh in each session — and a rule no sweep checks
is a rule nobody enforces.  *The Mask Comes Off Last* reached a composed Substack draft
carrying twenty-one generic masculines for the villain (the 2026-09-01 rule said they/them),
and then a lowercase *the one* for God (the essay voice capitalizes God named indirectly:
*the One*, *Someone*).  Both were caught by Eric, after compose, reading the page.

WHY E AND F EXIST (2026-09-07).  The first four sections stop at a quotation's edge — inside
one, the source's case was taken as evidence and left alone.  But the constitution's casing and
bracket rules reach INSIDE this house's own scripture (see `God_in_quotations`,
`God_in_quotations_casing`, `God_in_quotations_exclusions` in the essay voice's config.yaml), and
nothing was sweeping there.  *False Light*, 2026-09-07, measured four misses in one draft, all
inside italic King James quotations: Matthew 4:10 *Him only shalt thou serve* (a capital
*Him* that refers to the Father — the house pronoun is *[Them]*, bracketed, since that is a
substitution); Matthew 5:45 *He maketh His sun* (same: Father, so *[They make] [Their] sun*);
John 5:30 *of mine own self* and John 15:5 *without me* (the Son speaking, whose own pronouns
the house capitalizes inside a quotation — *Me*, *My*, *Mine* — as a casing convention, never
bracketed).  Eric caught the first one reading the page; the rest fell out of the audit it
prompted.  A sweep that stops at the quotation's edge cannot see any of them.

WHY H EXISTS (2026-09-10).  Section D catches a bare lowercase *it* / *its* within six words
after a God-word, and that shape is only half of how God gets turned into a *what*.  The other
half is the REFLEXIVE, which D's window never sees: *They Them* shipped live carrying *the source
that called itself us before it had made anything at all* and *A plural form, speaking of itself
in the plural* — both corrected (to *Themself* then, to *Themselves* now) — and again it was Eric,
reading the published page, who caught them.  A window cannot find these: the antecedent is what matters, and the two
legitimate uses in the corpus (*a second thing standing outside God on its own ground*, *the
clutching self is the source of its own suffering*) sit just as close to a God-word as the misses
do.  So H asks a grammatical question instead of a proximity one — whose reflexive is it? — and
its two paths are the two ways this corpus's answer comes out *God*.

WHAT IT CHECKS, on the whole draft body (footnotes included), whitespace-normalized:

  A. A SENTENCE-INITIAL CAPITAL THAT READS AS DEITY  He/Him/His/They/Them/She/Her at the head of a
     sentence, WHERE THE NEAREST ANTECEDENT IS A PERSON.  English forces the capital on every
     pronoun at a sentence head, so the capital itself is not the fault; in a house that
     capitalizes deity pronouns, the one that does damage is a HUMAN's, which then reads as the
     Son, the Father or the Spirit.  A capital whose nearest antecedent is God is correct and
     unremarkable, and so is one in a paragraph that has just named the person — the reader knows
     who is meant.  The capital can only be MISREAD where God is in play in the same paragraph, so
     both a figure and a God-word must be present, the figure nearer.  Listing every capital buried
     the real ones 485-deep, and listing every human-antecedent one still put 51 correct sentences
     up for review (narrowed twice on 2026-09-10, Eric's call).  Fix it by recasting the sentence
     so the pronoun is not its first word, or by using the name.
     KNOWN LIMIT: `nearest antecedent` mis-attributes where a person's NAME sits beside a divine
     pronoun — a scripture citation (*John 10*), or an author quoted about God.  *None but He and
     I* reads its *He* as Brother Lawrence when the word is God's, in Lawrence's own phrase.
  B. GENERIC MASCULINE  he/him/his/himself, and *a man*, *any man*, *one man*, *the man*.
     An imagined person is they/them; a real one — from scripture, history or a story, or the
     author — keeps their own pronouns.  A person named in `figures:` in the
     piece's publish.yaml — or passed with --names — is STICKY FOR THE REST OF ITS PARAGRAPH, and
     hits after them are theirs.  The old test was a 120-character lookback, far shorter than this
     desk's prose: *Rising After Falls* names Brother Lawrence once and then says *he* for two
     hundred words, and 85 of its 98 hits read GENERIC? when every one was Lawrence.
  C. GOD AS A LOWERCASE OBLIQUE, OR AS A *WHAT*  lowercase *someone / whoever / the one /
     a mind / one mind / something* where the same sentence names God (God, Lord, Father,
     Spirit, Them, infinite, dream(ing), remembering, the One).  The house capitalizes
     these when they mean God, and never refers to God as a thing.
  D. LOWERCASE DEITY PRONOUN  he/him/his/it within six words after God / the Lord / the Father /
     the Spirit / Christ / Jesus, outside a verbatim quotation.  Inside a quotation the source's
     own case is evidence and stays (the KJV lowercases; the house capitalizes in its own prose
     and, for its own scripture, raises the case — see the constitution).
  E. CAPITALIZED He/Him/His/Himself INSIDE A SCRIPTURE QUOTATION.  A capital there is the house
     saying *this is the Son*.  If the referent is the Father, the word is wrong, not the case:
     God-as-God is *They/Them*, and inside a verbatim quotation that is a substitution, so it is
     bracketed — *[Them] only shalt thou serve* — with the verb bracketed too where agreement
     needs it (*[They make]*, never *[They] maketh*).  The tool cannot know the referent; it
     lists every hit with its sentence, and each is justified as the Son or repaired.
  F. LOWERCASE me/my/mine/myself INSIDE A GOSPEL QUOTATION.  Where the speaker is the Son the
     house capitalizes His own pronouns in the quotation — *He that hath seen Me hath seen the
     Father* — as a casing convention (never bracketed, disclosed once per piece).  Heuristic:
     the quotation is followed by a footnote ref whose definition cites a Gospel (Matthew, Mark,
     Luke, John — not 1/2/3 John) and it contains a first-person pronoun.  A Gospel voice is not
     always Jesus (the prodigal's *make me as one of thy hired servants*), so it lists, and the
     operator names the speaker.
  H. THE REFLEXIVE FOR GOD  *itself* / *its own* / *themselves* whose antecedent is God, plus
     *themself* in ANY case, which is simply the wrong form (see `wrong-form` below).
     Three paths, each reported with the evidence that qualified it:
       `subject` / `rel` / `appositive` — the subject of the reflexive's own clause resolves to a
         God-word.  A relative clause takes the head noun it attaches to (*the source that called
         itself*), and a head noun that is an appositive in a copular chain resolves through it
         (*They are the One …, the verb …, the source that called itself*).  A possessive
         (*God's power … on its own*) is NOT the subject; *power* is.
       `self-naming` — the reflexive is the object of a verb of self-reference (call, name,
         describe, reveal, speak of, refer to, show, declare) in a paragraph that names God.  Only
         a someone can be *called* something, so in a God paragraph the referent is God.
       `wrong-form` — the word is *themself*, in any case.  **God's reflexive is *Themselves***
         (Eric, 2026-09-11: *Themself* "is more awkward than *Themselves*"), and this house has no
         other use for the form — so unlike the two paths above, this one needs no antecedent and
         reads INSIDE a quotation too, because a bracketed house substitution (*thy Father which
         seeth in secret [Themselves]*) is this house's word in the source's sentence, not the
         source's own.  A bare *themself* inside a quotation is the source's and is left alone.
         This path takes no antecedent because there is no legitimate singular to protect: the rule
         is about the FORM, and an instance that wants the singular silences it per piece.
     The INTENSIVE *itself* is skipped — *the thing itself*, *the wall itself* — where the word
     emphasizes a noun rather than standing for it; a God-word taking it (*the Father itself*) is
     kept.  Like C and G, a justified hit is silenced by a substring under `pronouns_allow:`.
     H warns, it never refuses: the antecedent is a human call, and the tool is guessing at one.

  WHAT COUNTS AS A SCRIPTURE QUOTATION, for E and F: an italic span `*…*` that is followed by a
  footnote ref whose definition cites the KJV or a book of the Bible, or a blockquote (`> …`)
  carrying such a ref.  For E only, an italic span or blockquote with no ref but King James
  diction (thou / thee / thy / ye / hath / shalt / -eth …) also counts — the Matthew 4:10 miss
  was exactly a span whose ref sat on a different span two sentences earlier.  Each hit says
  which evidence qualified it (`ref:matt4` or `kjv-diction`).  Footnote DEFINITIONS are never
  swept by E or F: a footnote carries the source's own wording unchanged, and that is the
  disclosure.  The three exclusions in the constitution (another organization's fixed text; a
  text quoted as evidence about its translators; any non-Judeo-Christian scripture) are
  judgments the tool cannot make — a hit inside one of those is justified by naming the
  exclusion, exactly as a section-B hit is justified by naming the person.

It REPORTS; it does not edit, and it cannot know a referent.  The operator justifies every hit
by naming who it points at — that is the sweep, and this tool only makes sure it happens.

USAGE
    python3 check_pronouns.py <piece-dir> [--names A,B,C] [--strict]
      --names   comma-separated named figures whose pronouns are theirs (Campbell,Peter,...)
      --strict  exit 3 if any C or D hit remains (for a publish preflight); A, B, E, F, G and H
                always exit 0 because they are lists to be justified, not verdicts — E, F, G and
                H each need a human call on a referent or a speaker, which no rule can make.
    G lists every *Lord* (mixed case) outside a footnote definition — the house sets *the LORD*
    in capitals wherever the word names God (2026-09-07), own prose and quoted scripture alike,
    so each remaining *Lord* is justified by naming what it is instead: the lord in a parable, an emperor called lord, the Lord of another faith, an invented deity, an
    institution's fixed wording, or a title such as the Lord's Prayer. A justified G-hit is silenced the same way as a C-hit, by a substring under
    `pronouns_allow:` in publish.yaml. Footnote definitions are never swept: the note that records
    the King James's wording keeps the King James's own *Lord*.
    A hit in C, D, E, F, G or H whose referent has been named is justified by listing a substring
    of it in the piece's publish.yaml under `pronouns_allow:` — reviewable, and it survives the
    session.  E and F joined the list on 2026-09-10, for the reason D did: a section that refuses
    or warns for ever, with no way to record the ruling, makes every later session re-derive the
    same referent.  Not every E-hit is even a deity pronoun — *He that hath seen Me hath seen the
    Father* is the King James's own sentence-initial capital on *he that* = *whoever*.
    D honors the list for the same reason C does (2026-09-10): D is a PROXIMITY test, so most of
    what it finds is a pronoun for something else standing near a God-word — *God is black, and
    meant it ontologically* (the claim), *the sentence says it takes both* (an expletive). Both
    sections refuse under --strict, so both need a way to say *this referent has been named*;
    without one the only way to clear a D-hit is to reword the draft, which on a published piece
    means editing live prose to satisfy a linter.
EXIT  0 clean or only A/B/E/F/G/H listings · 3 C/D hits under --strict · 1 usage
"""
import os, re, sys

GOD_WORDS = r"(God|the Lord|the LORD|the Father|the Spirit|Christ|Jesus|\bThem\b|\bThey\b|infinite|dream(?:ing|er)?|remembering|the One\b|Someone\b)"
QUOTE_SPAN = re.compile(r"\*[^*]+\*|\"[^\"]+\"|“[^”]+”|> [^\n]+")
SENT_SPLIT = re.compile(r'(?<=[.!?])[\*"”\]\)]*\s+(?=[“"\*\[\(]*[A-Z])')

# A footnote definition "cites scripture" when it names the King James or a book of the Bible.
BIBLE_BOOKS = (
    "Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|"
    "Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of Solomon|Song of Songs|Isaiah|Jeremiah|"
    "Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|"
    "Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|"
    "Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation|"
    "Gen|Ex|Lev|Num|Deut|Ps|Prov|Eccl|Isa|Jer|Ezek|Dan|Matt|Mk|Lk|Jn|Rom|Cor|Gal|Eph|Phil|Col|Thess|Tim|Heb|Rev"
)
SCRIPTURE_REF = re.compile(r"\bKJV\b|King James|\b(?:[1-3]\s*)?(?:" + BIBLE_BOOKS + r")\.?\s+\d+(?::\d+)?")
# A Gospel, and not an epistle of John: "1 John 4:19" is blocked by the lookbehind on a digit.
GOSPEL_REF = re.compile(r"(?<![0-9])(?<![0-9]\s)\b(?:Matthew|Matt|Mark|Mk|Luke|Lk|John|Jn)\.?\s+\d+(?::\d+)?")
KJV_DICTION = re.compile(r"\b(?:thou|thee|thy|thine|ye|hath|doth|saith|shalt|wilt|unto|[a-z]{3,}eth)\b", re.I)
FIRST_PERSON = re.compile(r"\b(?:I|me|my|mine|myself|Me|My|Mine|Myself)\b")
FOOTNOTE_REFS_AFTER = re.compile(r'^[.,;:!?”"\)]*((?:\s*\[\^[^\]]+\])+)')
REF_LABEL = re.compile(r'\[\^([^\]]+)\]')

# --- H: whose reflexive is it? ------------------------------------------------------------
# A God-word in a subject position, for antecedent purposes.  `the One`/`Someone` are here for
# the same reason section C capitalizes them; a possessive (`God's`) is excluded at the match,
# because in *God's power … on its own* the subject is *power*.
# `[Tt]he` because a subject sits at the head of its clause, where English forces the capital.
GOD_SUBJECT = (r"(?:God|[Tt]he LORD|[Tt]he Lord|[Tt]he Father|[Tt]he Son|[Tt]he Spirit|"
               r"[Tt]he Holy Spirit|Christ|Jesus|They|Them|[Tt]he One|Someone)")
REFLEXIVE = re.compile(r"\b(itself|themselves|its own)\b")
# *themself* is not a referent question at all — the house form is *Themselves* (2026-09-11), and
# nothing in this corpus wants the singular.  Matched in any case, and inside a quotation when it
# is bracketed, because a bracket is this house speaking inside the source's sentence.
WRONG_FORM = re.compile(r"\b[Tt]hemself\b")
# Clause boundaries, crude but adequate: punctuation, the coordinators, the common subordinators,
# and existential *there is/are* (which opens a clause of its own inside an *if …* subordinate).
CLAUSE_BREAK = re.compile(
    r'(?:[;:—–]|,)\s*'
    r'|\b(?:because|when|while|whenever|if|unless|though|although|since|so that|where|and|but|or)\s+'
    r'|\bthere\s+(?:is|are|was|were)\s+')
RELATIVIZER = re.compile(r'\b(that|which|who|whom)\b')
DETERMINER = (r"(?:the|a|an|this|these|those|its|his|her|their|our|my|one|no|every|each|some|any)")
# *the thing itself* — the intensive, emphasizing a noun rather than standing for it.  `that`,
# `which` and `who` are deliberately NOT determiners here: *the source that called itself* is a
# relative clause, not a noun phrase, and must not be read as one.
INTENSIVE = re.compile(r'\b' + DETERMINER + r"\s+([\w'’-]+)\s+itself\b", re.I)
# Leading discourse markers to strip before reading a clause's subject.
SUBJ_LEAD = re.compile(r"^(?:and|but|so|then|now|yet|for|because|if|when|while|where|though|"
                       r"although|since|that|as|to|of|in|it is)\s+", re.I)
# Only a someone is *called* something.  In a paragraph that names God, a reflexive under one of
# these verbs is God's — the second of the two 2026-09-10 misses was exactly this shape.
SELF_NAMING = re.compile(
    r"\b(?:call(?:s|ed|ing)?|nam(?:e|es|ed|ing)|describ(?:e|es|ed|ing)|reveal(?:s|ed|ing)?|"
    r"speak(?:s|ing)?\s+of|refer(?:s|red|ring)?\s+to|show(?:s|ed|ing)?|declar(?:e|es|ed|ing))"
    r"\s+(itself|themselves)\b")
GOD_NAMED = re.compile(r"\b(?:God|the LORD|the Lord|the Father|the Spirit|Christ|Jesus|They|Them|the One)\b")
IS_GOD = re.compile(r"^\W*" + GOD_SUBJECT + r"(?!['’]s)\b")
# *They are X, Y, the source that called itself …* — a copular chain whose appositives are the subject.
COPULAR_GOD = re.compile(r"^\W*(?:And |But |So |Yet |Then |Now )?(" + GOD_SUBJECT +
                         r")(?!['’]s)\s+(?:is|are|was|were)\b")

def body_of(piece_dir):
    src = open(os.path.join(piece_dir, 'draft.md'), encoding='utf-8').read()
    src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    if '\n---\n' in src:
        src = src.split('\n---\n', 1)[1]
    return src

def paragraphs(text):
    out = []
    for para in re.split(r'\n\s*\n', text):
        flat = re.sub(r'\s+', ' ', para).strip()
        if flat:
            out.append(flat)
    return out

def sentences(text):
    # Paragraphs first, so a paragraph head is always a sentence head (a forced capital there was
    # missed by a whole-file split); then sentences, allowing the sentence to close in a mark —
    # `*`, `"`, `”`, `]`, `)` — after its terminal punctuation, which is where the other misses were.
    out = []
    for flat in paragraphs(text):
        out.extend(s.strip() for s in SENT_SPLIT.split(flat) if s.strip())
    return out

def sentence_bounds(flat):
    """(start, end) of each sentence in a flattened paragraph — the same split as sentences()."""
    marks = [0] + [m.end() for m in SENT_SPLIT.finditer(flat)] + [len(flat)]
    return list(zip(marks, marks[1:]))

def sentence_at(flat, i):
    """The sentence of a flattened paragraph that contains offset i (same split as sentences())."""
    for a, b in sentence_bounds(flat):
        if a <= i < b:
            return flat[a:b].strip()
    return flat.strip()

def footnote_defs(text):
    """label -> definition text, continuation lines (indented) folded in.  Raw text, not flattened."""
    defs, cur = {}, None
    for line in text.split('\n'):
        m = re.match(r'^\[\^([^\]]+)\]:\s*(.*)$', line)
        if m:
            cur = m.group(1); defs[cur] = m.group(2); continue
        if cur is not None and line[:1] in (' ', '\t') and line.strip():
            defs[cur] += ' ' + line.strip(); continue
        cur = None
    return defs

def ctx(s, m, w=70):
    return '…' + s[max(0, m.start()-w):m.end()+w] + '…'

def quotation_spans(flat, defs):
    """Scripture quotations in one flattened paragraph, as (start, end, text, evidence, gospel).

    evidence is `ref:<label>` when a footnote ref follows the span and its definition cites
    scripture, else `kjv-diction` when the span reads as King James; gospel is True only on the
    ref path, when the definition cites a Gospel.  A span with neither is not a quotation here."""
    spans = []
    if flat.startswith('>'):
        body = re.sub(r'(?:^|(?<=\s))>\s*', '', flat)
        candidates = [(0, len(flat), body, REF_LABEL.findall(body))]
    else:
        candidates = []
        for m in re.finditer(r'\*([^*]+)\*', flat):
            tail = FOOTNOTE_REFS_AFTER.match(flat[m.end():])
            labels = REF_LABEL.findall(tail.group(1)) if tail else []
            candidates.append((m.start(), m.end(), m.group(1), labels))
    for start, end, body, labels in candidates:
        cited = [l for l in labels if l in defs and SCRIPTURE_REF.search(defs[l])]
        if cited:
            gospel = any(GOSPEL_REF.search(defs[l]) for l in cited)
            spans.append((start, end, body, 'ref:' + ','.join(cited), gospel))
        elif KJV_DICTION.search(body):
            spans.append((start, end, body, 'kjv-diction', False))
    return spans

def clause_subject(sent, i):
    """The subject of the clause containing offset `i`, as (text, how).

    A reflexive takes the subject of its own clause, so that is what H asks for.  Inside a
    relative clause the subject is the relative pronoun, which stands for the head noun the
    clause attaches to — so on that path the head noun is returned instead."""
    starts = [m.end() for m in CLAUSE_BREAK.finditer(sent) if m.end() <= i]
    cs = starts[-1] if starts else 0
    clause = sent[cs:i]
    rel = None
    for m in RELATIVIZER.finditer(clause):
        rel = m
    if rel is not None:
        head = clause[:rel.start()].strip()
        if not head:                       # the relativizer opens the clause; its head is behind it
            head = sent[:cs].rstrip().rstrip(',;:—– ')
        head = head.strip().rstrip('*"“”)]').strip()
        m = re.search(r"((?:" + DETERMINER + r"|[A-Z][\w'’]*)\s+(?:[\w'’-]+\s+){0,3}[\w'’-]+|" +
                      GOD_SUBJECT + r")$", head)
        return ((m.group(1) if m else head[-40:]).strip(), 'rel')
    lead = clause.strip().lstrip('*"“”([')
    return (SUBJ_LEAD.sub('', lead).strip()[:60], 'clause')

def reflexive_hits(flat, allow=()):
    """Section H over one flattened paragraph: [(word, evidence, sentence), ...]."""
    hits = []
    god_paragraph = bool(GOD_NAMED.search(flat))
    for a, b in sentence_bounds(flat):
        s = flat[a:b].strip()
        if not s:
            continue
        quoted = [(q.start(), q.end()) for q in QUOTE_SPAN.finditer(s)]
        for m in WRONG_FORM.finditer(s):
            bracketed = s[m.start() - 1:m.start()] == '[' if m.start() else False
            if not bracketed and any(x <= m.start() < y for x, y in quoted):
                continue                                   # the source's own singular, unbracketed
            window = s[max(0, m.start() - 60):m.end() + 60]
            if any(x in window for x in allow):
                continue
            hits.append((m.group(0), 'wrong-form:Themselves', s))
        for m in REFLEXIVE.finditer(s):
            if any(x <= m.start() < y for x, y in quoted):
                continue                                   # the source's own words
            window = s[max(0, m.start() - 60):m.end() + 60]
            if any(x in window for x in allow):
                continue                                   # justified in publish.yaml
            if m.group(1) == 'itself':
                em = INTENSIVE.search(s[max(0, m.start() - 40):m.end()])
                if em and not IS_GOD.match(em.group(1)) and not IS_GOD.match('the ' + em.group(1)):
                    continue                               # *the thing itself* — an intensive
            subj, how = clause_subject(s, m.start())
            evidence = None
            if IS_GOD.match(subj):
                evidence = 'subject' if how == 'clause' else 'rel'
            else:
                cop = COPULAR_GOD.match(s)
                if cop and how == 'rel' and ',' in s[:m.start()] and ';' not in s[:m.start()]:
                    subj, evidence = cop.group(1), 'appositive'
            if evidence is None and god_paragraph:
                lead = s[max(0, m.start() - 20):m.end()]    # the verb, if any, governing THIS reflexive
                sm = SELF_NAMING.search(lead)
                if sm and sm.end() == len(lead):
                    subj, evidence = sm.group(0).rsplit(None, 1)[0], 'self-naming'
            if evidence:
                hits.append((m.group(1), f'{evidence}:{subj[:32]}', s))
    return hits

def load_allow(piece):
    # Justified C-hits live in publish.yaml under `pronouns_allow:` (one substring per line),
    # so the preflight can pass a hit whose referent has been named, and the justification
    # survives in a reviewable file rather than a flag somebody has to remember.
    allow = []
    try:
        in_block = False
        for ln in open(os.path.join(piece, 'publish.yaml'), encoding='utf-8'):
            if re.match(r'^pronouns_allow\s*:', ln):
                in_block = True; continue
            if in_block:
                m = re.match(r'^\s+-\s+(.*?)\s*(?:#.*)?$', ln)
                if m: allow.append(m.group(1).strip()); continue
                if ln.strip() and not ln.startswith(' '): in_block = False
    except FileNotFoundError:
        pass
    return allow

def load_figures(piece):
    """Named people whose pronouns are their own, from publish.yaml `figures:`.

    B's old test was a 120-character lookback, which is far shorter than this desk's prose: a
    passage about Brother Lawrence names him once and then says *he* for two hundred words, so
    85 of 98 hits in *Rising After Falls* read GENERIC? when every one of them was Lawrence.
    A declared figure is sticky for the rest of its PARAGRAPH instead (2026-09-10)."""
    figs = []
    try:
        in_block = False
        for ln in open(os.path.join(piece, 'publish.yaml'), encoding='utf-8'):
            if re.match(r'^figures\s*:', ln):
                in_block = True; continue
            if in_block:
                m = re.match(r'^\s+-\s+(.*?)\s*(?:#.*)?$', ln)
                if m: figs.append(m.group(1).strip()); continue
                if ln.strip() and not ln.startswith(' '): in_block = False
    except FileNotFoundError:
        pass
    return figs

# A God-word standing as an ANTECEDENT — the referent a capitalized pronoun would point back at.
GOD_ANTECEDENT = re.compile(
    r"\b(?:God|the LORD|the Lord|the Father|the Son|the Spirit|the Holy Spirit|Christ|Jesus|"
    r"the One|Someone|They|Them|Their)\b")

def sweep(piece, names=(), allow=None):
    """Run every section over the piece.  Returns {'sentences': n, 'A': [...], ... 'H': [...]}."""
    allow = load_allow(piece) if allow is None else allow
    text = body_of(piece)
    sents = sentences(text)
    A, B, C, D, E, F, G, H, I = [], [], [], [], [], [], [], [], []
    figures = list(names) + [f for f in load_figures(piece) if f not in names]
    fig_re = re.compile(r'\b(' + '|'.join(map(re.escape, figures)) + r')\b') if figures else None

    def last_referent(before):
        """(kind, name) of the nearest antecedent in `before` — 'figure', 'God', or (None, None).

        Nearest wins: whichever of a declared human figure or a God-word was named last is what a
        pronoun after it points back at."""
        fm = None
        if fig_re:
            for fm in fig_re.finditer(before):
                pass
        gm = None
        for gm in GOD_ANTECEDENT.finditer(before):
            pass
        if fm and (not gm or fm.start() > gm.start()): return ('figure', fm.group(1))
        if gm: return ('God', gm.group(0))
        return (None, None)

    # A and B run over PARAGRAPHS, because a referent is sticky for the length of a passage and a
    # sentence-scoped test cannot see that (2026-09-10).
    carried = None            # the last figure named — a PRONOUN's antecedent survives a paragraph break
    for flat in paragraphs(text):
        if re.match(r'^\[\^[^\]]+\]:', flat):
            continue
        for a_i, b_i in sentence_bounds(flat):
            s = flat[a_i:b_i].strip()
            if not s:
                continue
            before = flat[:a_i]
            quoted = [(q.start(), q.end()) for q in QUOTE_SPAN.finditer(s)]
            def in_quote(i): return any(a <= i < b for a, b in quoted)
            # A — a sentence-initial capital that MISLEADS.  English forces the capital on every
            # pronoun at a sentence head; in a house that capitalizes deity pronouns, the one that
            # does damage is a HUMAN's, which then reads as the Son, the Father or the Spirit.  A
            # capital whose nearest antecedent is God is correct and unremarkable, and listing it
            # buried the real ones 485-deep (narrowed 2026-09-10, Eric's call).
            m = re.match(r'^[“"\*\[]*(He|Him|His|They|Them|She|Her)\b', s)
            if m:
                kind, who = last_referent(before)
                window = flat[max(0, a_i - 60):a_i + 60]
                # AMBIGUITY, not merely a human antecedent.  A capital in a paragraph that has just
                # named Pickle or Corey Taylor misleads nobody — the reader knows who is meant, and
                # listing those put 51 correct sentences in front of an operator.  The capital can
                # only be MISREAD where God is also in play in the same paragraph, so both a figure
                # and a God-word must be present, with the figure the nearer (2026-09-10).
                if (kind == 'figure' and GOD_ANTECEDENT.search(before)
                        and not any(x in window for x in allow)):
                    A.append((m.group(1), f'God is named in this paragraph too; nearest is {who}',
                              s[:130]))
            # B — generic masculine, with a declared figure sticky for the rest of its paragraph
            for m in re.finditer(r"\b(himself|him|his|he|any man|one man|the man|a man|man who)\b", s):
                if in_quote(m.start()):
                    continue
                w = s[max(0, m.start()-60):m.end()+60]
                if any(x in w for x in allow):
                    continue
                kind, who = last_referent(before + s[:m.start()])
                # A BARE PRONOUN needs an antecedent, and the last person named is it — so a figure
                # carries across the paragraph break, the way the prose does.  A NOUN PHRASE (*a
                # man*, *the man*, *man who*) introduces its own referent and is never attributed
                # away: that is where a generic masculine actually hides, so those always list.
                # Splitting the two took B from 904 to the 202 worth reading (2026-09-10).
                if m.group(1) in ('he', 'him', 'his', 'himself'):
                    if kind == 'figure' or (kind is None and carried):
                        continue                               # this person actually exists
                B.append(('GENERIC?', m.group(1), ctx(s, m, 60)))
        # Only ANOTHER PERSON displaces the carried antecedent.  God being named does not: a
        # paragraph can be about Brother Lawrence and about God in the same breath — that is what
        # these essays are — and the *he* in it is still Lawrence.  Resetting on a God-word left
        # the carry doing almost nothing, because God is named on nearly every page here.
        if fig_re:
            found = fig_re.findall(flat)
            if found:
                carried = found[-1]

    for s in sents:
        quoted = [(q.start(), q.end()) for q in QUOTE_SPAN.finditer(s)]
        def in_quote(i): return any(a <= i < b for a, b in quoted)
        # C — lowercase oblique for God, or God as a what
        if re.search(GOD_WORDS, s):
            for m in re.finditer(r"\b(the one|someone|whoever|something|a mind|one mind|the mind|a thing|the thing)\b", s):
                if in_quote(m.start()):
                    continue
                window = s[max(0, m.start()-60):m.end()+60]
                if any(a in window for a in allow):
                    continue                                   # justified in publish.yaml
                C.append((m.group(1), ctx(s, m, 70)))
        # D — lowercase deity pronoun right after a God-word, outside quotations
        for m in re.finditer(r"\b(God|the Lord|the LORD|the Father|the Spirit|Christ|Jesus)\b((?:\s+\S+){0,6}?)\s+\b(he|him|his|it|its)\b", s):
            if in_quote(m.start(3)):
                continue
            window = s[max(0, m.start()-60):m.end()+60]
            if any(a in window for a in allow):
                continue                                       # justified in publish.yaml
            D.append((m.group(3), ctx(s, m, 50)))
    # E and F look INSIDE scripture quotations, which A–D deliberately do not.  They run on
    # paragraphs, not sentences, because a quotation can hold more than one sentence and its
    # footnote ref sits after the closing `*`.  Footnote definitions are skipped: a footnote
    # carries the source's own wording unchanged, and that is the disclosure.
    defs = footnote_defs(text)
    for flat in paragraphs(text):
        if re.match(r'^\[\^[^\]]+\]:', flat):
            continue
        for start, end, body, evidence, gospel in quotation_spans(flat, defs):
            def justified(at):
                # Same escape C, D, G and H have (2026-09-10).  Without it a ruled E-hit re-lists
                # for ever and every session re-derives the same referent — and some referents are
                # NEITHER the Son nor the Father: *He that hath seen Me* is the King James's own
                # sentence-initial capital on a generic relative pronoun, *he that* = *whoever*.
                # The window is taken from the SPAN'S OWN text, not from the paragraph: for a
                # blockquote `body` has had its `> ` markers stripped, so a paragraph-relative
                # window drifts two characters per line and silently misses the substring on any
                # quotation more than a few lines long (measured on *The Towel*, 2026-09-10).
                w = body[max(0, at - 60):at + 60]
                return any(a in w for a in allow)
            for m in re.finditer(r"\b(He|Him|His|Himself)\b", body):
                if justified(m.start()):
                    continue
                E.append((m.group(1), evidence, sentence_at(flat, start + m.start())))
            if gospel and FIRST_PERSON.search(body):
                for m in re.finditer(r"\b(me|my|mine|myself)\b", body):
                    if justified(m.start()):
                        continue
                    F.append((m.group(1), evidence, sentence_at(flat, start + m.start())))
        # G — a mixed-case *Lord* anywhere in a body paragraph (prose or quotation): the house
        # writes LORD wherever the word names God, so each of these names something else or is a miss.
        for m in re.finditer(r"\bLord\b", flat):
            window = flat[max(0, m.start()-60):m.end()+60]
            if any(a in window for a in allow):
                continue                                       # justified in publish.yaml
            G.append(ctx(flat, m, 70))
        # H — a lowercase reflexive whose antecedent is God.  It runs on the paragraph because the
        # self-naming path asks whether the paragraph names God at all, which a sentence cannot say.
        H.extend(reflexive_hits(flat, allow))
        # I — a creature rendered as a *what*.  The publication's position is that God, any person
        # and any ANIMAL is a *who*; the pronoun rules forbid *it* but govern only PRONOUNS, and the
        # *what* rule covered God and people but not animals — so "Something came through here," said
        # of whatever a dog is smelling, was compliant with both and shipped through a draft, two
        # critiques and a compose (2026-09-10: an animal is never a thing).
        # This flags the WORD and asks about the REFERENT, because the same sentence can hold both:
        # in "the dog dug something up by the fence" the dog is a who and the bone is a what.
        for m in re.finditer(r"\b(Something|something|Anything|anything|Nothing|nothing)\b", flat):
            window = flat[max(0, m.start()-90):m.end()+90]
            if not CREATURE_NEAR.search(window):
                continue
            if any(a in window for a in allow):
                continue                                       # justified in publish.yaml
            I.append(ctx(flat, m, 75))
    return {'sentences': len(sents), 'A': A, 'B': B, 'C': C, 'D': D, 'E': E, 'F': F, 'G': G,
            'H': H, 'I': I}

CREATURE_NEAR = re.compile(
    r"\b(dog|dogs|cat|cats|animal|animals|creature|creatures|bird|birds|puppy|horse|horses|"
    r"sheep|lamb|ox|donkey|pig|pigs|fox|deer|bat|bats|bee|bees|leash|paw|paws|nose|snout|"
    r"smell|smelling|scent|sniff|sniffing|fur|tail|whimper|bark|barked|barking|"
    r"frightened|sick|hungry|wounded|grief|flinch)\b", re.I)

def _clip(s, n=200):
    return s if len(s) <= n else s[:n] + '…'

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__); sys.exit(1)
    piece = args[0].rstrip('/')
    names = []
    for a in sys.argv[1:]:
        if a.startswith('--names='):
            names = [n.strip() for n in a[8:].split(',') if n.strip()]
    if '--names' in sys.argv:
        i = sys.argv.index('--names'); names = [n.strip() for n in sys.argv[i+1].split(',')]
    strict = '--strict' in sys.argv
    r = sweep(piece, names)
    # The deity sections (A, C–H) are one publication's house conventions, not the desk's
    # (2026-09-15): a registry entry without `deity_conventions: true` is not asked them. B and I —
    # an invented person is they/them, a creature is a who — hold for every text.
    deity = True
    try:
        import publications
        deity = publications.deity_conventions(piece)
    except Exception:                                   # noqa: BLE001 — no registry tool: stay strict
        pass
    if not deity:
        for k in 'ACDEFGH':
            r[k] = []
    A, B, C, D, E, F, G, H, I = (r[k] for k in 'ABCDEFGHI')
    print(f"check_pronouns — {os.path.basename(piece)}: {r['sentences']} sentences")
    if not deity:
        print("   (its publication keeps no deity conventions: sections A and C–H are not asked)")
    print(f"\nA. a sentence-initial capital that READS AS DEITY but points at a person ({len(A)}):")
    for w, why, c in A: print(f"   {w:5s} {why:52s} {_clip(c,120)}")
    print(f"\nB. masculine / 'a man' to justify ({len(B)}; {sum(1 for t,_,_ in B if t.startswith('GENERIC'))} unexplained):")
    for t, w, c in B: print(f"   {t} {w:8s} {c}")
    print(f"\nC. lowercase oblique near a God-word, or God as a *what* ({len(C)}):")
    for w, c in C: print(f"   {w:9s} {c}")
    print(f"\nD. lowercase deity pronoun outside a quotation ({len(D)}):")
    for w, c in D: print(f"   {w:4s} {c}")
    print(f"\nE. capitalized He/Him/His inside a scripture quotation — justify each as the Son, or bracket [Them] for the Father ({len(E)}):")
    for w, ev, c in E: print(f"   {w:8s} {ev:14s} {_clip(c)}")
    print(f"\nF. lowercase me/my/mine inside a Gospel quotation — the Son's own pronouns take the capital ({len(F)}):")
    for w, ev, c in F: print(f"   {w:8s} {ev:14s} {_clip(c)}")
    print(f"\nG. mixed-case *Lord* in the body — the house writes LORD wherever it names God; justify each as a figure, another tradition, a fixed text or a title ({len(G)}):")
    for c in G: print(f"   {_clip(c)}")
    print(f"\nH. the reflexive for God — the house never lets God be a *what*, and the form is *Themselves*, never *itself* and never *themself* ({len(H)}):")
    for w, ev, c in H: print(f"   {w:8s} {ev:42s} {_clip(c)}")
    print(f"\nI. a creature as a *what* — the house makes God, any person AND any animal a *who*; justify each as naming a thing rather than a creature ({len(I)}):")
    for c in I: print(f"   {_clip(c)}")
    if strict:
        if E or F or G or H or I:
            print("\nSTRICT: E/F/G/H/I hits are warnings — each needs a referent or speaker named; not refused.")
        if C or D:
            print("\nSTRICT: C/D hits remain — justify or fix before compose.")
            sys.exit(3)

if __name__ == '__main__':
    main()
