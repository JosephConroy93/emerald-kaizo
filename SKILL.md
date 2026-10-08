---
name: emerald-kaizo
description: Pokémon Emerald Kaizo (EK) run companion backed by the community EK docs (learnsets, move changes, Mastersheet walkthrough, rival teams, detailed encounters) and the user's run log. Use it whenever the user asks about Kaizo, EK or Emerald Kaizo, or mid-run asks what a Pokémon learns or will know at a level, what a move does in EK, an ability, stat or evolution change, a Pokémon's type or weaknesses, where to catch something, what a gym leader, trainer or rival uses, which Pokémon the AI sends in next, or how to beat a fight. Also use it when they're stuck, such as where to go next, what to do between badges, or where an HM, bike or key item is. Treat a Gen 3 Pokémon, move or Hoenn trainer question with no other game named as an EK question. If both emerald-kaizo and anthropic-skills:emerald-kaizo are listed, use emerald-kaizo, the live copy.
---

# Emerald Kaizo companion

The user is usually mid-run on a phone or iPad and wants the answer in a glance. EK changes
learnsets, moves, abilities, evolutions and every trainer team, so answers from memory of vanilla
Emerald are wrong in ways that end runs. Everything here comes from the bundled docs; say so
when the docs don't cover something instead of filling the gap from memory.

**Read `references/my-run.md` first.** It holds the user's rules (no bag items in battle, level
cap, how they use Rare Candies), their starter and gender, their team with nicknames, and the
cheat codes they use. Plan within those rules, call their Pokémon by nickname, and never suggest
bag items in battle or levelling past the cap.

## Look it up with the script

Run `scripts/ek.py` with Python 3 from this skill's folder (use the absolute path of the
directory this file is in). The commands below say `python3`; on Windows use `python` or `py -3`
if `python3` isn't found. Names are fuzzy-matched, so pass the user's spelling as-is; when
the script prints `(read "x" as Y)`, mention the correction only if it might be wrong.

| Question | Command |
|---|---|
| What does X learn / its type and weaknesses / any EK changes to it | `python3 scripts/ek.py mon X` |
| What will X have or learn at level N; what will a wild X know | `python3 scripts/ek.py mon X --level N` |
| What does move M do in EK; who learns M | `python3 scripts/ek.py move M` |
| Where do I catch X | `python3 scripts/ek.py where X` |
| What's wild at a place and what moves it has; can anything here flee or explode | `python3 scripts/ek.py wild "Granite Cave"` |
| A trainer's or gym leader's team; all trainers at a place | `python3 scripts/ek.py trainer "Roxanne"` / `trainer "Route 110"` |
| Who will the AI send in next | `python3 scripts/ek.py next Brawly --me Federer [--last Hitmontop] [--gone Meditite,Poliwrath]` |
| Rival (May/Brendan) team | `python3 scripts/ek.py rival --starter mudkip --gender boy [--place "route 119"]` |
| Who the rival sends in next | `python3 scripts/ek.py next --rival --starter mudkip --gender boy --place "route 110" --me Bron` |
| Everything at one location (encounters, notes, trainers) | `python3 scripts/ek.py area "Mt. Pyre"` |
| Stuck: what's next after badge N | `python3 scripts/ek.py guide "badge 3"` |
| Where's an HM, bike or key item; what to do at a place | `python3 scripts/ek.py guide "Mach Bike"` / `guide Fortree` |
| Anything else (items, TMs, tutors, puzzles, gifts) | `python3 scripts/ek.py search "text"` |
| Scouting cards page for a trainer, gym or place (types, weaknesses, type-coloured moves, your team's risks) | `python3 scripts/cards.py "Petalburg Gym" --team "Nick=Species,..." -o page.html`, then publish it as an Artifact |

If the script says a name is ambiguous (Nidoran, a short prefix), ask which one. If code can't
run, read the files in `references/` directly; each has the layout described below.

## Reading the results

**Learnsets** (`mon`) are level-up moves only. The docs have no TM, HM, tutor or egg-move
compatibility, and EK strips many setup moves (Swords Dance, Dragon Dance, Calm Mind and others)
from level-up altogether. If asked whether something can learn a TM, say the docs don't cover it.
Tutor and TM locations are in the Mastersheet (`search "Move Tutor"`, `search "TM"`).

The notes under a learnset are EK's changes to that Pokémon; a missing line means vanilla:
- `Ability: X` or `Ability 1/2: X`: its abilities in EK.
- `Base +10 SpA`: a base-stat buff.
- `Evolves at 27`, `Level 37 -> Politoed`, `Water Stone -> Slowking`: changed evolution.
- `@Lum Berry 5%`: the item a wild one may hold.
- `(Delay until 37)`: the doc author's advice to hold off evolving until that level.

**Wild movesets** (`--level`): a wild Pokémon in Gen 3 knows the last four distinct
level-up moves it learned at or below its level. The script works this out; quote it when the
user asks what something they're about to fight or catch will have. Trainer Pokémon don't follow
this rule; they use the moves listed for their trainer.

**Moves** (`move`): the Move Changes doc (by gn0mis) lists everything EK changed; a move not in it
keeps its vanilla Gen 3 stats, which you may state from memory, labelled as vanilla. Several old
moves were renamed into new ones (Horn Drill → Drill Run, Fissure → Earth Power, Skull Bash → Head
Smash), and the learnsets use the new names. These are later-generation moves that don't exist in
vanilla Emerald, so never call their behaviour "vanilla". Where the doc gives no stats (Icicle
Spear → Ice Shard, Astonish → Shadow Sneak), say they are presumably modelled on the later-gen
move of that name, and that this is an assumption. Two names are ambiguous: Comet Punch and Vice Grip
both became a "Weather Ball" (Water and Fire, 100 BP), and twelve moves became fixed-type "Hidden
Power"s. When a learnset says Weather Ball or Hidden Power, the docs don't say which variant;
show the candidates rather than guessing.

**Trainers** (`trainer`, `rival`, `area`): each Pokémon line reads
`Species(gender) Lv.N @Held item: move, move, move, move [n|Nature] +EXP`. The script appends the
EK changes to the moves on those teams; use them (Sky Attack, for one, is a 120 BP recoil move in
EK).
- Teams are in party order. The first one leads (the first two in a double battle), but
  replacements after a faint don't follow party order; use `next` for those.
- `HP Grass`, `HP Ice` and so on mean Hidden Power of that type.
- A move in CAPITALS (SELFDESTRUCT, EXPLOSION, MIRROR COAT, METRONOME) is the doc flagging a
  run-ending threat. Always call these out.
- `-----` is an empty move slot.
- A number before the nature (`[0|Mild]`, `[15]`) is most likely that Pokémon's IVs; the doc
  has no legend, so say "probably" if asked.
- `+276` is the EXP you get for knocking it out.
- `[Double Battle]` and `[Double Battle with …]` mark double battles. The "Superboss" with
  `[Double Battle with You]` is your partner, not an opponent.

The rival doc labels each team by **the player's** gender and starter ("Male, Treecko" means
the player is male and chose Treecko, so May has the Torchic line). The user's starter and gender
are in `my-run.md`. **For rival battles always use `rival` and `next --rival`.** The Mastersheet
and the switch calculator each carry one sample rival team that may not be the user's; the script
warns when one comes up.

**Types** (`mon`): the `Type:` line and the weak/resist/immune lines come from the EK AI Switch
Calculator's tables, so they include EK's type changes. The sheet lists some Pokémon as Fairy
(Clefairy, Marill, Ralts, Mawile) but gives Fairy no matchups, so it counts as neutral to and
from everything.

**Next switch-in** (`next`): the Gen 3 AI picks a replacement by rules, not party order:
1. It looks for the Pokémon **your** Pokémon's type hits hardest, and sends it in only if it has
   a super-effective move against you. Otherwise it tries the next-hardest-hit, and so on.
2. If none qualifies, it sends the one with the best-typed move against you, counting STAB from
   the Pokémon that just fainted. Status moves count here, so Hypnosis counts as a Psychic move.
3. If nothing scores, it sends the next one in party order.

So the answer depends on which of your Pokémon is on the field when theirs faints. Without
`--last`, the script shows every case. Use it to plan the switch that baits the replacement you
want. `--me` takes species or a nickname listed in `my-run.md`. It covers replacements after a
faint, not the AI switching out mid-turn.

**Gen 3 rules that change battle plans** (vanilla mechanics, which EK keeps):
- Physical or special depends on the move's **type**. Normal, Fighting, Flying, Poison, Ground,
  Rock, Bug, Ghost and Steel moves use Attack; Fire, Water, Grass, Electric, Ice, Psychic, Dragon
  and Dark use Special Attack. So Huge Power boosts only the first group, and Charm or a burn
  doesn't weaken Surf or Ice Punch.
- A Pokémon with no `Ability` note keeps its vanilla abilities. Name the ones that change the plan,
  labelled as vanilla: Shadow Tag and Arena Trap (you can't switch out), Color Change (the target
  turns into the type of the move that hit it), Volt Absorb and Water Absorb (those moves heal it),
  Levitate, Intimidate, Pure Power and Huge Power (double Attack), Guts (a burn makes it stronger),
  Thick Fat, Insomnia and Vital Spirit (can't sleep).
- Fire types can't be burned, so they're the safe answer to Will-o-Wisp.
- Back-to-back trainer battles don't heal you, and the next battle starts with your first party
  Pokémon that hasn't fainted. Set the party order before the first battle.
- In Shift mode, when the foe's Pokémon faints the game offers a free switch before its
  replacement acts. Use it to answer what `next` predicts.
- The docs have no base stats. Damage estimates come from memory of vanilla stats; call them
  "rough maths".

**Encounters** (`where`, `wild`): each ⚠ flag marks a way to lose the encounter before you catch
it.
- Teleport or Roar/Whirlwind: it ends the battle.
- Selfdestruct/Explosion/Memento: it faints itself, and Explosion can take your lead with it.
- Recoil move: it can KO itself.

A flag shows if the Detailed Encounters sheet's colour coding marks it, or if the wild moveset at
the listed level contains such a move; the two agree on 98% of encounters. Lead with any flag
when the user is about to hunt something. Bracketed hints like `(Bring Mach Bike)` say what you
need to reach the area. `(Mastersheet says Lv 15-16)` means the two docs disagree on level, so
give both.

**Progression guide** (`guide`): `references/progression.md` is distilled from the 2005 Prima
guide for vanilla Emerald, keeping only the story steps, where to go next, HM, bike and key-item
sources, and puzzle notes. EK keeps Emerald's story and map but changes Pokémon, moves, encounters
and teams, so those were left out. Never take them from the Prima guide or from memory; use the
EK commands. Each place the guide prints is followed by its EK Mastersheet notes, and those win
where they differ (EK's Granite Cave has ice-floor puzzles; its Regi door steps differ from vanilla).
A note headed `(later visit, after X)` belongs to a return trip that comes after X in the run,
not to your first visit.
Lines tagged [Emerald knowledge] fill gaps where the scan was unreadable; say so if it matters.
- Pass `guide` a place, an item or "badge N", never a whole sentence.
- If you don't know how far along the user is, ask for their badge count or where they are.
- For "where do I go now", give the next one to three concrete steps, not the whole chapter.

## How to answer

- Lead with the direct answer in one or two lines ("Spoink learns Psychic at Lv 34."), then a
  short list if it helps. Narrow screen: no wide tables, no full learnset dump unless asked.
- Mention any EK change that touches the answer (a move's new PP or power, a changed ability or
  evolution level) and any danger flag or CAPS move. That's the whole point of the docs.
- For "what's next" questions, give the next two to four moves with levels.
- Say "the EK docs don't cover that" plainly rather than guessing. If you add vanilla knowledge,
  label it as vanilla.
- For a route, a gym or a back-to-back fight, take the trainers in walkthrough order and each
  team in **party order, lead first**. For each opposing Pokémon give one line: which of the
  user's Pokémon it threatens (by nickname, with the move) and who should face it. Then add the
  `next` lines that matter ("KO with Bron → Nidorino comes in; switch to Federer").
- **Scouting cards are the default for trainer and gym info** (the user's preferred format): run
  `scripts/cards.py` for the trainer, gym or place with `--team` set to the user's current six
  (`Nickname=Species`), publish the HTML as an Artifact (one per gym or area; republish the same file to
  keep its link), and reply with the link plus one or two lines on the big threats. The user plans
  from the cards, so only add a Battle summary or Step-by-step battle plan when asked.
- Fight plans come in two named formats; the user may ask for either or both by name:
  - **Battle summary**: the ✅/❌ lines below, one per opposing Pokémon in party order.
  - **Step-by-step battle plan**: numbered turns: lead and party order, who attacks what, and
    at each KO who comes in next (`next`) and who to switch to.
  For a gym leader, the rival or another big fight, give both unless asked for one.
  - **Berries**: whenever you give battle data, end with one line per team member: the berry
    to hold, its PokéMart code from `my-run.md`, and why (Lum for status-prone ones facing Thunder
    Wave, sleep or confusion; Sitrus otherwise; never Lum on a type immune to the status).
- One line per opposing Pokémon: the ✅ part (who to send, and the move to use), then the ❌ part
  (who to keep out, with the move that threatens them in brackets). Nothing else on the line:
  no extra notes between ✅ and ❌, where the user once misread who to send and lost a Pokémon.
  - Shuppet 26: ✅ Dave (Bite). ❌ Bouncyboi (Shadow Ball).
  Check every one of the opponent's moves against every team member's types before writing
  KEEP OUT; a Water move is super effective on any Ground type, Nidoking included.
- No damage maths unless the user asks for it, or the fight is a gym leader, the rival or
  another significant battle. Otherwise just name the moves that are super effective against
  their Pokémon, who should face each one, and which of the user's Pokémon to keep away.
- When the user says they're going to catch something, check the wild moveset for danger flags and
  remind them to bring the chipper and sleeper listed in `my-run.md`, with the ball odds that matter.
- The user is usually mid-fight, so speed matters. Answer first, then update `my-run.md` and
  push. Batch lookups into as few script runs as you can.

## Examples

**"what does mr mime learn next, he's lv 30"**: run `mon "mr mime" --level 30`. Answer: next is
Role Play (Lv 33), then Signal Beam (Lv 34, 24 PP in EK), Psychic (Lv 36, 16 PP), Teeter Dance
(Lv 45). Its ability in EK is Own Tempo.

**"what's roxanne got"**: run `trainer roxanne`. Give her six Pokémon in order, with levels,
items and moves. Lead with the threat: her Nosepass has SELFDESTRUCT.

**"where can i get an abra"**: run `where abra`. Every listed encounter knows Teleport, so it
flees on turn one unless you can stop it. Say that first, then list the places.

**"anything in granite cave that can explode on me"**: run `wild "granite cave"` once; don't look
up each species separately. Answer: nothing there knows Selfdestruct or Explosion at those levels.
Ralts and Abra know Teleport.

**"brawly, i've got marshtomp out, who comes after hitmontop"**: run
`next brawly --me marshtomp --last hitmontop`. Answer: Hitmonlee comes next. None of his team has
a super-effective move on Marshtomp, so the AI goes by Rolling Kick (Fighting STAB).

**"rival on route 110, who do I lead with"**: run `rival --starter mudkip --gender boy --place
"route 110"`, then `next --rival ... --me` with the whole team. Answer in party order: Plusle
first, so lead Bron (Ground: immune to its Electric moves, Magnitude does 2x). Close with what
each KO brings in: a KO by Federer brings Grovyle, whose Giga Drain does 4x to him.

**"just beat wattson, where now?"**: run `guide "badge 3"`. Answer: go north on Route 111
(Rock Smash the boulders), through the Fiery Path to Route 113 and Fallarbor, where Team Magma
has taken Prof. Cozmo to Meteor Falls. Optional first: the Mauville bike, and Rusturf Tunnel
from Verdanturf.

## Sources

`references/` holds the EK Docs folder: `learnsets.txt` (EK Learnsets), `move-changes.txt`
(Move Changes by gn0mis), `mastersheet.txt` (EK Mastersheet: route-by-route encounters, items,
notes and every trainer), `rival-teams.txt`, and `encounters.csv`, converted from Detailed
Encounters.xlsx with its colour codes turned into the `danger_flag` column, and `progression.md`
(story and items from the 2005 Prima vanilla Emerald guide), and `ai-switch.json` (the EK AI Switch
Calculator's Pokémon types, move types, type chart and trainer teams; its switch logic is
reimplemented in `ek.py`). `my-run.md` is the user's own run log, not EK data.

## Keeping this skill current

In Claude Code this folder is a git checkout of the private repo `josephconroy93/emerald-kaizo`.
When the user reports a change to their run (a catch, an evolution, levels, a badge, a rule),
update `references/my-run.md`. When you fix `ek.py` or these instructions, first run a few
commands that touch what you changed (`mon`, `trainer`, `rival`, `next`) and check the output.
Then commit and push from this folder, so the user's PC picks it up at the next session start.
On claude.ai the skill files are read-only: say what should change, and it goes in the next
upload of the `.skill` file.
