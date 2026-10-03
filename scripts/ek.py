#!/usr/bin/env python3
"""Emerald Kaizo lookups over the bundled EK docs (stdlib only).

  ek.py mon <pokemon> [--level N]   EK type and weaknesses, level-up learnset, and the doc's
                                    ability, base-stat, evolution and held-item changes; with
                                    --level, the moveset a wild one has at that level and
                                    what comes next
  ek.py move <move>                 EK changes to the move and every Pokémon that learns it
  ek.py where <pokemon>             wild, gift and diving encounters with level, rate and
                                    danger-move flag
  ek.py wild <place>                every wild Pokémon at a place with the moveset it will
                                    have at its listed levels and danger-move flags
  ek.py trainer <name or place>     trainer teams from the Mastersheet, plus EK changes to
                                    the moves they use
  ek.py rival [--starter S] [--gender G] [--place P]
                                    May/Brendan teams; S and G are the player's starter/gender
  ek.py area <place>                the whole Mastersheet section for a location
  ek.py guide [<place|item|"badge N">]
                                    vanilla story progression from the Prima guide: where to
                                    go, what to do, where HMs and key items come from; no
                                    argument prints the outline
  ek.py search <text>               plain text search across every doc
  ek.py next <trainer> --me <your pokémon> [--last P] [--gone P,P]
  ek.py next --rival --starter S --gender G --place P --me <your pokémon>
                                    which Pokémon the trainer's AI sends in after one faints,
                                    from the EK AI Switch Calculator's rules

Names are fuzzy-matched, so typos and missing punctuation are fine.
"""
import argparse
import csv
import difflib
import re
import signal
import sys
from pathlib import Path

REF = Path(__file__).resolve().parent.parent / 'references'
DASHES = re.compile(r'^-{3,}$')
BANNER = re.compile(r'^(?:-{3,}|>{3,})$')  # a place name sits between two of these
MON_LINE = re.compile(r'\bLv\.?\s?\d+')
ENC_LINE = re.compile(r'^([A-Z][A-Za-z ]+?)(?: \[([^\]]+)\])? \(([^)]*)\): (.*%.*)$')


def key(s):
    s = s.lower().replace('♀', 'f').replace('♂', 'm').replace('é', 'e')
    return re.sub(r'[^a-z0-9]', '', s)


def read(name):
    return (REF / name).read_text(encoding='utf-8').splitlines()


def resolve(query, names, what):
    """Return the one name that best matches query, or exit listing candidates."""
    q = key(query)
    by_key = {}
    for n in names:
        by_key.setdefault(key(n), n)
    if q in by_key:
        return by_key[q]
    pref = [n for k, n in by_key.items() if k.startswith(q)]
    if len(pref) == 1:
        return pref[0]
    if pref:
        sys.exit(f'"{query}" could mean more than one {what}: {", ".join(pref)}. Ask which one.')
    scored = sorted(((difflib.SequenceMatcher(None, q, k).ratio(), n) for k, n in by_key.items()), reverse=True)
    best, runner = scored[0], (scored[1] if len(scored) > 1 else (0, ''))
    if best[0] >= 0.75 and best[0] - runner[0] >= 0.05:  # a clear typo winner
        print(f'(read "{query}" as {best[1]})')
        return best[1]
    close = [n for r, n in scored[:6] if r >= 0.6]
    if close:
        sys.exit(f'"{query}" could mean more than one {what}: {", ".join(close)}. Ask which one.')
    sys.exit(f'No {what} in the EK docs matches "{query}".')


# ---------- learnsets ----------

def load_learnsets():
    mons, cur = [], None
    for line in read('learnsets.txt'):
        m = re.match(r'^(\d+)\.\s+(.+?)\s*$', line)
        if m:
            cur = {'num': int(m[1]), 'name': m[2], 'moves': [], 'notes': []}
            mons.append(cur)
            continue
        if cur is None or not line.strip():
            continue
        m = re.match(r'^Lv\.\s*(\d+)\s+(.+?)\s*$', line)
        if m:
            cur['moves'].append((int(m[1]), m[2]))
        else:
            cur['notes'].append(line.strip())
    return mons


def find_mon(mons, query):
    if query.strip().isdigit():
        n = int(query)
        for m in mons:
            if m['num'] == n:
                return m
    name = resolve(query, [m['name'] for m in mons], 'Pokémon')
    return next(m for m in mons if m['name'] == name)


def wild_moveset(moves, level):
    """Gen 3 default moveset: walk the learnset in order up to `level`; skip moves
    already known; once four are known, drop the oldest for each new one."""
    known = []
    for lvl, mv in moves:
        if lvl > level:
            break
        if key(mv) in (key(k) for k in known):
            continue
        if len(known) == 4:
            known.pop(0)
        known.append(mv)
    return known


# ---------- move changes ----------

def load_move_changes(mons):
    lines = [l.strip() for l in read('move-changes.txt')[1:] if l.strip()]
    names = {key(mv): mv for m in mons for _, mv in m['moves']}
    index = {}  # move key -> change lines whose subject is that move
    for l in lines:
        # Only the subject is indexed: "Psywave ... same effect as Seismic Toss" changes
        # Psywave, not Seismic Toss. Renames ("Old -> New (...)") index both names.
        if '->' in l:
            subjects = [re.split(r'\s*\(|\s+\d|\s+⅓|\s+High', side.strip())[0] for side in l.split('->')]
        else:
            head = re.split(r'\s+(?:is|has|have|are|now|all|always)\b|\s+\d', l)[0]
            subjects = re.split(r',\s*(?:and\s+)?|\s+and\s+', head)
        for nm in (s.strip() for s in subjects):
            if nm:
                names.setdefault(key(nm), nm)  # renamed and TM-only moves aren't in learnsets
                index.setdefault(key(nm), []).append(l)
    return names, index


# ---------- encounters ----------

def load_encounters(mons):
    rows = list(csv.DictReader(open(REF / 'encounters.csv', encoding='utf-8')))
    by_key = {key(m['name']): m['name'] for m in mons}
    for r in rows:
        if r['method'] == 'Note':
            r['mon'] = None
            continue
        k = key(r['pokemon'])
        hit = k if k in by_key else next(iter(difflib.get_close_matches(k, list(by_key), n=1, cutoff=0.8)), None)
        r['mon'] = by_key.get(hit)
    return rows


# ---------- mastersheet ----------

def mastersheet_sections():
    """Split the Mastersheet into (location, lines) in walkthrough order. Gyms, the
    Elite Four and similar sit between >>> banners and count as their own place."""
    L = read('mastersheet.txt')
    sections, i = [], 0
    cur = ('Start', [])
    while i < len(L):
        if BANNER.match(L[i].strip()) and i + 2 < len(L) and BANNER.match(L[i + 2].strip()) \
                and L[i + 1].strip() not in ('', '~'):
            cur = (L[i + 1].strip(), [])
            sections.append(cur)
            i += 3
            continue
        cur[1].append(L[i])
        i += 1
    return sections


def trainer_blocks(sections):
    """Yield (location, trainer name, [mon lines]) for every team in the Mastersheet."""
    for loc, lines in sections:
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ''
            if s and not MON_LINE.search(s) and not s.startswith(('>', '-')) and MON_LINE.search(nxt):
                team, j = [], i + 1
                while j < len(lines) and MON_LINE.search(lines[j]):
                    team.append(lines[j].strip())
                    j += 1
                yield loc, s, team
                i = j
            else:
                i += 1


VANILLA_RECOIL = ['Take Down', 'Double-Edge', 'Volt Tackle', 'Submission']


def danger_moves(changes):
    """Moves that lose a wild encounter: it flees, faints itself, or can KO itself."""
    recoil = set(VANILLA_RECOIL)
    for k, lines in changes.items():
        if any('recoil' in l.lower() for l in lines):
            for l in lines:
                if 'recoil' in l.lower():
                    head = l.split('->')[-1] if '->' in l else l
                    for nm in re.split(r',\s*(?:and\s+)?|\s+and\s+', re.split(r'\s+(?:is|has|have|are)\b|\s+\d|\s*\(|\s+⅓', head)[0]):
                        recoil.add(nm.strip())
    d = {key(m): 'Teleport' for m in ['Teleport']}
    d.update({key(m): 'Roar/Whirlwind' for m in ['Roar', 'Whirlwind']})
    d.update({key(m): 'Selfdestruct/Explosion/Memento' for m in ['Selfdestruct', 'Explosion', 'Memento']})
    d.update({key(m): 'Recoil move' for m in recoil if m})
    return d


def levels_of(text):
    """'15' -> [15]; '15-16' -> [15, 16]; '19, 43' -> [19, 43]; '' -> []"""
    return sorted({int(n) for n in re.findall(r'\d+', str(text))})


def print_team_changes(mon_lines):
    """List the EK move changes behind the moves in these trainer lines."""
    _, changes = load_move_changes(load_learnsets())
    out, hp = [], False
    for line in mon_lines:
        if ':' not in line:
            continue
        for mv in line.split(':', 1)[1].split(','):
            mv = re.sub(r'\[.*$|\+\d+\s*$', '', mv).strip()
            if re.match(r'^HP \w+$', mv):
                hp, mv = True, 'Hidden Power'
            for l in changes.get(key(mv), []):
                if l not in out:
                    out.append(l)
    if hp:
        print('\n"HP Grass" etc. = Hidden Power of that type.')
    if out:
        print('EK move changes for moves on these teams:')
        for l in out:
            print(f'  {l}')


# ---------- commands ----------

def cmd_mon(a):
    mons = load_learnsets()
    m = find_mon(mons, a.name)
    _, changes = load_move_changes(mons)
    print(f"#{m['num']} {m['name']} — EK level-up learnset")
    d = switch_data()
    typed = {key(n): n for n in d['mons']}.get(key(m['name']))
    if typed:
        print(f'  Type: {type_label(d, typed)}')
        names = {0: 'Immune to', 2: 'Takes ¼ from', 5: 'Resists', 20: 'Weak to', 40: '4x weak to'}
        for x, ts in sorted(matchups(d, typed).items(), reverse=True):
            print(f'  {names.get(x, f"{x / 10:g}x from")}: {", ".join(ts)}')
    changed = []
    for lvl, mv in m['moves']:
        flag = ''
        if key(mv) in changes:
            flag = '  *EK-changed'
            if mv not in changed:
                changed.append(mv)
        print(f'  Lv {lvl:>3}  {mv}{flag}')
    if m['notes']:
        print('Doc notes (EK changes to this Pokémon; absent = vanilla Emerald):')
        for n in m['notes']:
            print(f'  {n}')
    if a.level is not None:
        lv = a.level
        print(f'\nAt Lv {lv}:')
        print(f"  Wild/default moveset: {', '.join(wild_moveset(m['moves'], lv)) or '(none)'}")
        now = [mv for l, mv in m['moves'] if l == lv]
        if now:
            print(f"  Learns at exactly Lv {lv}: {', '.join(now)}")
        nxt = [(l, mv) for l, mv in m['moves'] if l > lv]
        if nxt:
            print('  Next: ' + ', '.join(f'{mv} (Lv {l})' for l, mv in nxt[:4]))
        else:
            print('  Nothing more to learn by level-up.')
    if changed:
        print('\nEK move changes affecting this learnset:')
        seen = set()
        for mv in changed:
            for l in changes[key(mv)]:
                if l not in seen:
                    seen.add(l)
                    print(f'  {l}')


def cmd_move(a):
    mons = load_learnsets()
    names, changes = load_move_changes(mons)
    mv = resolve(a.name, list(names.values()), 'move')
    k = key(mv)
    print(f'{mv}')
    if changes.get(k):
        print('EK changes (Move Changes doc):')
        for l in changes[k]:
            print(f'  {l}')
    else:
        print('No EK change listed: vanilla Gen 3 stats.')
    learners = [(m['name'], l) for m in mons for l, x in m['moves'] if key(x) == k]
    if learners:
        print(f'Learned by level-up ({len(learners)}):')
        for name, l in sorted(learners, key=lambda t: (t[1], t[0])):
            print(f'  Lv {l:>3}  {name}')
    else:
        print('No Pokémon learns it by level-up in EK.')


def cmd_where(a):
    mons = load_learnsets()
    m = find_mon(mons, a.name)
    rows = [r for r in load_encounters(mons) if r['mon'] == m['name']]
    _, changes = load_move_changes(mons)
    danger = danger_moves(changes)
    ms_levels, extra = {}, []  # Mastersheet's own encounter tables, to catch disagreements
    covered = {key(r['location']) for r in rows}
    for loc, lines in mastersheet_sections():
        for l in lines:
            e = ENC_LINE.match(l.strip())
            if not (e and re.search(r'\b' + re.escape(m['name']) + r'\b', e[4])):
                continue
            method = 'Grass' if e[1] == 'Cave' else e[1]
            ms_levels[(key(loc), key(e[2] or ''), key(method))] = e[3]
            if key(loc) not in covered:
                pct = re.search(r'(\d+%) ' + re.escape(m['name']) + r'\b', e[4])
                area = f" [{e[2]}]" if e[2] else ''
                extra.append(f"  {loc}{area} — {e[1]} Lv {e[3]} — {pct[1] if pct else '?'}")
    print(f"Where to find {m['name']} (Detailed Encounters sheet, walkthrough order):")
    for r in rows:
        place = r['location'] + (f" {r['area']}" if r['area'] else '')
        lvl = f" Lv {r['level']}" if r['level'] else ''
        # warn if either the sheet's colour code or the computed wild moveset says so
        flags = {r['danger_flag']} - {''}
        flags |= {danger[key(mv)] for l in levels_of(r['level']) for mv in wild_moveset(m['moves'], l) if key(mv) in danger}
        flag = f"  ⚠ knows {', '.join(sorted(flags))}" if flags else ''
        hint = f"  ({r['hint']})" if r['hint'] else ''
        other = ms_levels.get((key(r['location']), key(r['area']), key(r['method'])))
        diff = f"  (Mastersheet says Lv {other})" if other and levels_of(other) != levels_of(r['level']) else ''
        print(f"  {place} — {r['method']}{lvl} — {r['rate']}{flag}{hint}{diff}")
    if extra:
        print('Also listed in the Mastersheet:')
        print('\n'.join(extra))
    if not rows and not extra:
        print('  No wild encounter listed. Try: ek.py search "' + m['name'] + '" (gift, static or trade).')


def cmd_trainer(a):
    q = key(a.query)
    blocks = list(trainer_blocks(mastersheet_sections()))
    hits = [b for b in blocks if q in key(b[1])] or [b for b in blocks if q in key(b[0])]
    if not hits:  # typo: score the query against each word of each trainer name
        score = lambda name: max(difflib.SequenceMatcher(None, q, key(w)).ratio() for w in name.split() + [name])
        best = max(score(b[1]) for b in blocks)
        if best >= 0.8:
            hits = [b for b in blocks if score(b[1]) == best]
            print(f'(read "{a.query}" as {hits[0][1]})')
    if not hits:
        names = sorted({b[1] for b in blocks} | {b[0] for b in blocks})
        close = difflib.get_close_matches(a.query, names, n=6, cutoff=0.5)
        sys.exit(f'No trainer or place matches "{a.query}".' + (f' Closest: {", ".join(close)}' if close else ''))
    for loc, name, team in hits[:40]:
        print(f'{name} — {loc}')
        for t in team:
            print(f'  {t}')
        if re.search(r'\b(May|Brendan)\b', name):
            print(f'  {RIVAL_NOTE}')
    if len(hits) > 40:
        print(f'... {len(hits) - 40} more; narrow the query.')
    print_team_changes([t for _, _, team in hits[:40] for t in team])


RIVAL_NOTE = ('(Rival teams depend on your starter and gender; the Mastersheet shows one version. '
              'Use: ek.py rival --starter S --gender G --place P)')


def rival_variants():
    """(location, 'Male, Mudkip', [team lines]) for every rival battle in rival-teams.txt."""
    L = read('rival-teams.txt')
    i, loc, variants = 0, None, []
    while i < len(L):
        s = L[i].strip()
        if DASHES.match(s) and i + 2 < len(L) and DASHES.match(L[i + 2].strip()):
            loc = L[i + 1].strip(); i += 3; continue
        if re.match(r'^(Male|Female), \w+$', s):
            team, j = [], i + 1
            while j < len(L) and not L[j].strip():
                j += 1
            while j < len(L) and MON_LINE.search(L[j]):
                team.append(L[j].strip()); j += 1
            variants.append((loc, s, team)); i = j; continue
        i += 1
    return variants


def pick_rivals(a):
    out = []
    for loc, var, team in rival_variants():
        gender, starter = var.split(', ')
        if a.starter and key(a.starter) != key(starter):
            continue
        g = {'boy': 'm', 'girl': 'f'}.get(key(a.gender or ''), key(a.gender or '')[:1])
        if g and not key(gender).startswith(g):
            continue
        if a.place and key(a.place) not in key(loc):
            continue
        out.append((loc, gender, starter, team))
    return out


def cmd_rival(a):
    shown = []
    for loc, gender, starter, team in pick_rivals(a):
        print(f'{loc} — player {gender}, chose {starter}')
        for t in team:
            print(f'  {t}')
        shown += team
    print_team_changes(shown)


def cmd_wild(a):
    mons = load_learnsets()
    by_name = {m['name']: m for m in mons}
    _, changes = load_move_changes(mons)
    danger = danger_moves(changes)
    q = key(a.place)
    rows = [r for r in load_encounters(mons) if r['mon'] and (q in key(r['location']) or q in key(r['location'] + r['area']))]
    if not rows:
        locs = sorted({r['location'] for r in load_encounters(mons)})
        close = difflib.get_close_matches(a.place, locs, n=6, cutoff=0.5)
        sys.exit(f'No encounter table matches "{a.place}".' + (f' Closest: {", ".join(close)}' if close else ''))
    last = None
    for r in rows:
        place = f"{r['location']} {r['area']}".strip() + f" — {r['method']}"
        if place != last:
            print(f"\n{place}" + (f"  ({r['hint']})" if r['hint'] else ''))
            last = place
        lv = levels_of(r['level'])
        sets = [(l, wild_moveset(by_name[r['mon']]['moves'], l)) for l in (lv[:1] + lv[-1:] if lv else [])]
        if len(sets) == 2 and sets[0][1] == sets[1][1]:
            sets = sets[1:]
        bad = sorted({danger[key(mv)] for _, ms in sets for mv in ms if key(mv) in danger} | ({r['danger_flag']} - {''}))
        flag = f"  ⚠ {', '.join(bad)}" if bad else ''
        print(f"  {r['mon']} {r['rate']} Lv {r['level'] or '?'}{flag}")
        for l, ms in sets:
            print(f"    Lv {l}: {', '.join(ms)}")
    print('\n⚠ = knows a move that can lose you the encounter (flee, self-KO or recoil KO).')


def cmd_area(a):
    q = key(a.place)
    secs = [s for s in mastersheet_sections() if q in key(s[0])]
    if not secs:
        names = [s[0] for s in mastersheet_sections()]
        close = difflib.get_close_matches(a.place, names, n=6, cutoff=0.5)
        sys.exit(f'No Mastersheet section matches "{a.place}".' + (f' Closest: {", ".join(close)}' if close else ''))
    for loc, lines in secs:
        print(f'===== {loc} =====')
        print('\n'.join(l for l in lines).strip('\n'))
        print()
    print_team_changes([l.strip() for _, lines in secs for l in lines if MON_LINE.search(l)])


def guide_sections():
    """progression.md as [(milestone, heading, text)]; '## ' opens a milestone, '### ' a place."""
    out, milestone, head, buf = [], '', None, []
    for line in read('progression.md'):
        if line.startswith('## ') or line.startswith('### '):
            if head is not None:
                out.append((milestone, head, '\n'.join(buf).strip()))
            if line.startswith('## '):
                milestone, head = line[3:].strip(), line[3:].strip()
            else:
                head = line[4:].strip()
            buf = [line]
        elif head is not None:
            buf.append(line)
    if head is not None:
        out.append((milestone, head, '\n'.join(buf).strip()))
    return out


def ek_notes_for(heading):
    """The Mastersheet's EK notes (* lines and their indented follow-ons) for places named in a heading."""
    h = key(re.sub(r'\(.*?\)', '', heading))
    out, seen, prev = [], {}, 'Start'
    for loc, lines in mastersheet_sections():
        seen[loc] = seen.get(loc, 0) + 1
        label = loc if seen[loc] == 1 else f'{loc} (later visit, after {prev})'
        prev = loc
        k = key(re.sub(r'\(.*?\)', '', loc))
        if not k or k not in h:
            continue
        keep = False
        for l in lines:
            s = l.strip()
            if s.startswith('*') and not s.startswith('*Superboss'):
                keep = True
                out.append(f'  {label}: {s.lstrip("*").strip()}')
            elif keep and not s:
                continue  # blank lines sit inside multi-line notes (TM price lists, Regi steps)
            elif keep and l.startswith(' '):
                out.append(f'    {s}')
            else:
                keep = False
    return list(dict.fromkeys(out))


def cmd_guide(a):
    secs = guide_sections()
    if not a.query:
        for m, h, _ in secs:
            print(h if h == m else f'  {h}')
        return
    q = key(a.query)
    b = re.search(r'badges?\D{0,8}(\d)|(\d)\s*badges?', a.query.lower())
    if b:  # "badge 3", "after 3 badges": everything from that milestone to the next
        n = b[1] or b[2]
        hits = [x for x in secs if re.search(r'\bbadges?\s*' + n + r'\b', x[0].lower())]
    else:
        hits = [x for x in secs if x[1] != x[0] and q in key(re.sub(r'\(.*?\)', '', x[1]))] \
            or [x for x in secs if x[1] == x[0] and q in key(x[0])]
        if hits and hits[0][1] == hits[0][0]:  # a milestone name: include its places
            hits = [x for x in secs if x[0] == hits[0][0]]
    if not hits:  # full text, e.g. an item name
        hits = [x for x in secs if a.query.lower() in x[2].lower() or q in key(x[2])]
    if not hits:
        heads = [h for _, h, _ in secs]
        close = difflib.get_close_matches(a.query, heads, n=5, cutoff=0.4)
        sys.exit(f'Nothing in the progression guide matches "{a.query}".' + (f' Closest: {", ".join(close)}' if close else ''))
    print('(Prima 2005 vanilla guide: story and items only; the Mastersheet wins where they differ)')
    last_m = None
    for m, h, text in hits[:8]:
        if m != last_m and h != m:
            print(f'\n[{m}]')
        last_m = m
        print(text)
        notes = ek_notes_for(h) if h != m else []
        if notes:
            print('- **EK Mastersheet notes (these win):**')
            print('\n'.join(notes))
    if len(hits) > 8:
        print(f'... {len(hits) - 8} more sections; narrow the query.')


def cmd_search(a):
    q = a.text.lower()
    n = 0
    for fname in ('learnsets.txt', 'move-changes.txt', 'mastersheet.txt', 'rival-teams.txt', 'encounters.csv',
                  'progression.md'):
        ctx = ''
        L = read(fname)
        for i, l in enumerate(L):
            if fname == 'learnsets.txt' and re.match(r'^\d+\.\s', l):
                ctx = l.strip()
            if fname == 'progression.md' and l.startswith('#'):
                ctx = l.lstrip('#').strip()
            if fname in ('mastersheet.txt', 'rival-teams.txt') and i + 1 < len(L) and DASHES.match(l.strip()) \
                    and i + 2 < len(L) and DASHES.match(L[i + 2].strip()):
                ctx = L[i + 1].strip()
            if q in l.lower():
                n += 1
                if n <= 80:
                    where = f' [{ctx}]' if ctx and ctx != l.strip() else ''
                    print(f'{fname}:{i + 1}{where}: {l.strip()}')
    if n > 80:
        print(f'... {n - 80} more hits; narrow the search.')
    if not n:
        print(f'No hits for "{a.text}".')


# ---------- types and AI switch-ins (EK AI Switch Calculator) ----------
# The Gen 3 AI picks a replacement in two passes (pokeemerald GetMostSuitableMonToSwitchInto),
# and the calculator sheet models both:
#  1. typing: score each remaining Pokémon by how hard YOUR Pokémon's types hit it, highest
#     first, and send the first one that has a super-effective move against you;
#  2. otherwise, the move with the best type effectiveness x STAB, where STAB is judged on the
#     Pokémon that just left the field (the game reuses that slot's stats and types);
#  3. otherwise, the next one in party order.
# Ties go to the earlier party slot. Fixed-damage moves (power 1 in the game data) are skipped
# in pass 2, as the game does.

SE, NVE, NO_EFFECT = 1, 2, 4
_switch = None


def switch_data():
    global _switch
    if _switch is None:
        import json
        _switch = json.loads((REF / 'ai-switch.json').read_text(encoding='utf-8'))
    return _switch


def types_of(d, mon):
    t1, t2, lev = d['mons'][mon]
    return t1, t2, lev


def type_label(d, mon):
    t1, t2, lev = types_of(d, mon)
    s = t1.title() + ('' if t1 == t2 else '/' + t2.title())
    return s + (', Levitate' if lev else '')


def chart_mult(d, atk, t1, t2, foresight=False):
    """Battle effectiveness (in tenths) of an attacking type on a defender's two types."""
    x = 10
    for a, df, m, fs in d['chart']:
        if fs and foresight:
            break
        if a == atk:
            if df == t1:
                x = x * m // 10
            if df == t2 and t1 != t2:
                x = x * m // 10
    return x


def matchups(d, mon):
    t1, t2, lev = types_of(d, mon)
    out = {}
    for atk in sorted({row[0] for row in d['chart']}):
        x = 0 if (lev and atk == 'GROUND') else chart_mult(d, atk, t1, t2)
        if x != 10:
            out.setdefault(x, []).append(atk.title())
    return out


def type_score(d, your, cand):
    """Pass 1: how hard your types hit the candidate, in tenths. A single-type attacker fills
    both type slots, so its matchup counts twice (the game does the same)."""
    y1, y2, _ = types_of(d, your)
    c1, c2, _ = types_of(d, cand)
    v = 10
    for atk in (y1, y2):
        for a, df, m, fs in d['chart']:
            if a == atk:
                if df == c1:
                    v = v * m // 10
                if df == c2 and c1 != c2:
                    v = v * m // 10
    return v


def move_flags(d, move, your, foresight):
    """The game's super/not-very-effective flags for a move on your Pokémon; status moves
    (power 0) never count as super effective."""
    mtype, status, _ = d['moves'][move]
    t1, t2, lev = types_of(d, your)
    if lev and mtype == 'GROUND':
        return NO_EFFECT
    flags = 0
    for a, df, m, fs in d['chart']:
        if fs and foresight:
            break
        if a != mtype:
            continue
        for hit in (df == t1, df == t2 and t1 != t2):
            if not hit:
                continue
            if m == 0:
                flags = (flags | NO_EFFECT) & ~(SE | NVE)
            elif status or flags & NO_EFFECT:
                pass
            elif m == 5:
                flags = flags & ~SE if flags & SE else flags | NVE
            elif m == 20:
                flags = flags & ~NVE if flags & NVE else flags | SE
    return flags


def move_score(d, move, your, prev, foresight):
    """Pass 2: type effectiveness x STAB, with STAB judged on the Pokémon that just left."""
    mtype, _, power1 = d['moves'][move]
    if power1:
        return 0
    t1, t2, lev = types_of(d, your)
    x = 1.5 if mtype in types_of(d, prev)[:2] else 1.0
    if lev and mtype == 'GROUND':  # the AI's damage maths ignores Levitate
        return x
    return x * chart_mult(d, mtype, t1, t2, foresight) / 10


def ai_next(d, party, your, last, gone, foresight, partner):
    lo, hi = (0, 3) if partner and last < 3 else (3, 6) if partner else (0, 6)
    valid = [i for i in range(lo, min(hi, len(party))) if i != last and i not in gone]
    if not valid:
        return None, 'nothing left'
    tried = set()
    while True:
        best, pick = 0, None
        for i in valid:
            if i not in tried:
                s = type_score(d, your, party[i]['mon'])
                if best < s:
                    best, pick = s, i
        if pick is None:
            break
        se = [m for m in party[pick]['moves'] if move_flags(d, m, your, foresight) & SE]
        if se:
            mult = {2: '¼', 5: '½', 10: '1', 20: '2', 40: '4'}.get(best, f'{best / 10:g}')
            return pick, f'your type hits it {mult}x, and it has {", ".join(se)} (super effective on you)'
        tried.add(pick)
    best, pick, via = 0, None, ''
    for i in valid:
        for m in party[i]['moves']:
            s = move_score(d, m, your, party[last]['mon'], foresight)
            if best < s:
                best, pick, via = s, i, m
    if pick is not None:
        return pick, f'nothing with a super-effective move fits, so the AI goes by type and STAB: {via}'
    return valid[0], 'nothing scores, so the next one in party order'


def find_trainer(d, query, pick):
    q = key(query)
    ts = d['trainers']
    hits = [t for t in ts if q in key(t['name'])] or [t for t in ts if q in key(t['name'] + t['place'])]
    if not hits:
        names = sorted({t['name'] for t in ts})
        close = difflib.get_close_matches(query, names, n=6, cutoff=0.5)
        sys.exit(f'No trainer in the AI Switch Calculator matches "{query}".'
                 + (f' Closest: {", ".join(close)}' if close else ''))
    if len(hits) > 1 and not pick:
        lines = [f'  {n}. {t["name"]} — {t["place"]} (leads {t["party"][0]["mon"]})' for n, t in enumerate(hits[:30], 1)]
        sys.exit(f'"{query}" matches {len(hits)} trainers; rerun with --pick N:\n' + '\n'.join(lines))
    if pick and not 1 <= pick <= len(hits):
        sys.exit(f'--pick must be 1 to {len(hits)}.')
    return hits[(pick or 1) - 1]


TEAM_LINE = re.compile(r"^\s*(.+?)(?:\([mf]\))?\s*Lv\.?\s?\d+(?:\s*@[^:;]+)?\s*[:;]\s*(.*?)\s*(?:\[.*)?$")
MOVE_ALIAS = {'xscissors': 'X-Scissor', 'hijumpkick': 'High Jump Kick', 'faintattack': 'Feint Attack'}


def party_from_lines(d, lines):
    """Turn Mastersheet/rival team lines into the switch predictor's party format."""
    mons = {key(m): m for m in d['mons']}
    moves = {key(m): m for m in d['moves']}
    party, unknown = [], []
    for line in lines:
        m = TEAM_LINE.match(line)
        if not m:
            continue
        k = key(m.group(1))
        close = [] if k in mons else difflib.get_close_matches(k, list(mons), 1, 0.8)
        sp = mons.get(k) or (mons[close[0]] if close else None)
        if not sp:
            unknown.append(m.group(1)); continue
        mv = []
        for name in [x.strip() for x in m.group(2).split(',') if x.strip() and not x.strip().startswith('--')]:
            k = key(name)
            hit = moves.get(k) or MOVE_ALIAS.get(k)
            if not hit:
                close = difflib.get_close_matches(k, list(moves), 1, 0.85)
                hit = moves[close[0]] if close else None
            if hit:
                mv.append(hit)
            else:
                unknown.append(name)
        party.append({'mon': sp, 'moves': mv})
    if unknown:
        print('(not in the calculator data, ignored: ' + ', '.join(unknown) + ')')
    return party


def nicknames():
    """Nickname -> species from references/my-run.md (lines like '- **Federer**: Marshtomp, ...')."""
    path = REF / 'my-run.md'
    if not path.exists():
        return {}
    team = re.search(r'^## Team.*?(?=^## |\Z)', path.read_text(encoding='utf-8'), re.M | re.S)
    pairs = re.findall(r"^- \*\*(.+?)\*\*: ([A-Z][\w'. -]*?)[,.]", team.group(0) if team else '', re.M)
    return {key(n): sp for n, sp in pairs}


def resolve_mine(d, name):
    sp = nicknames().get(key(name))
    if sp and sp in d['mons']:
        if key(sp) != key(name):
            print(f'({name} = {sp})')
        return sp
    return resolve(name, list(d['mons']), 'Pokémon')


def party_slots(d, party, names, what):
    slots = []
    for n in names:
        mon = resolve(n, [p['mon'] for p in party], what)
        slot = next((i for i, p in enumerate(party) if p['mon'] == mon and i not in slots), None)
        if slot is None:
            sys.exit(f'{mon} is listed more times than the team has it.')
        slots.append(slot)
    return slots


def cmd_next(a):
    d = switch_data()
    if a.rival:
        found = pick_rivals(a)
        if len(found) != 1:
            opts = '\n'.join(f'  {loc} — player {g}, chose {s}' for loc, g, s, _ in found[:20]) or '  (none)'
            sys.exit(f'--rival needs --starter, --gender and --place that match exactly one rival battle. Matches:\n{opts}')
        loc, g, s, lines = found[0]
        t = {'name': f'Rival ({g} player, {s})', 'place': loc, 'partner': False, 'party': party_from_lines(d, lines)}
    else:
        if not a.trainer:
            sys.exit('Name a trainer, or use --rival with --starter, --gender and --place.')
        t = find_trainer(d, a.trainer, a.pick)
        if re.search(r'\b(May|Brendan)\b', t['name']):
            print(RIVAL_NOTE.replace('ek.py rival', 'ek.py next --rival --me ...'))
    party = t['party']
    split = lambda s: [x for x in re.split(r'\s*,\s*', s or '') if x]
    gone = party_slots(d, party, split(a.gone), f'Pokémon on {t["name"]}\'s team')
    lasts = party_slots(d, party, split(a.last), f'Pokémon on {t["name"]}\'s team') if a.last else \
        [i for i in range(len(party)) if i not in gone]
    yours = [resolve_mine(d, y) for y in split(a.me)]
    print(f'{t["name"]} — {t["place"]}: who the AI sends in next')
    print(f'  Leads with {party[0]["mon"]}. Team: ' + ', '.join(p['mon'] for p in party))
    if gone:
        print('  Already down: ' + ', '.join(party[i]['mon'] for i in gone))
    if t['partner']:
        print('  Partner battle: each trainer replaces from their own three.')
    for your in yours:
        print(f'\nWith your {your} ({type_label(d, your)}) on the field:')
        for last in lasts:
            nxt, why = ai_next(d, party, your, last, set(gone) | {last}, a.foresight, t['partner'])
            if nxt is None:
                print(f'  {party[last]["mon"]} goes down → that was the last one.')
            else:
                print(f'  {party[last]["mon"]} goes down → {party[nxt]["mon"]}: {why}')
    print('\nSource: EK AI Switch Calculator (Gen 3 switch AI). It predicts replacements after a faint;'
          ' it does not cover the AI switching out mid-turn.')


def main():
    if hasattr(signal, 'SIGPIPE'):  # not on Windows
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet exit when piped into head
    sys.stdout.reconfigure(encoding='utf-8')  # Windows pipes default to cp1252, which lacks →
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('mon'); s.add_argument('name'); s.add_argument('--level', '-l', type=int)
    s.set_defaults(f=cmd_mon)
    s = sub.add_parser('move'); s.add_argument('name'); s.set_defaults(f=cmd_move)
    s = sub.add_parser('where'); s.add_argument('name'); s.set_defaults(f=cmd_where)
    s = sub.add_parser('trainer'); s.add_argument('query'); s.set_defaults(f=cmd_trainer)
    s = sub.add_parser('rival'); s.add_argument('--starter'); s.add_argument('--gender'); s.add_argument('--place')
    s.set_defaults(f=cmd_rival)
    s = sub.add_parser('wild'); s.add_argument('place'); s.set_defaults(f=cmd_wild)
    s = sub.add_parser('area'); s.add_argument('place'); s.set_defaults(f=cmd_area)
    s = sub.add_parser('guide'); s.add_argument('query', nargs='?'); s.set_defaults(f=cmd_guide)
    s = sub.add_parser('search'); s.add_argument('text'); s.set_defaults(f=cmd_search)
    s = sub.add_parser('next'); s.add_argument('trainer', nargs='?')
    s.add_argument('--rival', action='store_true', help='use the rival doc team (with --starter, --gender, --place)')
    s.add_argument('--starter'); s.add_argument('--gender'); s.add_argument('--place')
    s.add_argument('--me', required=True, help='your Pokémon on the field (species or a nickname from my-run.md; comma-separate several)')
    s.add_argument('--last', help='the AI Pokémon that just went down (default: show each)')
    s.add_argument('--gone', help='AI Pokémon already down, comma-separated')
    s.add_argument('--foresight', action='store_true', help='your Pokémon is under Foresight/Odor Sleuth')
    s.add_argument('--pick', type=int, help='which trainer when the name matches several')
    s.set_defaults(f=cmd_next)
    a = p.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
