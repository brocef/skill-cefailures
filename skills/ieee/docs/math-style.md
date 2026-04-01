# IEEE Mathematics Style

Rules for formatting equations, mathematical notation, and symbols in IEEE publications.

## Equations as Grammar

Equations are sentences with grammatical structure. They contain nouns (variables), verbs (relational symbols like =, >=, <=, ~=), adjectives, prepositional phrases, conjunctions, and conditions.

When math occurs along with text, it shares the grammatical characteristics of that text. A displayed expression may be a main or subordinate clause, an expression in apposition, a direct object, an item in a list, or the object of a preposition.

**Core principle:** The only punctuation permitted at the end of an equation is a period. Interior punctuation (commas, semicolons) carries mathematical meaning and must not be altered.

**Introductory sentences:** Use a comma after introductory words like "i.e.," "e.g.," "Hence," or "That is." Use a colon after words like "following" or "as follows." No punctuation after forms of the verb "to be," or between a verb and its object.

**Ellipses:** Use exactly three dots, enclosed by commas, placed on the baseline:

    I = 1, 2, 3, ... , n

**Conditions:** When an equation includes conditions, place a comma at the end of the equation, then a 2em space, then the condition. Multiple conditions are separated with semicolons, aligned on the operator:

    v(t) = u(t),        t = 1, 2, ..., m.

## Inline Equation Rules

An inline equation appears within running text (not displayed). Five rules govern inline formatting.

**Rule 1 -- Break after verb or operator.** If an inline equation must break across lines, break after a verb (=, >=) or operator (+, -), keeping the verb or operator on the top line.

**Rule 2 -- No stacked fractions.** Fractions must not appear stacked (built-up) in running text. Use the solidus instead. Write `(a + b)/c` not a stacked fraction.

**Rule 3 -- Collective sign limits to the side.** Summation, product, and similar collective signs must have limits placed to the side (subscript/superscript position), not above and below.

**Rule 4 -- Use exp for long superscripts.** When the exponent of *e* is lengthy, use the roman function `exp` with brackets. Write `exp[(zx^2 + y)(alpha - 2yx) + zx]` instead of *e* with a long superscript.

**Rule 5 -- Avoid long radical signs (optional).** Rewrite long square roots using fractional exponents. Write `(x + alpha)^{1/2}` instead of a square root with a long bar.

## Displayed Equation Break/Alignment

Six rules govern how displayed equations are broken and aligned.

**Rule 1 -- Break at verbs, align on verbs.** When a displayed equation has multiple verbs, break at each verb and align them vertically:

    A = (5alpha + x) + (10y + beta)^2
     >= (5x - alpha + y + x^2)
      = B^2

**Rule 2 -- One verb: break at operators, align right of verb.** When an equation has only one verb, break at operators and align subsequent lines to the right of the verb:

    A = (5alpha + x)
        + (10y + beta)^2
        - (5x - alpha + y + x^2)

**Rule 3 -- Separate equations with em quad or stack.** Multiple separate equations either fit on one line separated by an em quad, or are stacked and aligned on their verbs.

**Rule 4 -- Two-line equations: flush left / flush right.** An equation that fits on two lines without further breaks should be broken at the verb and aligned flush left (first line) and flush right (second line) over the column width.

**Rule 5 -- Within fences: break at operator, align inside left fence.** When breaking an equation inside parentheses, brackets, or braces, break at an operator and align to the right of the left-hand fence.

**Rule 6 -- Period placement.** A period is placed at the end of a fraction, case equation, or after closed delimiters (outside the closing fence).

**Fence matching:** Pairs of fences must match in size and be proportional to the math they enclose.

**Special cases:**

- *Right-to-left equations:* When the verb appears in the right half, break before an operator and align to the left of the verb.
- *Solidus as operator:* Break after a solidus and align the next line to the right of the verb.
- *Implied product:* When one set of fences is followed directly by another, the equation may be broken between them if a multiplication sign (x or centered dot) is inserted. Align to the right of the verb.
- *Integrals and differentials:* Preferably break after the differential expression. If a break is needed before the differential, break at an operator and align to the right of the integral sign.

## Equation Numbering

**Consecutive numbering:** Equations are numbered consecutively from the beginning to the end of the article, parenthesized and set flush right: (1), (2), (3), etc.

**Appendix equations:** Continued consecutive numbering is preferred. If the author restarts numbering, (A1), (A2), etc. is permissible.

**Sub-numbers:** Use (1a), (1b) -- not (1-a) or (1.a). Apply consistently throughout the article.

**Section-based numbering:** Some Transactions permit numbering by section, e.g., (1.1), (1.2.1), (A1). This is an author's own system and acceptable where permitted.

## Italic vs Roman vs Bold

### Variables -- Always Italic

All mathematical variables are set in italic: *x*, *y*, *z*, *A*, *B*, *f(x)*.

### Vectors -- Boldface Italic

Vectors are set in boldface italic when distinguished by the author.

### Roman (Upright) -- Functions, Units, Abbreviations

The following function names must always be set in roman (upright) type:

| Function | Meaning | Function | Meaning |
|----------|---------|----------|---------|
| ad | adjoint | lim | limit |
| arg | argument | liminf | limit inferior |
| cos | cosine | limsup | limit superior |
| cosh | hyperbolic cosine | ln | natural logarithm |
| cot | cotangent | log | logarithm |
| coth | hyperbolic cotangent | lub | least upper bound |
| csc | cosecant | max | maximum |
| csch | hyperbolic cosecant | min | minimum |
| curl | curl | mod | modulus |
| det | determinant | Pr | probability |
| diag | diagonal | Re | real part |
| dim | dimension | sec | secant |
| div | divergence | sin | sine |
| exp | exponential | sinh | hyperbolic sine |
| hom | homology | tan | tangent |
| Im | imaginary part | tanh | hyperbolic tangent |
| inf | infimum | tr | trace |
| ker | kernel | Tr | transpose |
| | | wr | wreath |

Additional roman functions from Section L: int, cov, var, sgn, sinc, grad, sup, erf, erfc, Si, Ci, Cin, Shi, Chi, Ei, li, Ai, gaf, gafc, sn, cn, dn, an (Jacobian elliptic functions), ver, covers, havers, exsec.

**Preferred abbreviations:**
- Use "cot" not "ctg" or "ctn"
- Use "csc" not "cosec"
- Use "tan" not "tg"
- Use "Pr" not "Prob." and not italic *P_r*
- Use "Re" for real part (roman, not italic)

### Semiconductor Terms -- Roman

Semiconductor designations are set in roman: p-n, p-i-n, p+-n-p++. Always include the hyphen.

### Logic Keywords -- Small Caps

Logic and programming keywords are set in small caps: AND, OR, NOR, NAND, XOR, EXCLUSIVE OR, ADD, DO, GO TO, READ, WRITE, PRINT, CONTINUE, FORMAT, END, ON, OFF, DIMENSION, DIFFER, EXTRACT, PAUSE.

### Circuit Abbreviations -- Italic

Circuit-type abbreviations are set in italic: *RC*, *RL*, *LC*, *I-V*, *S/N*, *f/22*.

### Other Roman Items

The following are also set in roman (upright) type:
- Abbreviations: e.g., i.e., viz., cf., et al.
- Latin phrases: in situ, inter alia, in toto, in vivo, in vitro, a priori, a posteriori
- Signal-to-noise ratio (SNR), O ring, T junction, Y-connected circuit
- Class designations: class-A amplifier
- Transistor numbers: 2N5090 transistor
- Programming language names: Fortran IV, Algol 60, Cobol, PL/1, BAL, Atlas Autocode

## Spacing Rules

A thin space is approximately one-fifth of an em space. These thin spaces are required on either side of roman functions and differentials to separate them visually from adjacent variables.

**Functions:**

- Correct: `sin t = log mu` (thin spaces around sin and log)
- Incorrect: `sint = logmu` (no spaces -- function name runs into variable)

**Differentials:**

- Correct: integral of `f(x) dx` with thin space before *dx*
- Incorrect: integral of `f(x)dx` with no space before *dx*

**Exception:** Thin spaces are NOT needed when a function or differential is directly preceded or followed by a verb (=, >=, <=) or an operator (+, -, etc.). The verb or operator spacing provides sufficient separation.

## Theorems and Proofs

**Theorem headings:** Set the theorem number as a tertiary heading (no Arabic numeral preceding). Example: use "Theorem 1" as a third-level heading, not "3. Theorem 1" or "III. Theorem 1."

**Proof headings:** Set the proof heading as a quaternary heading (fourth-level heading). Example: "Proof" or "Proof of Theorem 1" as a fourth-level heading.

**Same rule applies to:** Lemmas, Hypotheses, Propositions, Definitions, Conditions, Corollaries, and similar constructs. Each follows the same tertiary/quaternary heading pattern.

Articles that do not conform to an outline style for theorems and proofs should be adapted to the normal heading sequence described above.

## Common Symbols and Notation

### Approximation Symbols -- Distinctions Matter

| Symbol | LaTeX | Meaning | Usage |
|--------|-------|---------|-------|
| ≈ | `\approx` | approximately equal | Between numbers: pi ≈ 3.14159 |
| ≃ | `\simeq` | asymptotically equal | Between functions: f(x) ≃ g(x) as x -> inf |
| ∼ | `\sim` | of the order of / proportional to / distributed as | Proportionality: f(x) ∼ g(x); distributions: X ∼ N(0,1) |
| ≅ | `\cong` | congruent / isomorphic | Between geometric figures or algebraic structures |

Do not use ≃ between numbers (use ≈). Do not use ≈ for asymptotic equivalence of functions (use ≃).

### Set Theory

| Symbol | Meaning |
|--------|---------|
| ⊂ | Is contained in / proper subset |
| ⊃ | Contains / proper superset |
| ⊆ | Contained as subclass within / is identical to |
| ⊇ | Contains as subclass |
| ∪ | Union (colloquially "cup") |
| ∩ | Intersection (colloquially "cap") |
| ∈ | Is an element of |
| ∉ | Is not an element of |
| ∅ | Empty set |

### Logic

| Symbol | Meaning |
|--------|---------|
| ∀ | For all |
| ∃ | There exists |
| ∴ | Therefore |
| ∵ | Because / since |
| ≡ | Congruent to / definitional identity / is identical to |
| ∧ | Conjunction (AND) |
| ∨ | Disjunction (OR) |

### Arrows

| Symbol | Meaning |
|--------|---------|
| → | Approaches / tends to the limit / implies (logic) |
| ← | Relata of a relation |
| ⇒ | Implies (double arrow) / converges to |
| ⇐ | Is implied by |
| ⇔ | Implies and is implied by / if and only if |
| ↔ | Mutually implies / one-to-one correspondence |
| ↑ | Tends up to the limit |
| ↓ | Tends down to the limit |

### Other Common Symbols

| Symbol | Meaning |
|--------|---------|
| ∞ | Infinity |
| ∝ | Varies as / proportional to |
| ∇ | Nabla / del / backward finite-difference operator |
| ∂ | Partial differentiation |
| ℘ | Weierstrass elliptic function |
| ℵ | Aleph; ℵ₀ = number of finite integers, ℵ₁, ℵ₂, ... = transfinite cardinals |
| Γ | Gamma function (when used as function, not variable) |
| ∫ | Integral |
| ∮ | Contour integral |
| | | Modulus (\|x\|), joint denial (p \| q), or divides (3 \| 6) |
| ‖ | Parallel to |
| ± | Plus or minus |
| ∓ | Minus or plus |
| × | Multiply |
| ÷ | Divide |

### Order Notation

| Notation | Meaning |
|----------|---------|
| O(x) | Of order; same order as x (big-O) |
| o(x) | Of lower order than x (little-o) |

Both O and o are set in roman type.

### Fence Hierarchy

When nesting fences (delimiters), use the following hierarchy from innermost to outermost:

    ( { [ ( ) ] } )

That is: parentheses innermost, then brackets, then braces, then parentheses again for the outermost level. Angle brackets (distinct from less-than / greater-than signs) may also be used as fences.

### Glossary of Key Terms

- **Baseline:** The imaginary line connecting the bottoms of capital letters.
- **Collective signs:** Sums (Sigma), products (Pi), unions, and integrals.
- **Differential:** Identifiable as *d* or delta (Delta, delta) combinations.
- **Em quad:** Unit of linear measurement equal to the point size of the type font.
- **En quad:** Half an em quad.
- **Fences:** Signs of aggregation -- parentheses ( ), brackets [ ], braces { }, angle brackets.
- **Indices:** Subscripts and superscripts. First-order indices attach directly to a symbol; second-order indices are sub/superscripts of first-order indices. Plural: "indices" (not "indexes" in math context).
- **Matrix:** A rectangular array of mathematical terms written between fences.
- **Operator:** A symbol indicating an operation: +, -, /, x.
- **Solidus:** A slanted line used in fractions (e.g., 3/4). Also known as "shilling."
- **Stacked fraction:** A fraction with numerator above a rule and denominator below (also "built up").
- **Verb:** A mathematical symbol indicating a relationship: =, >=, <=, >, <, etc.
