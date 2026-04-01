# IEEE Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a comprehensive IEEE style skill with 7 docs files covering editorial style, math notation, reference types, citation schemas, and citing rules — sourced from three official IEEE guideline documents.

**Architecture:** A `SKILL.md` routing file with frontmatter/triggers/reference table/inlined key patterns, backed by 7 topic docs in `docs/`. Content is extracted from three IEEE HTML source files (already unzipped to `/tmp/ieee_extract/`), distilled into focused markdown, and organized by task domain. Reference types are grouped into 3 files by domain; schemas doc provides TypeBox guidance; citing-rules, editorial-style, and math-style cover the remaining domains.

**Tech Stack:** Markdown skill files, TypeBox (for schema guidance in `reference-schemas.md`)

**Source files (pre-extracted to /tmp/ieee_extract/):**
- `/tmp/ieee_extract/IEEE Reference Style Guide for Authors/IEEEReferenceStyleGuideforAuthors.html`
- `/tmp/ieee_extract/IEEE Editorial Style Manual for Authors/IEEEEditorialStyleManualforAuthors.html`
- `/tmp/ieee_extract/IEEE Mathematics Style Guide for Authors/IEEEMathematicsStyleGuideforAuthors.html`

If the `/tmp/ieee_extract/` directory doesn't exist, re-extract from the zip files in the repo root:
```bash
mkdir -p /tmp/ieee_extract && for f in *.zip; do unzip -o "$f" -d /tmp/ieee_extract/"$(basename "$f" .zip)"/; done
```

**Spec:** `docs/superpowers/specs/2026-03-31-ieee-skill-design.md`

**Existing skill to use as structural reference:** `skills/elkjs/SKILL.md` and `skills/elkjs/docs/`

---

### Task 1: Create SKILL.md Router

**Files:**
- Create: `skills/ieee/SKILL.md`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p skills/ieee/docs
```

- [ ] **Step 2: Write SKILL.md**

Create `skills/ieee/SKILL.md` with the following content. Follow the exact structure of `skills/elkjs/SKILL.md` — frontmatter, overview, "When to Use" triggers, reference table, and inlined key patterns:

```markdown
---
name: ieee
description: Use when writing, reviewing, or building software involving IEEE style — covers editorial style, reference/citation formatting, mathematical notation, and TypeBox schema derivation for IEEE reference types.
---

# ieee

Comprehensive IEEE style knowledge for writing/editing IEEE-compliant text and for building software that models IEEE citation types. Based on three official IEEE guidelines: the Reference Style Guide, Editorial Style Manual, and Mathematics Style Guide for Authors.

## When to Use

- Writing or reviewing text that should follow IEEE style
- Formatting references or citations in IEEE style
- Building data models / schemas for IEEE citation types
- Structuring an IEEE article (sections, headings, abstract, footnotes)
- Formatting mathematical equations for IEEE publications
- Checking grammar, hyphenation, abbreviations, or inclusive language per IEEE rules

## Reference

Read the relevant doc based on your task:

- **Academic Reference Types** — `docs/reference-types-academic.md` — Conferences, periodicals, theses/dissertations, reports, lectures, courses, unpublished works
- **Media & Online Reference Types** — `docs/reference-types-media.md` — Books, blogs, websites, online videos, software, datasets, news articles
- **Formal/Legal Reference Types** — `docs/reference-types-formal.md` — Patents, standards, handbooks, manuals, legal citations, government documents
- **TypeBox Schemas for References** — `docs/reference-schemas.md` — Field taxonomy, TypeBox schema patterns, required vs optional fields, validation rules, rendering to IEEE string
- **Citing & Formatting Mechanics** — `docs/citing-rules.md` — In-text citation syntax, abbreviation rules/patterns, DOI/URL placement, author name formatting
- **Editorial Style & Writing** — `docs/editorial-style.md` — Article structure, writing conventions, grammar/usage, acronyms, inclusive language, special paper types
- **Math Notation & Equations** — `docs/math-style.md` — Equation formatting, break/alignment, italic vs roman, numbered equations, symbols/functions

## Key Patterns

- References use numbered square brackets `[1]`, treated as nouns or footnotes in text
- Author format: initials before last name (e.g., `A. B. Author`)
- Paper titles in quotes, book/periodical titles in italics
- Up to 6 authors listed; beyond 6 use "et al."
- Every reference ends with a period (except those ending with a URL)
- DOI format: `doi: 10.xxxx/xxxxx.`
- American English spelling (Merriam-Webster first spelling); no contractions
- Serial/Oxford comma required; "that" (restrictive) vs "which" (nonrestrictive)
- Variables italic, vectors boldface italic, function names/units/abbreviations roman
```

- [ ] **Step 3: Verify the file renders correctly**

```bash
cat skills/ieee/SKILL.md
```

Confirm: frontmatter has `name` and `description`, the 7 reference table entries point to docs paths that match the plan, key patterns are present.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/SKILL.md
git commit -m "Add IEEE skill SKILL.md router"
```

---

### Task 2: Create citing-rules.md

**Files:**
- Create: `skills/ieee/docs/citing-rules.md`
- Read: `/tmp/ieee_extract/IEEE Reference Style Guide for Authors/IEEEReferenceStyleGuideforAuthors.html` — Sections I (Citing References), II intro (general style rules), III (Notes About Online References), and IV-A (Common Abbreviations — extract rules/patterns only, not full table)

- [ ] **Step 1: Read the source HTML**

Read the IEEE Reference Style Guide HTML. Focus on:
- **Section I** ("Citing References"): subsections A (References in Text) and B (Citing Parts of a Reference)
- **Section II intro** (before subsection A): the general formatting rules that apply across all reference types
- **Section III** ("Notes About Online References"): DOI/URL ordering, accessed date format, URL breaking rules
- **Section IV-A** ("Common Abbreviations"): extract only the abbreviation *rules and patterns* (e.g., "-ology" → "-ol.", "-graphy" → "-gr.", compound word rules) plus the ~30 most common abbreviations (Proc., Conf., Int., Symp., Trans., Dept., Univ., Lab., Inst., Amer., Assoc., Soc., Technol., Electron., Commun., Comput., Inform., Appl., Eng., Sci., Nat., Res., Rev., Dig., Rec., Coll., Annu.)

- [ ] **Step 2: Write citing-rules.md**

Create `skills/ieee/docs/citing-rules.md` with these sections:

1. **In-Text Citation Syntax** — Square bracket numbering `[1]`, treating as nouns ("as shown in [3]") vs footnotes ("...is shown [3]"), citing specific parts (`[3, Thm. 1]`, `[3, pp. 5-10]`, `[3, Fig. 2]`, `[3, eq. (8)]`, `[3, Sec. IV]`, `[3, Appendix A]`, `[3, Algorithm 1]`), no "ibid." or "op. cit." — always repeat the reference number
2. **Author Name Formatting** — Initials before last name (`A. B. Author`), no commas around Jr./Sr./III, up to 6 authors then "et al." (for IEEE publications), editor notation "Ed."/"Eds." after name(s)
3. **General Reference Punctuation** — Paper/article titles in quotes, book/journal/periodical titles in italics, period at end of every reference (except URL-ending ones), one reference number = one reference (no combined references), at least a year required ("(n.d.)" if unavailable), two-month issues use slash (Jul./Aug.)
4. **Abbreviation Rules and Patterns** — The systematic rules: "-ology" → "-ol.", "-graphy" → "-gr.", compound words use abbreviation of last word, conference names use ordinal numbers (1st, 2nd) and omit articles/prepositions ("of the", "on"). Then the curated list of ~30 most common abbreviations.
5. **DOI and URL Placement** — DOI format (`doi: 10.xxxx/xxxxx.`), DOI placement rules relative to URLs, accessed date format (`Accessed: Mon. Day, Year.`), no trailing period after URLs, `[Online]. Available:` before URLs
6. **URL Line-Breaking Rules** — Break after slash/double-slash/period, break before tilde/hyphen/underscore/question mark/percent, break before or after equals/ampersand

Target length: 200-350 lines. Include 2-3 concrete examples per section where the source provides them.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/citing-rules.md
```

Confirm the file has all 6 sections, concrete examples, and stays within target length.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/citing-rules.md
git commit -m "Add IEEE citing rules doc"
```

---

### Task 3: Create reference-types-academic.md

**Files:**
- Create: `skills/ieee/docs/reference-types-academic.md`
- Read: `/tmp/ieee_extract/IEEE Reference Style Guide for Authors/IEEEReferenceStyleGuideforAuthors.html` — Section II subsections C (Conferences), D (Courses), G (Lectures), M (Periodicals), N (Reports), Q (Theses), S (Unpublished)

- [ ] **Step 1: Read the source HTML**

Read the IEEE Reference Style Guide HTML. For each of the 7 categories below, extract:
- The **Basic Format** template (the field-order pattern with punctuation)
- All **subtypes/variations** listed
- 1-2 representative **examples** per category (pick the most common subtypes)
- Any **notes** on special cases (e.g., early access, "to be published" vs "submitted for publication")

Categories to extract:
- **C** — Conferences/Proceedings (paper presented, proceedings print/online, with DOI, with editors, with location, with series)
- **M** — Periodicals (basic, with article ID, with DOI, early access, other language, online, virtual journal)
- **Q** — Theses/Dissertations (print, online; M.S. thesis vs Ph.D. dissertation)
- **N** — Reports (print, online; report number formatting)
- **G** — Lectures (lecture notes, online)
- **D** — Courses (course, coursepack)
- **S** — Unpublished (private communication, submitted/unpublished, arXiv preprint)

- [ ] **Step 2: Write reference-types-academic.md**

Create `skills/ieee/docs/reference-types-academic.md`. Structure each category as:

```markdown
## Category Name (IEEE Letter)

**Basic Format:**
`[#] A. B. Author, "Title," ...punctuation pattern...`

**Subtypes:** list of variations

**Required Fields:** field1, field2, ...
**Optional Fields:** field3, field4, ...

**Examples:**

[1] Example reference string...

[2] Example reference string...

**Notes:**
- Special case notes...
```

Cover all 7 categories. For Conferences and Periodicals (the two most common/complex), include 2-3 examples showing key variations. For the others, 1-2 examples each.

Target length: 250-400 lines.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/reference-types-academic.md
grep "^## " skills/ieee/docs/reference-types-academic.md
```

Confirm 7 `##` sections exist, each with Basic Format, Required/Optional Fields, and Examples.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/reference-types-academic.md
git commit -m "Add IEEE academic reference types doc"
```

---

### Task 4: Create reference-types-media.md

**Files:**
- Create: `skills/ieee/docs/reference-types-media.md`
- Read: `/tmp/ieee_extract/IEEE Reference Style Guide for Authors/IEEEReferenceStyleGuideforAuthors.html` — Section II subsections A (Blogs), B (Books), E (Datasets), J (News), K (Online Video), O (Software), T (Websites)

- [ ] **Step 1: Read the source HTML**

Read the IEEE Reference Style Guide HTML. For each of the 7 categories below, extract the same elements as Task 3 (basic format, subtypes, examples, notes).

Categories to extract:
- **B** — Books (basic, online, foreign/translated, with chapter title, with editor(s), with series/volume/edition)
- **A** — Blogs
- **T** — Websites (basic, social media)
- **K** — Online Video
- **O** — Software (with FORCE11 Software Citation Principles)
- **E** — Datasets (basic, using DOI, using DOI resolver, using website address)
- **J** — News Articles (print, online)

- [ ] **Step 2: Write reference-types-media.md**

Create `skills/ieee/docs/reference-types-media.md` using the same per-category structure as Task 3. Books is the most complex category here — include 2-3 examples covering the key variations (basic, with chapter, with editor). For the others, 1-2 examples each.

Target length: 250-400 lines.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/reference-types-media.md
grep "^## " skills/ieee/docs/reference-types-media.md
```

Confirm 7 `##` sections exist, each with Basic Format, Required/Optional Fields, and Examples.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/reference-types-media.md
git commit -m "Add IEEE media reference types doc"
```

---

### Task 5: Create reference-types-formal.md

**Files:**
- Create: `skills/ieee/docs/reference-types-formal.md`
- Read: `/tmp/ieee_extract/IEEE Reference Style Guide for Authors/IEEEReferenceStyleGuideforAuthors.html` — Section II subsections F (Handbooks), H (Legal), I (Manuals), L (Patents), P (Standards), R (Government)

- [ ] **Step 1: Read the source HTML**

Read the IEEE Reference Style Guide HTML. For each of the 6 categories below, extract the same elements as Tasks 3/4.

Categories to extract:
- **L** — Patents (print, online)
- **P** — Standards (print, online — e.g., ISO, IEEE standards)
- **F** — Handbooks (single format)
- **I** — Manuals (print, online)
- **H** — Legal Citations (U.S. Supreme Court, lower-court, U.S. laws)
- **R** — Government Documents (U.S. government, print, online)

- [ ] **Step 2: Write reference-types-formal.md**

Create `skills/ieee/docs/reference-types-formal.md` using the same per-category structure as Tasks 3/4. 1-2 examples per category.

Target length: 200-300 lines.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/reference-types-formal.md
grep "^## " skills/ieee/docs/reference-types-formal.md
```

Confirm 6 `##` sections exist, each with Basic Format, Required/Optional Fields, and Examples.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/reference-types-formal.md
git commit -m "Add IEEE formal/legal reference types doc"
```

---

### Task 6: Create reference-schemas.md

**Files:**
- Create: `skills/ieee/docs/reference-schemas.md`
- Read (for field requirements): all three `reference-types-*.md` files created in Tasks 3-5
- Read (for TypeBox patterns): `skills/typebox/SKILL.md` and `skills/typebox/docs/` as needed for TypeBox API reference

This task synthesizes the field requirements from the reference type docs into TypeBox schema guidance. It does NOT copy content from the IEEE HTML — it builds on top of the already-extracted reference type docs.

- [ ] **Step 1: Read the reference type docs and TypeBox skill**

Read:
- `skills/ieee/docs/reference-types-academic.md`
- `skills/ieee/docs/reference-types-media.md`
- `skills/ieee/docs/reference-types-formal.md`
- `skills/typebox/SKILL.md`

From the reference type docs, build a mental model of which fields appear in which types and which are required vs optional. From the TypeBox skill, understand the API for defining schemas.

- [ ] **Step 2: Write reference-schemas.md**

Create `skills/ieee/docs/reference-schemas.md` with these sections:

**1. Field Taxonomy**

A table mapping fields to reference types. Group fields into three tiers:

- **Universal** (almost all types): `authors` (or `inventors`/`assignees` for patents), `title`, `year`
- **Common** (many types): `volume`, `number`, `pages`, `publisher`, `address` (city/state/country), `doi`, `url`, `accessedDate`, `edition`, `editors`
- **Type-specific**: `conferenceTitle`, `proceedingsTitle`, `journalTitle`, `thesisType`, `reportNumber`, `patentNumber`, `standardNumber`, `courtName`, `blogName`, `datasetVersion`, `softwareVersion`, `platform`, `articleId`, `seriesTitle`

Present as a concise reference table showing which types use which fields.

**2. TypeBox Schema Patterns**

Show the recommended modeling approach:

- A discriminated union on a `type` literal field
- A shared `IeeeAuthor` schema: `Type.Object({ initials: Type.String(), lastName: Type.String(), suffix: Type.Optional(Type.String()) })`
- A shared `IeeeDate` schema for flexible date representation (year required, month optional, day optional, special values like "n.d.")
- A base `IeeeReferenceBase` with the universal fields
- One type-specific schema per reference category, composing the base with category-specific fields
- The top-level union: `Type.Union([IeeeBook, IeeeConference, IeeePeriodical, ...])` with `Type.Literal` discriminators

Show complete TypeBox code for:
- `IeeeAuthor`
- `IeeeDate`
- `IeeeReferenceBase`
- 3 representative type schemas (Book, Conference, Periodical) to establish the pattern
- A note that remaining types follow the same pattern, with required/optional fields per the reference type docs

**3. Validation Rules**

Constraints that go beyond schema shape:
- Max 6 authors before "et al." applies (schema allows any count; validation/rendering handles the cutoff)
- `title` is always required (non-empty string)
- `year` is required; use literal string `"(n.d.)"` if unavailable
- `doi` format: regex pattern `^10\.\d{4,}/\S+$`
- If `url` is present, `accessedDate` should be present (soft validation / warning)
- Month values must be IEEE abbreviated form: `"Jan."`, `"Feb."`, ..., `"Dec."`, or two-month slash: `"Jan./Feb."`
- Page ranges: `startPage` and `endPage` as strings (to handle Roman numerals, article IDs)

**4. Rendering to IEEE String**

Rules for assembling a formatted reference string from a populated schema object:
- General field ordering pattern (author, title, source, volume/issue, pages, date, DOI/URL)
- Punctuation between fields (commas, periods, "in" before conference proceedings)
- How the `type` discriminator drives the rendering template
- Handling "et al." at render time based on author count
- URL/DOI placement at the end
- Note: each reference type doc has the exact format template — this section explains the rendering *strategy*, not every template

Target length: 250-400 lines.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/reference-schemas.md
grep "^## " skills/ieee/docs/reference-schemas.md
grep "Type\." skills/ieee/docs/reference-schemas.md | head -5
```

Confirm 4 `##` sections exist, TypeBox code is present, and the file stays within target length.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/reference-schemas.md
git commit -m "Add IEEE reference schemas doc with TypeBox patterns"
```

---

### Task 7: Create editorial-style.md

**Files:**
- Create: `skills/ieee/docs/editorial-style.md`
- Read: `/tmp/ieee_extract/IEEE Editorial Style Manual for Authors/IEEEEditorialStyleManualforAuthors.html` — Sections I-III plus Appendix B (hyphenations) and Appendix E (inclusive language)

- [ ] **Step 1: Read the source HTML**

Read the IEEE Editorial Style Manual HTML. Focus on extracting:
- **Section I**: purpose and editing philosophy (brief summary only)
- **Section II-A**: article component ordering and formatting rules for each component (title, abstract, index terms, headings, footnotes, figures/tables, acknowledgment, biographies)
- **Section II-B through II-D**: body rules, special paper types
- **Section II-E**: writing style (acronyms, spelling, trademarks, hyphenation, en/em dash, grammar rules, capitalization, dates, percentages, math in text)
- **Section III**: grammar and usage (possessives, serial comma, that/which, semicolons, punctuation with quotes, compound nouns/modifiers, commonly confused words)
- **Appendix B**: curated subset of ~40 most commonly mishandled hyphenations/spellings
- **Appendix E**: inclusive language replacement table (key entries)

Skip Appendix A (acronyms — too large, Claude knows these), Appendix C (units — reference data), Appendix D (massive abbreviation table — reference data).

- [ ] **Step 2: Write editorial-style.md**

Create `skills/ieee/docs/editorial-style.md` with these 9 sections:

1. **Article Structure and Ordering** — Component sequence (title through biographies), four section heading levels (Roman numeral centered caps → lowercase letter double-indented run-in), drop cap for first letter of full-length articles
2. **Title and Byline Rules** — Title capitalization rules, ORCID requirement for corresponding author, membership grades, first footnote three-paragraph structure (dates/support, affiliations, supplementary)
3. **Writing Conventions** — American English, no contractions, "data" is plural, define acronyms in abstract AND body, no TM/R symbols, international date format (4 June 2002), percentages as numeral + %, unit only after last number in ranges (40-50 mm)
4. **Hyphenation and Compound Modifiers** — Compound modifiers before nouns hyphenated / not after, no hyphen after comparatives/superlatives, "-ly" adverbs no hyphen, en dash for ranges/pairs/opposites, em dash for parenthetical
5. **Grammar and Usage** — Serial/Oxford comma required, "that" (restrictive) vs "which" (nonrestrictive), semicolons between independent clauses, punctuation inside quotation marks (except colon/semicolon), no double parentheses (use brackets `[see (10)]`), curated list of commonly confused words (affect/effect, fewer/less, that/which, comprise/compose, etc.)
6. **Figures and Tables** — "Fig." always abbreviated, TABLE headings centered Roman numerals, no Lena image (effective April 2024), caption formatting, permission/copyright reuse requirements
7. **Special Paper Types** — Brief rules for: editorials (no abstract, signature at end), brief papers (abstract, initial cap, no bios), short papers/letters (no membership in byline, no bios), comments/replies ("In the above article [1]..."), corrections/errata (specific title formats), book reviews (em dash between title and author)
8. **Inclusive Language** — Key replacements table: blacklist→blocklist, whitelist→access list, master/slave→primary/secondary, man hours→work hours, manned→crewed, unmanned→autonomous, chairman→chairperson, single-blind→single-anonymous, A.D./B.C.→C.E./B.C.E.
9. **Common Hyphenations and Spellings** — Curated ~40 entries: acknowledgment (no "e"), analog (not analogue), appendixes, bandwidth, baseband, Boolean, Chebyshev, coauthor, crossover, database, eigenvalue, email, feedback, flowchart, formulas (not formulae), gauge (not gage), half-duplex, internet, login (n)/log in (v), microwave, nonlinear, offline, online, percent, preprocess, real time (n)/real-time (adj), setup (n)/set up (v), standalone, traveling, WiFi, worldwide

Target length: 300-450 lines.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/editorial-style.md
grep "^## " skills/ieee/docs/editorial-style.md
```

Confirm 9 `##` sections exist and file stays within target length.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/editorial-style.md
git commit -m "Add IEEE editorial style doc"
```

---

### Task 8: Create math-style.md

**Files:**
- Create: `skills/ieee/docs/math-style.md`
- Read: `/tmp/ieee_extract/IEEE Mathematics Style Guide for Authors/IEEEMathematicsStyleGuideforAuthors.html` — Sections A through L

- [ ] **Step 1: Read the source HTML**

Read the IEEE Mathematics Style Guide HTML. Focus on extracting:
- **Section A** (Language of Math): equations as grammar, punctuation rules
- **Section B** (Inline Equations): 5 rules for equations in running text
- **Section C** (Break/Alignment): 6 rules for displayed equation layout
- **Section D** (Exceptions): special cases for right-to-left equations, solidus, integrals
- **Section E** (Headings): theorem/proof/lemma heading conventions
- **Section F** (Numbered Equations): numbering conventions
- **Section G** (Reminders): algorithms, angle brackets, vectors, thin spaces
- **Section H** (Italic/Roman/Small Caps): the three-column reference table
- **Section I** (Roman Functions): the ~35 function names that must be roman
- **Section J** (Glossary): key term definitions (fences, indices, operators, verbs, etc.)
- **Section L** (Symbols): curated subset — focus on the most commonly needed symbols and the ones where distinctions matter (e.g., ≈ vs ≃ vs ∼ vs ≅)

Skip Section K (Greek alphabet — Claude knows this).

- [ ] **Step 2: Write math-style.md**

Create `skills/ieee/docs/math-style.md` with these 8 sections:

1. **Equations as Grammar** — Equations are sentences: nouns (variables), verbs (=, ≥, ≤, ≈, etc.), punctuation. Only end-of-equation punctuation is a period. Interior commas/semicolons carry mathematical meaning — do not alter. Ellipses: exactly 3 dots, enclosed by commas, on baseline. Multiple conditions separated by semicolons with 2em space before conditions.
2. **Inline Equation Rules** — 5 rules: (1) break after verb/operator, (2) no stacked fractions inline — use solidus, (3) collective signs (Σ, Π) limits to the side, (4) use `exp[...]` for long superscripts, (5) avoid long radical signs — use fractional exponents
3. **Displayed Equation Break/Alignment** — 6 rules: (1) break at verbs, align on verbs, (2) one verb: break at operators, align right of verb, (3) separate equations with em quad or stack aligned on verb, (4) two-line: flush left/flush right, (5) within fences: break at operator, align inside left fence, (6) period placement at end of fractions/case equations/closed delimiters. Fence pairs must match in size. Special cases: right-to-left equations, solidus as operator, implied product between fence sets, integrals/differentials.
4. **Equation Numbering** — Consecutive throughout article, parenthesized, flush right. Appendix equations may continue or restart as (A1), (A2). Sub-numbers: (1a) not (1-a), (2a) not (2.a). Some Transactions allow section-based: (1.1), (1.2.1).
5. **Italic vs Roman vs Bold** — Variables: always italic. Vectors: boldface italic. Function names, units, abbreviations: always roman. Complete list of ~35 roman functions: ad, arg, cos, cosh, cot, coth, csc, csch, curl, det, diag, dim, div, exp, hom, Im, inf, ker, lim, liminf, limsup, ln, log, lub, max, min, mod, Pr, Re, sec, sin, sinh, tan, tanh, tr, Tr, wr. Preferred abbreviations: "cot" not "ctg", "csc" not "cosec". Semiconductor terms in roman (p-n, p-i-n). Small caps for logic keywords (AND, OR, NOR, NAND, XOR). Circuit abbreviations in italic (RC, RL, LC).
6. **Spacing Rules** — Thin spaces (~1/5 em) on either side of roman functions and differentials (e.g., "sin t" not "sint"). NOT needed when preceded/followed by verbs (=, ≥) or operators (+, −).
7. **Theorems and Proofs** — Theorem number set as tertiary heading (no Arabic numeral). Proof heading as quaternary heading. Same rule for lemmas, hypotheses, propositions, definitions, conditions.
8. **Common Symbols and Notation** — Curated reference of frequently needed symbols with distinctions that matter:
   - Approximation: ≈ (approximately equal), ≃ (asymptotically equal), ∼ (of the order of / distributed as), ≅ (congruent/isomorphic)
   - Set theory: ⊂, ⊃, ∪, ∩, ∈, ∅
   - Logic: ∀, ∃, ∴ (therefore), ∵ (because)
   - Arrows: → (tends to / maps to), ⇒ (implies), ⇔ (if and only if), ↦ (maps to, specific element)
   - Other: ∞, ∝ (proportional to), ∇ (nabla/del), ∂ (partial), ℘ (Weierstrass), ℵ (aleph/transfinite)
   - Order notation: O(x) (big-O, same order), o(x) (little-o, smaller order)
   - Fence hierarchy: ( { [ ( ) ] } )

Target length: 250-400 lines.

- [ ] **Step 3: Verify**

```bash
wc -l skills/ieee/docs/math-style.md
grep "^## " skills/ieee/docs/math-style.md
```

Confirm 8 `##` sections exist and file stays within target length.

- [ ] **Step 4: Commit**

```bash
git add skills/ieee/docs/math-style.md
git commit -m "Add IEEE math style doc"
```

---

### Task 9: Install and Verify the Skill

**Files:**
- Read: `scripts/install_skill.py`

- [ ] **Step 1: List available skills to confirm ieee appears**

```bash
python scripts/install_skill.py --list
```

Expected: `ieee` appears in the list alongside elkjs, typebox, knex, etc.

- [ ] **Step 2: Install the ieee skill**

```bash
python scripts/install_skill.py ieee
```

Expected: symlink created at `~/.claude/skills/ieee` pointing to `skills/ieee`.

- [ ] **Step 3: Verify the symlink**

```bash
ls -la ~/.claude/skills/ieee
cat ~/.claude/skills/ieee/SKILL.md | head -20
```

Expected: symlink points to the repo's `skills/ieee/`, SKILL.md frontmatter is readable.

- [ ] **Step 4: Verify all docs are accessible through the symlink**

```bash
ls ~/.claude/skills/ieee/docs/
```

Expected output lists all 7 docs files:
```
citing-rules.md
editorial-style.md
math-style.md
reference-schemas.md
reference-types-academic.md
reference-types-formal.md
reference-types-media.md
```

- [ ] **Step 5: Final commit (if any fixes were needed)**

Only commit if verification revealed issues that required fixes. Otherwise, skip.
