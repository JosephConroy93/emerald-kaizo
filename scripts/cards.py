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
    return {'key': key_ or 'Castform', 'species': species.title() if species.isupper() else species, 'gender': m.group('g') or '',
            'level': int(m.group('lv')), 'item': titled((m.group('item') or '').strip()), 'nature': nature, 'ivs': ivs,
            'types': [t1] if t1 == t2 else [t1, t2], 'levitate': bool(lev), 'matchups': weak, 'moves': moves}


# Power used to rank suggestions: EK values where the Move Changes doc gives one, vanilla
# Gen 3 otherwise. Fixed-damage moves get a rough equivalent; status moves are left out.
POWER = {
    'Thunderpunch': 75, 'Mach Punch': 40, 'Cross Chop': 100, 'Flamethrower': 95, 'Heat Wave': 100, 'Bite': 60,
    'Crunch': 80, 'Dig': 60, 'Rock Slide': 75, 'Dragonbreath': 60, 'Superpower': 120, 'Head Smash': 150,
    'Body Slam': 85, 'Giga Drain': 75, 'Sludge Bomb': 90, 'Water Pulse': 60, 'Ice Beam': 95, 'Psychic': 90,
    'X-Scissors': 80, 'Shadow Ball': 80, 'Brick Break': 75, 'Crush Claw': 100, 'Ember': 40, 'Headbutt': 70,
    'Dragon Claw': 80, 'Air Slash': 80, 'Earthquake': 100, 'Hydro Cannon': 150, 'Mud Shot': 55,
    'Muddy Water': 95, 'Octazooka': 65, 'Signal Beam': 75, 'Rock Smash': 20, 'Rock Throw': 50,
    'Secret Power': 70, 'Bone Rush': 100, 'Surf': 95, 'Thunderbolt': 95, 'Seismic Toss': 70, 'Drill Run': 80,
    'Wild Charge': 90, 'Bounce': 85, 'Earth Power': 90, 'Double-Edge': 120, 'Thief': 40, 'Night Shade': 60,
    'Drill Peck': 80, 'Shock Wave': 60, 'Ice Punch': 75, 'Water Gun': 40, 'Slash': 70, 'Rock Tomb': 50,
    'Thrash': 90, 'Horn Attack': 65, 'Double Kick': 60, 'Psybeam': 65, 'Psywave': 60, 'Waterfall': 80,
    'Hyper Voice': 120, 'Overheat': 120, 'Ice Shard': 40,
}
FIXED = {'Seismic Toss', 'Night Shade', 'Psywave'}
# Recharge and recoil cost a turn or HP, so they rank lower than their raw power.
DRAWBACK = {'Hydro Cannon': 0.6, 'Head Smash': 0.8, 'Overheat': 0.85, 'Double-Edge': 0.85,
            'Superpower': 0.9, 'Wild Charge': 0.9}


def score_all(d, opp, pool):
    """Score every pool Pokémon against one opposing Pokémon: hit it hard, take little back."""
    o1, o2, olev = d['mons'][opp['key']]
    threats = [m for m in opp['moves'] if m['cat'] != 'status']
    scored = []
    for c in pool:
        c1, c2, clev = d['mons'][c['species']]
        best, best_mv, best_x = 0, '', 0
        for mv in c['moves']:
            if mv not in POWER:
                continue
            t = norm_type(next((v[0] for k, v in d['moves'].items() if ek.key(k) == ek.key(mv)), 'NORMAL'))
            x = mult(d, t, o1, o2, olev)
            if mv in FIXED:
                x = 0 if x == 0 else 1
            stab = 1.5 if t in (c1, c2) and mv not in FIXED else 1
            v = POWER[mv] * DRAWBACK.get(mv, 1) * x * stab * (1.6 if x >= 2 else 1)
            if v > best:
                best, best_mv, best_x = v, mv, x
        worst, worst_mv = 0, ''
        for m in threats:
            x = mult(d, m['type'], c1, c2, clev)
            if x > worst:
                worst, worst_mv = x, m['name']
        if not threats:
            worst = 1
        score = best * (0.35 if worst >= 2 else 1.25 if worst == 0 else 1.1 if worst < 1 else 1)
        scored.append((score, best_x, worst, c, best_mv, worst_mv))
    scored.sort(key=lambda s: -s[0])
    return scored, bool(threats)


def why(entry, threats):
    score, bx, worst, c, mv, wmv = entry
    hit = f'{mv} {fmt(bx)}' if mv else 'no good attack'
    if not threats:
        take = 'it has no attacking moves'
    elif worst == 0:
        take = 'immune to all its attacks'
    elif worst < 1:
        take = 'resists all its attacks'
    elif worst == 1:
        take = 'nothing super effective on it'
    else:
        take = f'careful: {wmv} {fmt(worst)}'
    return f'{hit}; {take}'


def suggest(d, opp, pool):
    """Up to two picks for one opposing Pokémon."""
    scored, threats = score_all(d, opp, pool)
    return [{'who': e[3]['who'], 'where': e[3]['where'], 'why': why(e, threats)} for e in scored[:2]]


def best_team(d, party, pool, size=6):
    """Six from the pool: the best answer to each opposing Pokémon (nobody assigned more than two),
    then backups that rank high against the rest."""
    tables = [{e[3]['who']: e[0] for e in score_all(d, opp, pool)[0]} for opp in party]
    by_who = {c['who']: c for c in pool}
    team, covers = [], {}
    order = sorted(range(len(party)), key=lambda i: max(tables[i].values()))   # hardest first
    for i in order:
        ranked = sorted(tables[i], key=lambda w: -tables[i][w])
        pick = next((w for w in ranked if w in team and len(covers[w]) < 2), None) if len(team) >= size else None
        if pick is None:
            pick = next((w for w in ranked if len(covers.get(w, [])) < 2 and (w in team or len(team) < size)), ranked[0])
        if pick not in team:
            team.append(pick)
        covers.setdefault(pick, []).append(party[i]['species'])
    backups = {}
    if len(team) < size:
        top3 = [sorted(t, key=lambda w: -t[w])[:3] for t in tables]
        rest = sorted((w for w in by_who if w not in team),
                      key=lambda w: -sum(tables[i][w] for i in range(len(party)) if w in top3[i]))
        for w in rest[:size - len(team)]:
            team.append(w)
            backups[w] = [party[i]['species'] for i in range(len(party)) if w in top3[i]]
    out = []
    for w in team:
        c = by_who[w]
        out.append({'who': w, 'species': c['species'], 'where': c['where'],
                    'covers': covers.get(w, []), 'backup': backups.get(w, []),
                    'types': list(dict.fromkeys(d['mons'][c['species']][:2]))})
    return out


def fmt(x):
    return {0: '0×', 0.25: '¼×', 0.5: '½×'}.get(x, f'{x:g}×')


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
    pool = []
    pool_file = Path(__file__).parent.parent / 'references' / 'pool.json'
    if pool_file.exists():
        pool = [c for c in json.loads(pool_file.read_text(encoding='utf-8'))['pool'] if c['species'] in d['mons']]
    for loc, name, lines in hits:
        party = [p for p in (mon_info(d, l, changes, team) for l in lines) if p]
        for p in party:
            p['suggest'] = suggest(d, p, pool) if pool else []
        best = best_team(d, party, pool) if pool and party else []
        leads = [x['species'] for x in party[:2 if 'double battle' in name.lower() else 1]]
        for b in best:
            b['lead'] = [x for x in leads if x in b['covers']]
        best.sort(key=lambda b: min([leads.index(x) for x in b['lead']] or [9]))
        trainers.append({'name': re.sub(r'\s*\[.*?\]', '', name).strip(), 'place': loc,
                         'double': 'double battle' in name.lower(), 'party': party, 'best': best})
    return {'trainers': trainers, 'team': [w for w, _ in team]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('query')
    p.add_argument('--team', default='')
    p.add_argument('--title', default='')
    p.add_argument('--start', default='', help='drop trainers before the first one whose name contains this')
    p.add_argument('-o', '--out', required=True)
    a = p.parse_args()
    data = build(a.query, a.team)
    if a.start:
        idx = next((i for i, t in enumerate(data['trainers']) if ek.key(a.start) in ek.key(t['name'])), 0)
        data['trainers'] = data['trainers'][idx:]
    tpl = (Path(__file__).parent / 'cards_template.html').read_text(encoding='utf-8')
    title = a.title or data['trainers'][0]['name']
    page = tpl.replace('__TITLE__', html.escape(title)).replace('__DATA__', json.dumps(data, ensure_ascii=False))
    Path(a.out).write_text(page, encoding='utf-8')
    print(f'wrote {a.out}: ' + ', '.join(f"{t['name']} ({len(t['party'])})" for t in data['trainers']))


if __name__ == '__main__':
    main()
