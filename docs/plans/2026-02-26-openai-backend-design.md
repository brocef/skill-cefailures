# OpenAI Backend Design

## Problem

The Claude CLI backend truncates output for large documentation inputs (no `--max-tokens` flag), causing JSON parse failures. The Anthropic SDK backend works but requires an Anthropic API key. Adding OpenAI SDK support provides an alternative backend that the user already has credentials for.

## Design

### Backend abstraction

Refactor `create_skill.py` to use a `Backend` ABC with three concrete implementations:

```
Backend (ABC)
├── generate(model, name, content) -> dict  [abstract]
└── _build_prompt(name, content) -> str     [shared, uses ANALYSIS_PROMPT]

CliBackend          → subprocess to claude CLI
AnthropicBackend    → anthropic SDK
OpenAIBackend       → openai SDK
```

All backends return through the shared `parse_skill_response()` function.

### Model defaults

```python
DEFAULT_MODELS = {
    "cli": "claude-sonnet-4-6",
    "sdk": "claude-sonnet-4-6",
    "openai": "gpt-5.2",
}
```

`--model` default is `None`, resolved at runtime from `DEFAULT_MODELS[backend]`.

### CLI changes

- `--backend` choices: `["cli", "sdk", "openai"]`
- New `--api-key` flag: optional, overrides `OPENAI_API_KEY` env var (openai backend only)

### OpenAI backend specifics

- Lazy `import openai` in `OpenAIBackend.generate()`
- API key: `--api-key` flag > `OPENAI_API_KEY` env var > error
- `max_tokens=16000`
- Uses `client.chat.completions.create()` with single user message
- Response from `response.choices[0].message.content`

### Dependencies

`requirements.txt` adds optional `openai>=1.0.0` comment.

### Testing

- `test_generate_skill_openai_success()` — mock openai client
- API key validation tests (env var and flag)
- Existing tests updated for Backend class refactor
