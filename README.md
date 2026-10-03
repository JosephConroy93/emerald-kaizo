# emerald-kaizo

A personal Claude Code skill for a Pokémon Emerald Kaizo run: EK learnsets, move changes,
trainers and rival teams, encounters, a progression guide and the Gen 3 AI switch-in predictor.
`SKILL.md` tells Claude how to use it; `references/my-run.md` is the current run log.

## Install on a PC (once)

Clone it straight into your personal skills folder:

    git clone https://github.com/josephconroy93/emerald-kaizo.git ~/.claude/skills/emerald-kaizo

On Windows that folder is `%USERPROFILE%\.claude\skills\emerald-kaizo`.

## Pull updates automatically

Add this to `~/.claude/settings.json` so every Claude Code session starts with the latest version:

    {
      "hooks": {
        "SessionStart": [
          { "hooks": [ { "type": "command", "command": "git -C ~/.claude/skills/emerald-kaizo pull --ff-only -q" } ] }
        ]
      }
    }

Or update by hand with `git -C ~/.claude/skills/emerald-kaizo pull`.

## Phone and iPad

claude.ai uses its own copy. Zip this folder (as `emerald-kaizo/...`) into `emerald-kaizo.skill`
and upload it under Settings → Capabilities → Skills, replacing the old one.
