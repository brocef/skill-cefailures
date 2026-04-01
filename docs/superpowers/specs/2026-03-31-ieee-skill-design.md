# IEEE Skill Design Spec

## Overview

A Claude Code skill providing comprehensive IEEE style knowledge for two use cases:

1. **Writing/editing** — reviewing and drafting IEEE-compliant text (articles, references, math notation)
2. **Software development** — deriving TypeBox schemas and validation logic for IEEE citation types in an application

The skill follows the existing repo pattern: a `SKILL.md` routing file with frontmatter, triggers, a reference table, and inlined key patterns, backed by `docs/*.md` topic files.

## Source Material

Three IEEE guidelines documents (zipped HTML from Google Docs):

- **IEEE Reference Style Guide for Authors** (v3.28.2025) — 20 reference type categories (A-T), citing rules, abbreviation/publisher/periodical lookup tables
- **IEEE Editorial Style Manual for Authors** (v3.25.2025) — Article structure, writing style, grammar/usage, acronyms, units, inclusive language, special paper types
- **IEEE Mathematics Style Guide for Authors** (v10.27.2023) — Equation formatting, break/alignment rules, italic/roman/bold conventions, symbols/functions

## Design Decisions

- **Format-agnostic**: The skill teaches logical rules (what to abbreviate, what's required, what's italic) without prescribing rendering technology (no LaTeX mapping). Claude bridges to LaTeX/HTML/etc. from its own knowledge.
- **Curated lookup tables**: Abbreviation, publisher, and symbol tables are distilled to rules and patterns plus the most common/tricky entries, not reproduced in full.
- **TypeBox schemas**: Reference type modeling uses TypeBox, leveraging the existing `typebox` skill in the repo. Schemas use discriminated unions on a `type` field.
- **Grouped reference types**: The 20 IEEE categories are grouped into 3 docs by domain (academic, media, formal/legal) rather than 20 individual files or one monolithic file.

## File Structure

```
skills/ieee/
  SKILL.md
  docs/
    reference-types-academic.md
    reference-types-media.md
    reference-types-formal.md
    reference-schemas.md
    citing-rules.md
    editorial-style.md
    math-style.md
```

## SKILL.md — Router

### Frontmatter

```yaml
name: ieee
description: Use when writing, reviewing, or building software involving IEEE style — covers editorial style, reference/citation formatting, mathematical notation, and TypeBox schema derivation for IEEE reference types.
```

### Triggers

- Writing or reviewing text that should follow IEEE style
- Formatting references or citations in IEEE style
- Building data models / schemas for IEEE citation types
- Structuring an IEEE article (sections, headings, abstract, footnotes)
- Formatting mathematical equations for IEEE publications
- Checking grammar, hyphenation, abbreviations, or inclusive language per IEEE rules

### Reference Table

| Task | Doc | Covers |
|------|-----|--------|
| Academic reference types | `docs/reference-types-academic.md` | Conferences, periodicals, theses/dissertations, reports, lectures, courses, unpublished |
| Media & online reference types | `docs/reference-types-media.md` | Books, blogs, websites, online videos, software, datasets, news articles |
| Formal/legal reference types | `docs/reference-types-formal.md` | Patents, standards, handbooks, manuals, legal citations, government documents |
| TypeBox schemas for references | `docs/reference-schemas.md` | Field taxonomy, TypeBox patterns, required vs optional fields, validation |
| Citing & formatting mechanics | `docs/citing-rules.md` | In-text citation syntax, abbreviation rules/patterns, DOI/URL placement, publisher abbreviations |
| Editorial style & writing | `docs/editorial-style.md` | Article structure, writing conventions, grammar/usage, acronyms, inclusive language, special paper types |
| Math notation & equations | `docs/math-style.md` | Equation formatting, break/alignment, italic vs roman, numbered equations, symbols/functions |

### Inlined Key Patterns

- References use numbered square brackets `[1]`, treated as nouns or footnotes in text
- Author format: initials before last name (e.g., `A. B. Author`)
- Paper titles in quotes, book/periodical titles in italics
- Up to 6 authors listed; beyond 6 use "et al."
- Every reference ends with a period (except those ending with a URL)
- DOI format: `doi: 10.xxxx/xxxxx.`

## Doc Specifications

### docs/reference-types-academic.md

Covers 7 IEEE reference categories. Each type includes: basic format template, required fields, optional fields, 1-2 examples, and notes on variations.

**Categories:**

1. **Conferences/Proceedings (C)** — Paper presented, proceedings in print/online, with DOI, with editors, with series title. Basic format: `[#] Author, "Title," in *Proc. Conf. Name*, City, State, Country, Year, pp. x-y.`
2. **Periodicals (M)** — Basic journal article, with article ID, with DOI, early access, other language, online, virtual journal. Basic format: `[#] Author, "Title," *Abbrev. J. Title*, vol. X, no. Y, pp. x-y, Month Year.`
3. **Theses/Dissertations (Q)** — Print and online. Distinguishes M.S. thesis vs Ph.D. dissertation.
4. **Reports (N)** — Technical reports, print and online. Includes report number formatting.
5. **Lectures (G)** — Lecture notes and online lectures.
6. **Courses (D)** — Course and coursepack citations.
7. **Unpublished (S)** — Private communication, submitted/unpublished, arXiv preprints.

### docs/reference-types-media.md

Covers 7 IEEE reference categories with the same per-type structure.

**Categories:**

1. **Books (B)** — Basic, online, foreign/translated, with chapter title, with editor(s), with series/volume/edition.
2. **Blogs (A)** — Blog post citation format.
3. **Websites (T)** — Basic website, social media.
4. **Online Video (K)** — e.g., YouTube videos.
5. **Software (O)** — With FORCE11 Software Citation Principles.
6. **Datasets (E)** — Basic, using DOI, using DOI resolver, using website address.
7. **News Articles (J)** — Print and online.

### docs/reference-types-formal.md

Covers 6 IEEE reference categories with the same per-type structure.

**Categories:**

1. **Patents (L)** — Print and online patent citations.
2. **Standards (P)** — Print and online (e.g., ISO, IEEE standards).
3. **Handbooks (F)** — Single format.
4. **Manuals (I)** — Print and online.
5. **Legal Citations (H)** — U.S. Supreme Court, lower-court, U.S. laws.
6. **Government Documents (R)** — U.S. government, print and online.

### docs/reference-schemas.md

Guidance for deriving TypeBox schemas from IEEE reference types.

**Sections:**

1. **Field taxonomy** — Unified field catalog across all 20 reference types:
   - Universal fields (almost all types): authors, title, year/date
   - Common fields: volume, number, pages, publisher, DOI, URL, accessed date
   - Type-specific fields: patent number, report number, court name, standard number, blog name, dataset version, etc.

2. **TypeBox pattern guidance** — How to model IEEE references:
   - Discriminated union on a `type` field (e.g., `"book"`, `"conference"`, `"periodical"`)
   - Base schema with shared fields, extended per type
   - Author modeling: array of `{ initials: string, lastName: string, suffix?: string }`
   - Page ranges, volume/issue numbers, date representations
   - Optional vs required fields per type (derived from IEEE "basic format" templates)

3. **Validation rules** — Constraints derived from IEEE rules:
   - Max 6 authors before "et al." triggers
   - Title always required
   - Year required; `"(n.d.)"` if unavailable
   - DOI format validation pattern
   - URL and accessed-date co-occurrence
   - Month abbreviation validation (three-letter + period, two-month slash format)

4. **Rendering from schema to IEEE string** — Field ordering and punctuation rules for assembling a formatted reference string from structured data.

### docs/citing-rules.md

Mechanics of citing and formatting references.

**Sections:**

1. **In-text citation syntax** — Square bracket numbering, references as nouns vs footnotes, citing specific parts (`[3, Thm. 1]`, `[3, pp. 5-10]`), no "ibid."/"op. cit.", cross-referencing figures/equations/sections within a cited work.

2. **Abbreviation rules and patterns** — The system, not the full tables:
   - "-ology" truncates after "-ol." (Technology -> Technol.)
   - "-graphy" truncates after "-gr."
   - Compound words abbreviate the last word
   - Conference name abbreviation: ordinal numbers, omit articles/prepositions
   - Curated list of ~30 most common abbreviations (Proc., Conf., Int., Symp., Trans., Dept., Univ., Lab., Inst., etc.)

3. **DOI and URL placement** — `doi: 10.xxxx/xxxxx.` format, DOI before vs after URL, accessed date format (`Accessed: Mon. Day, Year.`), no trailing period after URLs.

4. **URL line-breaking rules** — Break after slash/double-slash/period, break before tilde/hyphen/underscore/question mark/percent, break before or after equals/ampersand.

5. **Author name formatting** — Initials before last name, no commas around Jr./Sr./III, up to 6 authors then "et al.", editor notation "Ed."/"Eds."

6. **General punctuation** — Paper titles in quotes, book/periodical titles in italics, period at end (except URL-ending), one number = one reference.

### docs/editorial-style.md

Article structure, writing conventions, grammar, and inclusive language.

**Sections:**

1. **Article structure and ordering** — Standard component sequence: title, byline/ORCID, abstract (150-250 words, single paragraph), index terms, nomenclature, introduction, body, conclusion, appendix(es), acknowledgment (no "e"), references, biographies. Four section heading levels.

2. **Title and byline rules** — Title capitalization (capitalize nouns/verbs/adverbs, lowercase articles/short prepositions, capitalize prepositions 4+ letters). Membership grades. First footnote three-paragraph structure.

3. **Writing conventions** — American English (Merriam-Webster first spelling), no contractions, "data" is plural, acronym definition rules (define in abstract AND body), no TM/R symbols, international date format, percentages as numeral + %, unit ranges.

4. **Hyphenation and compound modifiers** — Compound modifiers hyphenated before nouns but not after, no hyphen after comparatives/superlatives, "-ly" adverbs need no hyphen. En dash for ranges/pairs. Em dash for parenthetical.

5. **Grammar and usage** — Serial/Oxford comma required, "that" (restrictive) vs "which" (nonrestrictive), semicolons between independent clauses, punctuation inside quotation marks (except colon/semicolon), no double parentheses. Curated commonly confused words.

6. **Figures and tables** — "Fig." always abbreviated, TABLE headings centered with Roman numerals, no Lena image (effective April 2024).

7. **Special paper types** — Editorials, brief papers, short papers/letters, comments/replies, corrections/errata, book reviews.

8. **Inclusive language** — Key replacements: blacklist->blocklist, master/slave->primary/secondary, man hours->work hours, chairman->chairperson, etc.

9. **Common hyphenations and spellings** — Curated subset of most commonly mishandled terms: acknowledgment, analog, appendixes, bandwidth, Boolean, coauthor, database, eigenvalue, flowchart, traveling, etc.

### docs/math-style.md

Equation formatting, notation, and typesetting rules.

**Sections:**

1. **Equations as grammar** — Equations are sentences with nouns (variables), verbs (=, >=), punctuation. Only end-of-equation punctuation is a period. Interior commas/semicolons carry mathematical meaning. Ellipses: 3 dots, enclosed by commas, on baseline.

2. **Inline equation rules** — Break after verb/operator, no stacked fractions (use solidus), collective sign limits to the side, use `exp[...]` for long superscripts, avoid long radicals.

3. **Displayed equation break/alignment** — Break at verbs, align on verbs. One verb: break at operators, align right of verb. Two-line: flush left/flush right. Within fences: break at operator, align inside left fence. Period placement for fractions/case equations.

4. **Equation numbering** — Consecutive, parenthesized, flush right. Appendix: continue or restart as (A1). Sub-numbers: (1a) not (1-a).

5. **Italic vs roman vs bold** — Variables italic, vectors boldface italic, functions/units/abbreviations roman. ~35 functions that must be roman (sin, cos, exp, det, lim, log, Re, Im, etc.). Semiconductor terms roman. Small caps for logic keywords (AND, OR, NOR).

6. **Spacing rules** — Thin spaces around roman functions and differentials. Not needed adjacent to verbs/operators.

7. **Theorems and proofs** — Theorem as tertiary heading, proof as quaternary heading. Same for lemmas, propositions, definitions, conditions.

8. **Common symbols and notation** — Curated reference: approximation variants (each with distinct meaning), set theory symbols, logical symbols, arrow conventions, fence hierarchy, order notation.
