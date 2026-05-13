# Upcoming

- `AGENTS.md`: renamed the repo-level instruction file from `CLAUDE.md`; `CLAUDE.md` is now a symlink for Claude Code compatibility.
- `scripts/install_skill.py`: added `--agent {claude,codex,all}` so symlink installs can target `~/.claude/skills/`, `~/.codex/skills/`, or both.
- `tests/test_install_skill.py`: added coverage for Codex-only and all-agent installation targets.
- `README.md`: documented Codex-compatible local installation and the `AGENTS.md`/`CLAUDE.md` compatibility layout.
