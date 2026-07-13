# Optional product-layer coordination

Use this protocol only when the host workspace declares both repo-local capability files and a shared product-layer catalog. A single repository needs no product layer.

## Model

- **Repo-local layer:** capability files describe behavior implemented or intended in one repository.
- **Product layer:** workspace-owned files describe platform-independent intent across repositories.
- **Coordinator:** the workspace role authorized to read and update the product layer and relay wording to repo-local agents.

The host workspace defines paths, ownership, and transport. This skill does not prescribe an orchestrator repository, broker, agent tool, or directory name.

## When to coordinate

Ask the coordinator for product-layer wording when a capability:

- exists or could exist in multiple repositories or platforms;
- has shared product wording already maintained by the workspace; or
- is being marked `Missing` or `Omitted` and that decision may express product-wide intent.

A useful request names the repo-local file and capability, then asks for the canonical wording and status. The coordinator should return only the relevant paragraph, status, and known platform differences—not unrelated sibling-repository paths.

## When coordination is unavailable

1. Author from in-repository evidence and host instructions.
2. Add this as the first body paragraph when wording remains uncertain:

   ```markdown
   _TODO: confirm wording with the workspace product layer._
   ```

3. Report the uncertainty in the completion summary.
4. Let the workspace coordinator reconcile the entry later.

Do not block indefinitely and do not attempt an unauthorized cross-repository read.

## Boundaries

- Repo-local capability files do not directly reference sibling repositories.
- The coordinator owns shared product-layer content; repo-local agents own local evidence.
- Product-layer coordination aligns intent but does not replace human review.
- If the host workspace declares no product layer, omit this protocol entirely.
