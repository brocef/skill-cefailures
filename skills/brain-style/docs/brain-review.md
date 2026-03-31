# Brain Review — Design Architecture

When the user asks for a "brain-review" of a file, function, class, or other code unit, review the code against the guidelines below and report findings with specific, actionable suggestions.

## Guidelines

### 1. Break Down Large Classes and Functions

Look for opportunities to make large classes or functions smaller by extracting logic into other structures or functions.

- **Functions over ~40 lines:** Look for self-contained blocks that can be extracted into named helper functions.
- **Classes with many responsibilities:** Identify groups of related methods that could be extracted into a collaborator class or module.
- **Deeply nested logic:** Flatten by extracting inner blocks into well-named functions.

### 2. Break Down Large Files

If the file is over 1,000 lines, look for opportunities to split it.

- **General code files:** Identify cohesive groups of functions, classes, or constants that can move to their own module. Look for natural seams — groups that share imports, types, or a common concept.
- **Test files specifically:** Consider breaking the test suite along conceptual lines and reorganizing into multiple test files. Group by feature, component, or behavior rather than keeping one monolithic test file.

### 3. Eliminate Functional Redundancy

Look for functional redundancies and opportunities to use or create a reusable function.

- **Near-duplicate code blocks:** Two or more blocks that do essentially the same thing with minor variations — extract a shared function parameterized by the differences.
- **Repeated patterns across files:** If the same pattern appears in multiple places, suggest a shared utility.
- **Existing utilities not being used:** If the codebase already has a helper that covers the logic, flag the redundancy and suggest using the existing function.

## Output Format

Structure findings as a list grouped by guideline. For each finding:

1. **Location** — file, line range, class/function name.
2. **Issue** — what the problem is (e.g., "function is 120 lines with 3 distinct phases").
3. **Suggestion** — concrete extraction or reorganization proposal.

Skip any guideline section that has no findings. If the code is clean, say so briefly.
