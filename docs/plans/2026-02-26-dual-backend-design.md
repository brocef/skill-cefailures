# Dual Backend for create_skill.py — Design Document

## Purpose

Add support for two LLM backends in `create_skill.py`: the `claude` CLI (default) and the Anthropic SDK. This removes the hard requirement for `ANTHROPIC_API_KEY` since most users have Claude Code installed.

## CLI Flag

```
--backend {cli,sdk}    LLM backend (default: cli)
```

- `cli` — calls `claude -p` via `subprocess.run()`, no SDK needed
- `sdk` — uses `anthropic.Anthropic()`, requires `ANTHROPIC_API_KEY`

## Import Changes

Remove `import anthropic` from top-level. Lazy-import inside `generate_skill_sdk()` only. `httpx` stays top-level (always needed for fetching).

`requirements.txt` updated with comment noting `anthropic` is optional.

## Functions

### parse_skill_response(response_text: str) -> dict

Shared helper extracted from current `generate_skill()`:
- Strip markdown code fences
- `json.loads` with error handling
- Validate required keys (`library_description`, `trigger_description`, `when_to_use`, `key_patterns`, `topics`)
- Return parsed dict

### generate_skill_cli(model: str, name: str, content: str) -> dict

- Format `ANALYSIS_PROMPT` with name and content
- Call `subprocess.run(["claude", "-p", prompt, "--model", model, "--output-format", "json"], ...)`
- Parse outer JSON from claude output, extract `.result` field
- Pass result text to `parse_skill_response()`
- Error handling: `FileNotFoundError` → tell user to install Claude Code or use `--backend sdk`; non-zero exit → print stderr

### generate_skill_sdk(model: str, name: str, content: str) -> dict

- Lazy `import anthropic`
- Check `ANTHROPIC_API_KEY` env var
- Call `client.messages.create()` (current logic)
- Extract `response.content[0].text`
- Pass to `parse_skill_response()`

### main() dispatch

```python
if args.backend == "cli":
    skill_content = generate_skill_cli(args.model, args.name, content)
else:
    skill_content = generate_skill_sdk(args.model, args.name, content)
```

## Error Handling

| Scenario | Message |
|----------|---------|
| `claude` not found (CLI) | "Error: claude CLI not found. Install Claude Code or use --backend sdk." |
| Non-zero exit (CLI) | Print stderr from claude process |
| Missing API key (SDK) | "Error: ANTHROPIC_API_KEY environment variable is not set." |
| Malformed JSON (both) | Show first 500 chars of raw response |
| Missing keys (both) | List missing required keys |
