# Change request: prefer Markdown representations for Claude Code webpage fetches

**Target surface:** Claude Code hooks, initially scoped to `WebFetch`.

## Problem

Agents often fetch documentation and article pages as HTML even when the same
resource is available as Markdown. That costs context, preserves navigation and
layout noise, and can make downstream summaries less reliable. Several modern
documentation platforms now expose agent-friendly Markdown through standard web
mechanisms, but agents do not automatically discover or prefer those forms.

The original idea was a tool-call hook that intercepts a requested URL and
changes it to an equivalent Markdown representation when one exists.

## Findings from research

The approach is viable, but it should be framed as a discovery heuristic rather
than a guaranteed web standard that all major sites implement.

Useful mechanisms:

- **HTTP content negotiation:** request the original URL with an `Accept` header
  that prefers Markdown, such as `text/markdown, text/html;q=0.9, */*;q=0.8`.
  If the response returns `Content-Type: text/markdown`, use that response while
  preserving the original URL as the canonical citation target.
- **HTTP `Link` header:** parse links advertising `rel="alternate"` and
  `type="text/markdown"`.
- **HTML head metadata:** parse `<link rel="alternate" type="text/markdown"
  href="...">` from the document head.
- **Offline fallback:** if no Markdown representation is advertised, use a
  real HTML-to-Markdown/readability extractor rather than regex cleanup.

Implementation caveats:

- Prefer `GET` with the Markdown `Accept` header over `HEAD`; many sites handle
  `HEAD` inconsistently or omit useful headers.
- Parse `Link` headers with a real parser. String splitting is fragile because
  headers can contain multiple links, quoted parameters, and commas.
- Resolve relative alternate URLs against the fetched URL.
- Do not blindly fetch arbitrary cross-origin alternates. Default to same-origin
  alternates, with an allowlist or explicit prompt for cross-origin rewrites.
- Cache discoveries per URL or origin so the hook does not double-fetch every
  page.

## Claude Code feasibility

Claude Code is the right first target. Its `PreToolUse` hooks receive the tool
name and `tool_input` as JSON and can return `hookSpecificOutput.updatedInput`
to replace the tool arguments before execution. For `WebFetch`, this means a
hook can inspect the requested URL, discover a Markdown representation, and
rewrite the tool input before the fetch runs.

The hook should replace the entire input object, preserving all unchanged fields
alongside the modified URL. When it rewrites the URL, it should also provide
`additionalContext` explaining the original URL and the Markdown URL so Claude
can cite the canonical source correctly.

## Codex parity note

Codex also has lifecycle hooks, including `PreToolUse` and `PostToolUse`, with
matching by tool name. Current Codex docs establish hook matching and execution,
including support for MCP tool names, but they do not show a documented
`updatedInput` equivalent for rewriting a built-in tool call before execution.

For that reason, Codex parity should be handled later, most likely by exposing
the shared Markdown discovery logic as an MCP `smart_fetch` tool and instructing
Codex to use it for webpage retrieval. Do not block the Claude Code hook on
Codex parity.

## Proposed implementation sketch

Build the implementation in two layers:

1. **Shared resolver module**
   - Input: original URL and optional fetch options.
   - Output: original URL, selected fetch URL, representation type, response
     content, and discovery reason.
   - Discovery order:
     1. `GET` original URL with Markdown-preferring `Accept` header.
     2. If response is Markdown, return it.
     3. Inspect HTTP `Link` headers for Markdown alternates.
     4. Inspect HTML head `<link rel="alternate" type="text/markdown">`.
     5. Fall back to HTML-to-Markdown/readability extraction.

2. **Claude Code `PreToolUse` hook**
   - Match `WebFetch`.
   - Read `tool_input.url`.
   - Run the resolver in metadata/discovery mode.
   - If a distinct Markdown URL is found, return:
     - `permissionDecision: "allow"` or `"ask"` depending on safety policy.
     - `updatedInput` with the original tool fields plus the rewritten URL.
     - `additionalContext` with the original canonical URL and rewrite reason.
   - If no Markdown representation is found, exit with no JSON decision so the
     normal `WebFetch` call proceeds unchanged.

## Open design questions

- Should same-origin Markdown rewrites be automatic while cross-origin rewrites
  require `"ask"`?
- Should the hook rewrite only explicit Markdown alternates, or also same-URL
  content negotiation responses? For same-URL negotiation, a wrapper fetch tool
  may be cleaner than `WebFetch` URL rewriting because the URL does not change.
- Where should the cache live: per project, global user cache, or process-local
  only?
- Which HTML-to-Markdown fallback should be used in Python for acceptable
  dependency weight and output quality?

## Test cases

1. A page returns `Content-Type: text/markdown` when sent `Accept:
   text/markdown` -> hook leaves canonical URL intact and fetches/returns
   Markdown.
2. A page advertises a same-origin Markdown alternate in the HTTP `Link` header
   -> hook rewrites `WebFetch` to that URL.
3. A page advertises a same-origin Markdown alternate in an HTML head `<link>`
   tag -> hook rewrites `WebFetch` to that URL.
4. A page advertises a cross-origin Markdown alternate -> hook blocks, prompts,
   or skips according to configured policy.
5. A page has no Markdown alternate -> hook exits silently and normal `WebFetch`
   behavior is unchanged.
6. A malformed or slow alternate lookup -> hook fails open and preserves the
   original fetch rather than blocking the agent.

## References

- Claude Code hooks: `https://code.claude.com/docs/en/hooks.md`
- Codex hooks: `https://developers.openai.com/codex/hooks.md`
- Vercel content negotiation: `https://vercel.com/blog/making-agent-friendly-pages-with-content-negotiation`
- Vercel AI-readable docs guide: `https://vercel.com/kb/guide/make-your-documentation-readable-by-ai-agents`
- Cloudflare Markdown for Agents: `https://blog.cloudflare.com/markdown-for-agents/`
- Web Linking standard: `https://www.rfc-editor.org/rfc/rfc8288`
