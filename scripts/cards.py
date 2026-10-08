#!/usr/bin/env python3
"""Build a trainer card page (HTML) from the EK docs.

  python3 scripts/cards.py "Triathlete Randall" --team "Malbra Red=Magmar,Flygon,Donphan" -o out.html

Each opposing Pokémon gets its types, what hits it super effectively, and its four moves
coloured by type with what each move is super effective against. --team marks which of your
Pokémon a move hits super effectively. Trainer queries match the same way as `ek.py trainer`
(a name or a place; several hits make several cards).
"""
import argparse, html, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ek  # noqa: E402

TYPES = ['NORMAL', 'FIRE', 'WATER', 'ELECTRIC', 'GRASS', 'ICE', 'FIGHTING', 'POISON', 'GROUND',
         'FLYING', 'PSYCHIC', 'BUG', 'ROCK', 'GHOST', 'DRAGON', 'DARK', 'STEEL']
SPECIAL = {'FIRE', 'WATER', 'ELECTRIC', 'GRASS', 'ICE', 'PSYCHIC', 'DRAGON', 'DARK'}
LINE = re.compile(r'^(?P<mon>[A-Za-z][\w .\'-]*?)(?:\((?P<g>[mf])\))?:?\s+Lv\.?\s*(?P<lv>\d+)'
                  r'(?:\s*@\s*(?P<item>[^:]+?))?\s*[:;]\s*(?P<moves>[^\[+]*)(?:\[(?P<tag>[^\]]*)\])?')


def norm_type(t):
    t = t.upper()
    return 'FIGHTING' if t == 'FIGHT' else t


def mult(d, atk, t1, t2, lev):
    if lev and atk == 'GROUND':
        return 0
    return ek.chart_mult(d, atk, t1, t2) / 10


def move_info(d, name, changes):
    hp = re.match(r'^HP (\w+)$', name.strip())
    if hp:
        t, status, nm = norm_type(hp.group(1)), False, f'HP {hp.group(1).title()}'
    else:
        m = next((v for k, v in d['moves'].items() if ek.key(k) == ek.key(name)), None)
        t, status, nm = (norm_type(m[0]), m[1], name.strip()) if m else ('NORMAL', False, name.strip())
    se = [x for x in TYPES if ek.chart_mult(d, t, x, x) > 10] if not status else []
    cat = 'status' if status else ('special' if t in SPECIAL else 'physical')
    note = '' if hp else short_note(changes.get(ek.key(name), []))
    return {'name': nm, 'type': t, 'cat': cat, 'se': se, 'danger': name.strip().isupper() and len(name.strip()) > 3,
            'note': note}


def short_note(lines):
    """Keep only what EK changed about this move: a shared 'X, Y and Z all have 16 PP' line
    shrinks to '16 PP'."""
    if not lines:
        return ''
    l = lines[0]
    m = re.search(r'\b(?:all have|are all|all are|have|has)\s+(.+)$', l)
    if l.count(',') >= 2 and m:
        return m.group(1).strip().rstrip('.')
    return l


def mon_info(d, line, changes, team):
    m = LINE.match(line)
    if not m:
        return None
    species = m.group('mon').strip()
    key_ = next((k for k in d['mons'] if ek.key(k) == ek.key(species)), None)
    t1, t2, lev = d['mons'][key_] if key_ else ('NORMAL', 'NORMAL', False)
    weak = {}
    for atk in TYPES:
        x = mult(d, atk, t1, t2, lev)
        if x != 1:
            weak.setdefault(str(x), []).append(atk)
    tag = (m.group('tag') or '').split('|')
    nature = tag[-1].strip() if tag and tag[-1].strip() and not tag[-1].strip().isdigit() else ''
    ivs = next((x for x in tag if x.strip().isdigit()), '')
    moves = []
    for mv in [x for x in m.group('moves').split(',') if x.strip() and '---' not in x]:
        info = move_info(d, mv, changes)
        info['hits'] = []
        for who, sp in team:
            s1, s2, sl = d['mons'][sp]
            x = 0 if info['cat'] == 'status' else mult(d, info['type'], s1, s2, sl)
            if x > 1:
                info['hits'].append({'who': who, 'x': x})
        moves.append(info)
    return {'species': species.title() if species.isupper() else species, 'gender': m.group('g') or '',
            'level': int(m.group('lv')), 'item': titled((m.group('item') or '').strip()), 'nature': nature, 'ivs': ivs,
            'types': [t1] if t1 == t2 else [t1, t2], 'levitate': bool(lev), 'matchups': weak, 'moves': moves}


def titled(s):
    return s.title() if s.isupper() else s


def resolve_team(d, spec):
    out = []
    for part in [p.strip() for p in spec.split(',') if p.strip()]:
        who, _, sp = part.partition('=')
        sp = sp or who
        key_ = next((k for k in d['mons'] if ek.key(k) == ek.key(sp)), None)
        if not key_:
            sys.exit(f'Unknown species in --team: {sp}')
        out.append((who.strip(), key_))
    return out


def build(query, team_spec):
    d = ek.switch_data()
    _, changes = ek.load_move_changes(ek.load_learnsets())
    team = resolve_team(d, team_spec) if team_spec else []
    q = ek.key(query)
    blocks = list(ek.trainer_blocks(ek.mastersheet_sections()))
    hits = [b for b in blocks if q in ek.key(b[1])] or [b for b in blocks if q in ek.key(b[0])]
    if not hits:
        sys.exit(f'No trainer or place matches "{query}".')
    trainers = []
    for loc, name, lines in hits:
        party = [p for p in (mon_info(d, l, changes, team) for l in lines) if p]
        trainers.append({'name': re.sub(r'\s*\[.*?\]', '', name).strip(), 'place': loc,
                         'double': 'double battle' in name.lower(), 'party': party})
    return {'trainers': trainers, 'team': [w for w, _ in team]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('query')
    p.add_argument('--team', default='')
    p.add_argument('--title', default='')
    p.add_argument('-o', '--out', required=True)
    a = p.parse_args()
    data = build(a.query, a.team)
    tpl = (Path(__file__).parent / 'cards_template.html').read_text(encoding='utf-8')
    title = a.title or data['trainers'][0]['name']
    page = tpl.replace('__TITLE__', html.escape(title)).replace('__DATA__', json.dumps(data, ensure_ascii=False))
    Path(a.out).write_text(page, encoding='utf-8')
    print(f'wrote {a.out}: ' + ', '.join(f"{t['name']} ({len(t['party'])})" for t in data['trainers']))


if __name__ == '__main__':
    main()
