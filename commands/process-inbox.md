---
description: Process a request document from docs/inbox/ — pick a candidate, read it and any bundled artifacts, produce the initial artifact the request implies, then archive the source to docs/inbox/.archive/.
---

# Process Inbox

The user maintains a `docs/inbox/` folder of request documents — pre-written prompts (optionally with accompanying artifacts) that they want an agent to pick up and process. This command walks one inbox entry end-to-end.

## 1. Verify the inbox exists

If `docs/inbox/` doesn't exist, ask: "There's no `docs/inbox/` folder yet — would you like me to create it (and `docs/inbox/.archive/` for processed requests)?"

If they agree, create both folders and stop — there's nothing to process yet. If they decline, stop without changes.

## 2. Enumerate candidates

In `docs/inbox/`, ignore `.archive/` and any hidden entries (anything starting with `.`). Each remaining entry is a candidate:

- **Loose text files** (`.md`, `.txt`) — each is a standalone request.
- **Folders** — each is a request bundle: the request doc lives inside; other files in the folder are supporting artifacts.

Loose **non-text** files at the inbox root are ambiguous — they aren't standalone requests and aren't bound to any particular request doc. Mention them to the user so they can move them into a bundle folder, but don't auto-attach them to any candidate.

If there are no candidates, tell the user the inbox is empty and stop.

## 3. Pick a candidate

- Exactly one candidate → use it without asking.
- Multiple candidates → list them and ask the user which to process.

## 4. Locate the request doc inside a bundle

For folder candidates, find the request doc inside the folder using this preference order:

1. A conventional name, in this order: `request.md`, `request.txt`, `proposal.md`, `proposal.txt`, `README.md`.
2. The only `.md`/`.txt` file in the folder (if there is exactly one).
3. Multiple text files and no conventional match → ask the user which file is the request doc.
4. No text files at all → tell the user the bundle has no request doc and stop; they can add one and re-run.

Non-text files in the bundle become supporting artifacts; reference them by path when processing.

## 5. Read and route

Read the request doc fully. If the filename uses a convention (`fix-*`, `feat-*`, `bug-*`, `refactor-*`, `chore-*`, etc.), note the implied type. Otherwise infer from the content.

Then route:

- **If `superpowers:*` skills appear in your available-skills list**, invoke the matching skill to drive the work: `brainstorming` for feature/design requests, `systematic-debugging` for bugs and failures, `writing-plans` when the doc is already a fleshed-out spec, and so on. Treat the request doc's contents as the task description and any sibling artifacts as supporting material.
- **If superpowers is not installed**, process the request directly: ask clarifying questions if the intent is unclear, and produce whatever artifact the request implies (a spec, a plan, code changes, etc.).

## 6. Archive the source

Once the request has been ingested — read and translated into whatever initial artifact you produce (a spec, a plan, in-context understanding) — move the source out of the inbox into `docs/inbox/.archive/`:

- Loose file → move just the file.
- Folder bundle → move the entire folder (with all its artifacts).

Create `docs/inbox/.archive/` if it doesn't exist. If a file or folder of the same name already exists in the archive, append a timestamp suffix (e.g., `feat-new-icons` → `feat-new-icons-20260519-143022`) rather than overwriting.

Archiving signals that the prompt has been picked up. The resulting artifacts live wherever your workflow normally puts them (spec docs, plan files, code changes) — not in the archive.

## 7. Continue

Continue with the work implied by the request. The archived source is no longer load-bearing — your spec, plan, or in-context understanding is the durable artifact going forward.
