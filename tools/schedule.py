#!/usr/bin/env python3
"""
schedule.py — a piece can be finished and still not be due yet.

A piece is sealed on one day and meant to go live on another. Between those two days
there is nothing in the desk that knows the difference, and every tool that publishes
will happily publish. This is the thing that knows: one field in the manifest, one
moment, and a refusal before it.

  publish_at: 2026-09-15 09:00 America/New_York

Read it with `state()`, or from the command line:

  python3 tools/schedule.py check <piece>...     exit 4 while a piece is embargoed
  python3 tools/schedule.py list                 every piece that carries the field
  python3 tools/schedule.py due [--within 48h]   what opens inside the window (or has)
  python3 tools/schedule.py set <piece> "<moment>"
  python3 tools/schedule.py clear <piece>
  python3 tools/schedule.py runbook <piece>      the prompt a scheduled wake-up needs
  python3 tools/schedule.py arm <piece> --task … --does … --reviewed "<who, when>"
  python3 tools/schedule.py armed                what is armed across the desk
  python3 tools/schedule.py record <piece> --outlet … --where … --approved "<who, when>"

RECORD THE ACT, NOT ONLY THE INTENT. A native schedule lives on Substack's or LinkedIn's
side, where nothing here can see it — so a tool reading `publish_at` alone says "its own
scheduler has it for Tuesday" whether the schedule was set or forgotten. `record` writes
the act into the manifest (when, where, against what evidence, approved by whom), and
`outlet_audit` reads an outlet that is due with no record as NOT SCHEDULED.

THE ORDER IS NOT NEGOTIABLE: compose the drafts, let the author read them, THEN arm. A
scheduled publication fires with nobody watching, so the reading has to have happened
first (Eric, 2026-09-11: "we don't set the schedule until the drafts are reviewed and
approved"). `arm` refuses without `--reviewed`, and records who approved it.

WHAT IT GATES, AND WHAT IT DELIBERATELY DOES NOT.

  REFUSES   Anything that makes the piece public or queues it to become public:
            `md_to_site.py` will not export an embargoed piece into the store bundle
            (exit 12), which is what a site reads -- UNLESS that outlet is configured
            `on_schedule: immediate` (see OUTLETS below), in which case it exports and
            says so.

  WARNS     Composing. A Substack draft is private and a LinkedIn file is a file on
            this Mac; composing early is how a scheduled publication is prepared at
            all, so `md_to_substack.py` and `md_to_linkedin.py` print the embargo and
            carry on. The `publish` skill reads this tool before it clicks anything.

  KNOWS     Nothing about clocks. It compares a moment to now, and the refusal is the
            whole mechanism. Nothing here fires on its own, on purpose: an unattended
            publish is a decision the author makes explicitly elsewhere (for Substack,
            its own scheduler, set in the composer once the draft is ready).

WHY A TIMEZONE IS REQUIRED. "2026-09-15" is not a moment, it is a date in whatever zone
the reader happens to be in, and an embargo that opens at a different instant depending
on who asks is not an embargo. A moment with no zone is refused (exit 2) rather than
assumed. Write the zone you mean: `America/New_York` reads correctly across a DST
boundary, where a fixed `-04:00` quietly does not.

OUTLETS: THE MOMENT IS NOT THE SAME QUESTION FOR ALL OF THEM, AND THE REASON IS
EDITORIAL. One piece has one `publish_at:`, but the outlets it names do not all want to
wait for it. The quire websites are the CANONICAL publication and drive no traffic, so a
piece belongs there as soon as it is finished; the feed outlets -- Substack, LinkedIn --
are where regular publishing does work, and they wait for the moment (Eric, 2026-09-11:
"we should be able to configure an outlet for immediate publishing when scheduling ...
the websites (using quire) are the canonical publications and do not drive traffic").

So the policy is a property of the OUTLET, in the instance's registry:

  outlets:
    alignmentfellowship:
      on_schedule: immediate     # canonical: publishes as soon as the piece is ready
    substack:
      on_schedule: at_moment     # the default, and may be left unwritten

`outlet_policy()` reads it and FAILS CLOSED: a missing file, an unknown outlet, an
unreadable registry or an unrecognised value all answer `at_moment`. The safe direction
is refusing to publish, so nothing about a typo or an absent PyYAML can turn an embargo
off. An exemption also has to be SAID -- `embargo_note()` is what a caller prints --
because a piece published before its moment with nothing on the terminal is
indistinguishable from a piece that never had an embargo at all.

Exit codes: 0 open (or no field) · 1 usage · 2 a malformed or zoneless moment ·
4 at least one piece is still embargoed.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:                                            # pragma: no cover
    ZoneInfo = None

HERE = os.path.dirname(os.path.abspath(__file__))
FIELD = 'publish_at'

# `2026-09-15 09:00 America/New_York`, `2026-09-15T09:00:00-04:00`, `2026-09-15 09:00 UTC`.
_MOMENT = re.compile(
    r'^(?P<date>\d{4}-\d{2}-\d{2})'
    r'(?:[ T](?P<time>\d{2}:\d{2}(?::\d{2})?))?'
    r'(?:\s*(?P<zone>Z|UTC|[A-Za-z]+/[A-Za-z_+\-]+|[+-]\d{2}:?\d{2}))?$')


class Malformed(ValueError):
    """The moment cannot be read, or carries no zone."""


def parse_moment(raw):
    """'2026-09-15 09:00 America/New_York' -> an aware datetime. Raises Malformed."""
    s = str(raw).strip().strip('"\'')
    s = s.split('#', 1)[0].strip()
    m = _MOMENT.match(s)
    if not m:
        raise Malformed(f'cannot read {raw!r} as a moment — '
                        f'write it as `2026-09-15 09:00 America/New_York`')
    zone = m.group('zone')
    if not zone:
        raise Malformed(f'{raw!r} names no timezone, so it is a date and not a moment — '
                        f'write it as `{m.group("date")} '
                        f'{m.group("time") or "09:00"} America/New_York`')
    time = m.group('time') or '00:00'
    if len(time) == 5:
        time += ':00'
    naive = datetime.fromisoformat(f'{m.group("date")}T{time}')

    if zone in ('Z', 'UTC'):
        return naive.replace(tzinfo=timezone.utc)
    if zone[0] in '+-':
        zone = zone if ':' in zone else f'{zone[:3]}:{zone[3:]}'
        hh, mm = int(zone[1:3]), int(zone[4:6])
        off = timedelta(hours=hh, minutes=mm)
        return naive.replace(tzinfo=timezone(-off if zone[0] == '-' else off))
    if ZoneInfo is None:
        raise Malformed('this Python has no zoneinfo; write a numeric offset instead')
    try:
        return naive.replace(tzinfo=ZoneInfo(zone))
    except Exception:
        raise Malformed(f'{zone!r} is not a timezone this machine knows')


def read_field(piece_dir):
    """The raw `publish_at:` line from a manifest, or None. Deliberately a line-reader
    rather than a YAML load: this runs inside tools that parse the manifest their own
    way, and one field should not drag a parser in behind it."""
    path = os.path.join(piece_dir, 'publish.yaml')
    if not os.path.exists(path):
        return None
    for line in open(path, encoding='utf-8'):
        if line.startswith(f'{FIELD}:'):
            value = line.split(':', 1)[1]
            value = value.split('#', 1)[0].strip()
            return value or None
    return None


def state(piece_dir, now=None):
    """('none'|'open'|'embargoed', moment_or_None). Raises Malformed on a bad field."""
    raw = read_field(piece_dir)
    if raw is None:
        return 'none', None
    moment = parse_moment(raw)
    now = now or datetime.now(timezone.utc)
    return ('open' if now >= moment else 'embargoed'), moment


IMMEDIATE = 'immediate'
AT_MOMENT = 'at_moment'


def policy_for(outlets, outlet):
    """The same question for a caller that has already loaded the registry (md_to_site
    does, as `o.outlets`). Fails closed: anything but the exact string `immediate` on
    that one outlet answers AT_MOMENT."""
    if not outlet or not isinstance(outlets, dict):
        return AT_MOMENT
    cfg = outlets.get(outlet)
    if not isinstance(cfg, dict):
        return AT_MOMENT
    return IMMEDIATE if str(cfg.get('on_schedule')).strip().lower() == IMMEDIATE else AT_MOMENT


def outlet_policy(outlets_path, outlet):
    """What an outlet does with an embargo: IMMEDIATE, or AT_MOMENT (the default).

    Fails closed in every direction. No path, no file, no PyYAML, no such outlet, no
    key, or a value this function does not recognise all answer AT_MOMENT, because the
    safe answer is the one that refuses to publish. Only the exact string `immediate`
    turns the moment off, and only for the outlet that carries it."""
    if not outlets_path or not outlet:
        return AT_MOMENT
    try:
        # Imported here, not at the top: this module is deliberately a line-reader for
        # the manifest, and one optional dependency should not become a hard one. No
        # PyYAML means AT_MOMENT, which is the refusing answer.
        import yaml as _yaml
        with open(outlets_path, encoding='utf-8') as f:
            reg = _yaml.safe_load(f) or {}
    except Exception:
        return AT_MOMENT
    return policy_for(reg.get('outlets') or {}, outlet)


def embargo_note(piece_dir, outlet, now=None):
    """What an exempt caller must PRINT. An early publication with nothing said about it
    reads exactly like a piece that never had a moment."""
    try:
        st, moment = state(piece_dir, now)
    except Malformed:
        return None
    if st != 'embargoed':
        return None
    return (f'{os.path.basename(piece_dir.rstrip("/"))} is embargoed until '
            f'{fmt(moment)} ({human_delta(moment, now)}), and {outlet} is configured '
            f'`on_schedule: immediate` — publishing it there now, on purpose. The '
            f'moment still governs every outlet that is not.')


def refuse_if_embargoed(piece_dir, now=None, policy=AT_MOMENT):
    """For a caller that publishes. Returns a refusal string, or None to proceed.

    `policy` comes from `outlet_policy()`; IMMEDIATE proceeds, and the caller is
    expected to print `embargo_note()` when it does."""
    try:
        st, moment = state(piece_dir, now)
    except Malformed as e:
        return f'{os.path.basename(piece_dir.rstrip("/"))}: {FIELD} is unusable — {e}'
    if st != 'embargoed' or policy == IMMEDIATE:
        return None
    return (f'{os.path.basename(piece_dir.rstrip("/"))} is embargoed until '
            f'{fmt(moment)} ({human_delta(moment, now)}). '
            f'Publishing it now is the one thing the field exists to prevent; '
            f'clear or move it with `schedule.py set` if the date really changed.')


def fmt(moment):
    return moment.strftime('%Y-%m-%d %H:%M %Z').strip()


def human_delta(moment, now=None):
    now = now or datetime.now(timezone.utc)
    secs = (moment - now).total_seconds()
    past = secs < 0
    secs = abs(secs)
    if secs < 3600:
        said = f'{int(secs // 60)}m'
    elif secs < 86400:
        said = f'{int(secs // 3600)}h {int(secs % 3600 // 60)}m'
    else:
        said = f'{int(secs // 86400)}d {int(secs % 86400 // 3600)}h'
    return f'{said} ago' if past else f'in {said}'


# --------------------------------------------------------------------------- CLI


def pieces_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(d, 'pieces')):
            return os.path.join(d, 'pieces')
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def resolve(ref):
    if os.path.isdir(ref):
        return os.path.abspath(ref)
    import corpus
    found = corpus.find(corpus.desk_root(), ref)
    if found:
        return found
    sys.exit(f'no such piece: {ref}')


def all_pieces():
    import corpus
    return [d for _s, d, _k in corpus.texts(corpus.desk_root())]


def parse_window(s):
    m = re.match(r'^(\d+)\s*([hd])$', s.strip(), re.I)
    if not m:
        sys.exit(f'--within wants something like 48h or 7d, not {s!r}')
    n = int(m.group(1))
    return timedelta(hours=n) if m.group(2).lower() == 'h' else timedelta(days=n)


def cmd_check(args):
    bad = 0
    for ref in args.pieces:
        pdir = resolve(ref)
        refusal = refuse_if_embargoed(pdir)
        if refusal:
            print(f'EMBARGOED  {refusal}')
            bad += 1
        else:
            st, moment = state(pdir)
            print(f'open       {os.path.basename(pdir)}'
                  + (f' — opened {fmt(moment)} ({human_delta(moment)})' if moment else
                     f' — no {FIELD}'))
    return 4 if bad else 0


def cmd_list(args):
    rows, bad = [], 0
    for pdir in all_pieces():
        raw = read_field(pdir)
        if raw is None:
            continue
        try:
            st, moment = state(pdir)
            rows.append((st.upper(), os.path.basename(pdir), fmt(moment),
                         human_delta(moment)))
            bad += st == 'embargoed'
        except Malformed as e:
            rows.append(('MALFORMED', os.path.basename(pdir), raw, str(e)))
            bad += 1
    if not rows:
        print(f'no piece carries {FIELD}')
        return 0
    w = max(len(r[1]) for r in rows)
    for st, slug, moment, note in sorted(rows, key=lambda r: r[2]):
        print(f'{st:10} {slug:{w}}  {moment}  ({note})')
    return 4 if any(r[0] == 'EMBARGOED' for r in rows) else 0


def cmd_due(args):
    window = parse_window(args.within)
    now = datetime.now(timezone.utc)
    found = 0
    for pdir in all_pieces():
        if read_field(pdir) is None:
            continue
        try:
            st, moment = state(pdir, now)
        except Malformed:
            continue
        if moment <= now + window:
            found += 1
            print(f'{"OPEN" if st == "open" else "opens"}  {os.path.basename(pdir)}  '
                  f'{fmt(moment)} ({human_delta(moment, now)})')
    if not found:
        print(f'nothing due within {args.within}')
    return 0


RUNBOOK = """\
Publication day for {slug} — "{title}".

You are a fresh session with no memory of how this was arranged. Everything you need is here
and in the piece; read pieces/{slug}/README.md first, and do not improvise past this list.

The desk is {root}. The moment is {moment}; `python3 framework/tools/schedule.py check {slug}`
must say OPEN before anything public happens. If it says EMBARGOED, stop: you woke early.

IF YOU ARE RUNNING LATE — the app was closed and this fired at launch instead of on time — say
so in your first line, then check what already went out before you touch anything: the Substack
post and the LinkedIn article are on their own platforms' schedulers and may already be live.

1. `python3 framework/tools/lease.py acquire {slug} --what "publication day"`.
2. Gates: `schedule.py check`, `check_verified.py`, `check_links.py`, `check_refs.py` — any
   refusal stops the run and is reported, not worked around.
3. The canonical goes first. Cutover steps 1-3 in the README: copy original_published_at to
   published_at, record blog_url and canonical, export the bundle, publish it to the store, then
   remove {slug} from TAKEN_DOWN_FOR_REDRAFT in muffinlabs-web/next.config.ts and deploy — a
   config redirect beats the page route, so the piece cannot appear at its URL until that lands.
4. Verify the live page yourself before saying it is up, on a cache-busted URL.
5. Substack and LinkedIn publish on their own schedulers. Confirm rather than assume: if the
   Substack post is not live within ten minutes of the moment, say so and stop — do NOT click
   Publish yourself, because that decision was made against a draft the author reviewed and
   whatever went wrong needs a human.
6. LinkedIn's Article copy links the canonical, so it is composed only after step 4 passes. If it
   is still a draft, leave it and say so.
7. Record it: post_url / blog_url / linkedin_url in publish.yaml, README and the dashboard
   fragment to published, an append-only log entry, `dashboard.py sync`, release the lease, and
   commit by path (never `git add` then a bare commit).
8. Notify the author with: what is live, what is not, and what is left for them (the Note is
   always theirs — never post it).
"""


def cmd_runbook(args):
    """Print the self-contained prompt for the scheduled wake-up.

    A scheduled task starts with no memory of the conversation that created it, so the prompt
    has to carry the piece, the moment, the order and the gates. It is generated from the
    manifest rather than typed, so moving `publish_at` cannot leave a stale moment inside a
    prompt nobody re-reads."""
    pdir = resolve(args.piece)
    st, moment = state(pdir)
    if not moment:
        sys.exit(f'{os.path.basename(pdir)} has no {FIELD} — nothing to arm')
    title = ''
    for line in open(os.path.join(pdir, 'publish.yaml'), encoding='utf-8'):
        if line.startswith('title:'):
            title = line.split(':', 1)[1].strip().strip('"\'')
            break
    print(RUNBOOK.format(slug=os.path.basename(pdir), title=title, moment=fmt(moment),
                         root=os.path.dirname(os.path.dirname(os.path.abspath(pdir)))))
    return 0


def scheduled_record(piece_dir, outlet):
    """-> {at, set, where, approved} for a native schedule actually set on this outlet, or None.

    THE DIFFERENCE THIS EXISTS FOR: `publish_at` says when a piece is DUE, which is intent, and
    a tool that reports "its own scheduler has it for Tuesday" from intent alone says exactly the
    same sentence whether the schedule was set or forgotten. A native schedule lives on
    Substack's or LinkedIn's side, where nothing here can see it, so the desk records the ACT —
    when it was set, where, and against what evidence — and an outlet that is due with no record
    reads as NOT SCHEDULED rather than as fine."""
    path = os.path.join(piece_dir, 'publish.yaml')
    if not os.path.exists(path):
        return None
    block, cur, rec = False, None, {}
    for line in open(path, encoding='utf-8'):
        raw = line.rstrip('\n')
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if not raw.startswith((' ', '\t')):
            block = raw.split(':', 1)[0].strip() == 'scheduled'
            cur = None
            continue
        if not block:
            continue
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        if indent <= 2 and stripped.endswith(':'):
            cur = stripped[:-1].strip()
            if cur == outlet:
                rec = {}
            continue
        if cur == outlet and ':' in stripped:
            k, v = stripped.split(':', 1)
            rec[k.strip()] = v.split('#', 1)[0].strip()
    return rec or None


def cmd_record(args):
    """Write down that a native schedule was set on one outlet."""
    pdir = resolve(args.piece)
    moment = parse_moment(args.at) if args.at else None
    if not moment:
        st, moment = state(pdir)
        if not moment:
            sys.exit(f'{os.path.basename(pdir)} has no {FIELD} and no --at — nothing to record')
    if not args.approved:
        sys.exit('refusing to record: --approved is required. A native schedule publishes with\n'
                 '  nobody watching, so the reading has to have happened first; name who approved\n'
                 '  it and when.')
    path = os.path.join(pdir, 'publish.yaml')
    src = open(path, encoding='utf-8').read()
    from datetime import date
    entry = (f'  {args.outlet}:\n'
             f'    at: {fmt(moment)}\n'
             f'    set: {date.today().isoformat()}\n'
             f'    where: {args.where}\n'
             f'    evidence: {args.evidence or "none recorded"}\n'
             f'    approved: {args.approved}\n')
    if re.search(r'(?m)^scheduled:$', src):
        # replace this outlet's entry if it has one, else append to the block
        pat = re.compile(r'(?ms)^  %s:\n(?:    .*\n)*' % re.escape(args.outlet))
        if pat.search(src):
            src = pat.sub(entry, src, count=1)
        else:
            src = re.sub(r'(?m)^scheduled:$', 'scheduled:\n' + entry.rstrip('\n'), src, count=1)
    else:
        src = src.rstrip('\n') + (
            '\n\n# Native schedules actually SET on a platform, per outlet — the act, not the\n'
            '# intent. `publish_at` says when the piece is due; this says a scheduler was told.\n'
            'scheduled:\n' + entry)
    open(path, 'w', encoding='utf-8').write(src)
    print(f'{os.path.basename(pdir)}: {args.outlet} scheduled for {fmt(moment)} '
          f'({args.where}) — recorded')
    return 0


def cmd_arm(args):
    """Record that a wake-up has been scheduled for this piece, and by what.

    The task itself is created by the session (the scheduler lives in the app, not in this
    tool). What this writes is the desk's record of it, so `armed` can answer the question
    a week later and a moved moment shows up as a contradiction rather than a surprise.

    `--reviewed` is required, and it is the rule rather than a formality: **the schedule is
    not set until the drafts are reviewed and approved** (Eric, 2026-09-11). A scheduled
    publication fires with nobody watching, so the reading has to have happened first — and
    the composing is what produces the thing to read, which puts it before the arming and
    never after. Naming who approved it makes the order auditable in the manifest."""
    pdir = resolve(args.piece)
    st, moment = state(pdir)
    if not moment:
        sys.exit(f'{os.path.basename(pdir)} has no {FIELD} — set one before arming')
    if not args.reviewed:
        sys.exit('refusing to arm: --reviewed is required.\n'
                 '  The schedule is not set until the drafts are reviewed and approved, because\n'
                 '  a scheduled publication fires with nobody watching. Compose the drafts, let\n'
                 '  the author read them, then arm with --reviewed "<who, when>".')
    path = os.path.join(pdir, 'publish.yaml')
    src = open(path, encoding='utf-8').read()
    # The key is `armed:`, NOT `scheduled:`. `record` owns `scheduled:` for the per-outlet
    # record of a platform schedule, and writing a second top-level `scheduled:` here made a
    # duplicate key: YAML lets the later one win, so arming a piece SILENTLY ERASED the record
    # of which platform had been told — the one thing that distinguishes a schedule that was
    # set from one that was forgotten. Measured on false-light, 2026-09-11.
    #
    # And every value is emitted as a JSON string, which is a valid YAML double-quoted scalar.
    # `--does` is a sentence written by a human and a sentence contains colons: `does: … live:
    # confirms …` broke the manifest so completely that PyYAML would not read it at all, and
    # `armed` could not see the damage because it reads this block with a regex.
    q = json.dumps
    block = (f'# A scheduled wake-up is armed for this piece. The moment of record is {FIELD};\n'
             f'# this block is only the note that something was told to fire near it. Armed only\n'
             f'# after the drafts were read and approved — see `approved`.\n'
             f'armed:\n'
             f'  task: {q(args.task)}\n'
             f'  fires: {q(args.fires or fmt(moment))}\n'
             f'  does: {q(args.does)}\n'
             f'  approved: {q(args.reviewed)}\n')
    src = re.sub(r'(?ms)^# A scheduled wake-up.*?^  approved: .*?$\n', '', src)
    src = src.rstrip('\n') + '\n\n' + block
    # A manifest writer that can emit invalid YAML is the deeper fault, so prove the result
    # parses before it lands. Everything on this desk reads publish.yaml; leaving it broken is
    # worse than refusing to arm.
    try:
        import yaml as _yaml
        _yaml.safe_load(src)
    except Exception as e:
        sys.exit(f'refusing to arm: the result would not parse as YAML — {e}\n'
                 f'  nothing was written. This is a bug in this tool, not in your input.')
    open(path, 'w', encoding='utf-8').write(src)
    print(f'{os.path.basename(pdir)}: armed — {args.task} fires {args.fires or fmt(moment)}')
    return 0


def cmd_armed(args):
    rows = []
    for pdir in all_pieces():
        p = os.path.join(pdir, 'publish.yaml')
        if not os.path.exists(p):
            continue
        src = open(p, encoding='utf-8').read()
        # `armed:` is the current key; the older shape wrote `scheduled:` and is still read so
        # a piece armed before the fix is not invisible here.
        m = (re.search(r'(?ms)^armed:\n  task: (.+?)\n  fires: (.+?)\n  does: (.+?)$', src)
             or re.search(r'(?ms)^scheduled:\n  task: (.+?)\n  fires: (.+?)\n  does: (.+?)$', src))
        if m:
            # the values are YAML double-quoted scalars now; show them as the words they are
            def unq(v):
                v = v.strip()
                if v[:1] == '"':
                    try:
                        return json.loads(v)
                    except Exception:
                        return v
                return v
            rows.append((os.path.basename(pdir), unq(m.group(1)), unq(m.group(2)), unq(m.group(3))))
    if not rows:
        print('nothing armed')
        return 0
    w = max(len(r[0]) for r in rows)
    for slug, task, fires, does in rows:
        print(f'{slug:{w}}  {task}  fires {fires}  — {does}')
    return 0


def required_companions_missing(pdir):
    """-> [(role, why)] its publication requires and this piece has not got. Arming the schedule
    is the approval moment (docs/SCHEDULING.md), and it is the last one where writing a Note is
    cheap — after it, the next person to touch the piece is publishing it."""
    try:
        import publications as pb
        root = os.path.dirname(os.path.dirname(os.path.abspath(pdir)))
        pubs, _ = pb.load(root)
        if not pubs:                                        # a one-publication desk asks nothing
            return []
        return pb.missing_companions(pb.read_manifest(pdir), pubs, pdir, require_live=False)
    except Exception:
        return []                                           # never let this block a schedule


def cmd_set(args):
    pdir = resolve(args.piece)
    moment = parse_moment(args.moment)                      # refuse before writing
    missing = [] if getattr(args, 'no_companions', False) else required_companions_missing(pdir)
    if missing:
        slug = os.path.basename(pdir)
        print(f'{slug}: NOT scheduled — this publication requires a companion this piece '
              f'has not got:', file=sys.stderr)
        for role, why in missing:
            print(f'    {role}: {why}', file=sys.stderr)
        print('\nWrite it (a note is `note.md` with a form/style header, declared as\n'
              '`companions: {note: note.md}`), or say why it is exempt with\n'
              '`companions_exempt: {note: "<reason>"}`. To arm the schedule anyway, pass\n'
              '--no-companions. The check is here because arming the schedule is the approval,\n'
              'and a Note found missing on publication morning is found too late.',
              file=sys.stderr)
        return 5
    path = os.path.join(pdir, 'publish.yaml')
    lines = open(path, encoding='utf-8').read().split('\n')
    line = f'{FIELD}: {args.moment.strip()}'
    for i, ln in enumerate(lines):
        if ln.startswith(f'{FIELD}:'):
            lines[i] = line
            break
    else:
        note = ('# Not due yet. Nothing may be made public before this moment; '
                'schedule.py is the gate.')
        for i, ln in enumerate(lines):
            if ln.startswith('publication:'):
                lines[i:i] = [note, line]
                break
        else:
            lines.insert(1, note)
            lines.insert(2, line)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'{os.path.basename(pdir)}: {FIELD} = {fmt(moment)} ({human_delta(moment)})')
    return 0


def cmd_clear(args):
    pdir = resolve(args.piece)
    path = os.path.join(pdir, 'publish.yaml')
    lines = open(path, encoding='utf-8').read().split('\n')
    kept = [ln for ln in lines if not ln.startswith(f'{FIELD}:')]
    if len(kept) == len(lines):
        print(f'{os.path.basename(pdir)}: no {FIELD} to clear')
        return 0
    open(path, 'w', encoding='utf-8').write('\n'.join(kept))
    print(f'{os.path.basename(pdir)}: {FIELD} cleared — nothing gates this piece now')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('check', help='exit 4 while any named piece is embargoed')
    c.add_argument('pieces', nargs='+')
    c.set_defaults(fn=cmd_check)

    c = sub.add_parser('list', help='every piece carrying the field')
    c.set_defaults(fn=cmd_list)

    c = sub.add_parser('due', help='what opens inside a window')
    c.add_argument('--within', default='48h')
    c.set_defaults(fn=cmd_due)

    c = sub.add_parser('runbook', help='the self-contained prompt for a scheduled wake-up')
    c.add_argument('piece')
    c.set_defaults(fn=cmd_runbook)

    c = sub.add_parser('arm', help='record that a wake-up is scheduled (after the drafts are approved)')
    c.add_argument('piece')
    c.add_argument('--task', required=True, help='the scheduler\'s id for it')
    c.add_argument('--does', required=True, help='one line: what it will do when it fires')
    c.add_argument('--fires', help='when, if not the publish_at moment itself')
    c.add_argument('--reviewed', help='who approved the drafts, and when — REQUIRED')
    c.set_defaults(fn=cmd_arm)

    c = sub.add_parser('record', help='write down a native schedule that was actually set')
    c.add_argument('piece')
    c.add_argument('--outlet', required=True)
    c.add_argument('--where', required=True, help="the platform's own control, named")
    c.add_argument('--evidence', help='the post/article id or url the schedule sits on')
    c.add_argument('--at', help='the moment, if not the piece\'s publish_at')
    c.add_argument('--approved', help='who approved the drafts, and when — REQUIRED')
    c.set_defaults(fn=cmd_record)

    c = sub.add_parser('armed', help='what is armed across the desk')
    c.set_defaults(fn=cmd_armed)

    c = sub.add_parser('set', help='write the field')
    c.add_argument('piece')
    c.add_argument('moment')
    c.add_argument('--no-companions', action='store_true',
                   help='arm the schedule even though a required companion is missing')
    c.set_defaults(fn=cmd_set)

    c = sub.add_parser('clear', help='remove the field')
    c.add_argument('piece')
    c.set_defaults(fn=cmd_clear)

    args = ap.parse_args()
    try:
        return args.fn(args)
    except Malformed as e:
        print(f'refusing: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
