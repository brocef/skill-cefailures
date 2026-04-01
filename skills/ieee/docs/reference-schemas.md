# IEEE Reference Schemas: TypeBox Modeling Guide

TypeBox schema patterns for modeling IEEE citation reference types in TypeScript.
Synthesized from the field requirements across all 20 IEEE reference categories.

---

## Field Taxonomy

Fields are grouped into three tiers based on how many reference types use them.

### Universal Fields

Present in nearly all reference types (with name variations noted):

| Field | Types That Use It | Notes |
|-------|------------------|-------|
| `authors` | All except Handbooks, Standards (no-author variant), Courses (online) | Array of person names; patents use `inventors` |
| `title` | All types | Paper title, book title, patent title, case name, etc. |
| `year` | All types | Publication year; use `"(n.d.)"` if unavailable |

### Common Fields

Used by many but not all reference types:

| Field | Types That Use It |
|-------|------------------|
| `volume` | Periodicals, Conference Proceedings, Books (series), Legal (court) |
| `number` / `issueNumber` | Periodicals |
| `pages` | Periodicals, Conference Proceedings, Books, Legal, Government |
| `publisher` | Books, Handbooks, Manuals, Software, Datasets |
| `address` | Books, Handbooks, Manuals, Reports, Theses |
| `doi` | Periodicals, Conference Proceedings, Datasets |
| `url` | Online variants of all types |
| `accessedDate` | Online Books, Manuals, Websites, Videos, Software, Datasets |
| `edition` | Books, Handbooks, Manuals |
| `editors` | Books, Conference Proceedings (rare) |
| `month` | Periodicals, Reports, Patents, News Articles, Blogs |

### Type-Specific Fields

Unique to one or a few reference types:

| Field | Type(s) |
|-------|---------|
| `conferenceName` / `proceedingsTitle` | Conferences |
| `periodicalTitle`, `articleId`, `earlyAccess` | Periodicals |
| `thesisType`, `department`, `university` | Theses |
| `reportNumber`, `reportType`, `institutionName` | Reports (also Courses) |
| `patentNumber`, `patentCountry` | Patents |
| `standardNumber`, `corporateAuthor` | Standards |
| `caseName`, `reporter`, `courtName`, `seriesName` | Legal Citations |
| `legislativeBody`, `congressNumber`, `session`, `billNumber` | Government Documents |
| `blogName` | Blogs |
| `newsSource` | News Articles |
| `websiteTitle` | Websites |
| `videoCreator`, `releaseDate`, `location` | Online Video |
| `softwareVersion` | Software |
| `datasetVersion`, `distributor` | Datasets |
| `courseTitle`, `semester` | Courses |
| `arxivId` | Unpublished (arXiv preprint) |
| `language`, `translator`, `seriesTitle` | Books/Periodicals (foreign/series) |

---

## TypeBox Schema Patterns

Use a discriminated union on the `type` field. Each reference category gets its own
schema that composes shared base types with category-specific fields.

### Shared Types

```typescript
import { Type, type Static } from '@sinclair/typebox'

// Person name: initials + last name, optional suffix
const IeeeAuthor = Type.Object({
  initials: Type.String({ description: 'First/middle initials, e.g. "J. K."' }),
  lastName: Type.String({ description: 'Last name, e.g. "Author"' }),
  suffix: Type.Optional(Type.String({ description: 'Jr., Sr., III, etc.' }))
})
type IeeeAuthor = Static<typeof IeeeAuthor>

// Flexible date: year required, month/day optional
const IeeeDate = Type.Object({
  year: Type.String({ description: 'Four-digit year or "(n.d.)" if unavailable' }),
  month: Type.Optional(Type.String({
    description: 'IEEE abbreviated month: "Jan.", "Feb.", ..., "Dec.", or slash form "Jan./Feb."'
  })),
  day: Type.Optional(Type.String({ description: 'Day of month as string' }))
})
type IeeeDate = Static<typeof IeeeDate>

// Page range: strings to handle Roman numerals and article IDs
const IeeePages = Type.Object({
  startPage: Type.String(),
  endPage: Type.Optional(Type.String())
})
type IeeePages = Static<typeof IeeePages>
```

### Base Reference Schema

Universal fields shared across almost all reference types:

```typescript
const IeeeReferenceBase = Type.Object({
  authors: Type.Array(IeeeAuthor, { minItems: 1 }),
  title: Type.String({ minLength: 1 }),
  date: IeeeDate
})
```

### Representative Type Schemas

Three complete schemas that establish the composition pattern. Remaining types
follow the same approach -- compose `IeeeReferenceBase` fields with type-specific
fields via `Type.Intersect`.

#### Book

```typescript
const IeeeBook = Type.Intersect([
  IeeeReferenceBase,
  Type.Object({
    type: Type.Literal('book'),
    publisherCity: Type.String(),
    publisherCountry: Type.String(),
    publisher: Type.String(),
    chapterTitle: Type.Optional(Type.String()),
    edition: Type.Optional(Type.String()),
    volume: Type.Optional(Type.String()),
    seriesTitle: Type.Optional(Type.String()),
    editors: Type.Optional(Type.Array(IeeeAuthor)),
    translator: Type.Optional(Type.String()),
    language: Type.Optional(Type.String()),
    chapterNumber: Type.Optional(Type.String()),
    sectionNumber: Type.Optional(Type.String()),
    pages: Type.Optional(IeeePages),
    publisherState: Type.Optional(Type.String({ description: 'Two-letter U.S. state only' })),
    url: Type.Optional(Type.String()),
    accessedDate: Type.Optional(IeeeDate),
    doi: Type.Optional(Type.String({ pattern: '^10\\.\\d{4,}/\\S+$' }))
  })
])
type IeeeBook = Static<typeof IeeeBook>
```

#### Conference

```typescript
const IeeeConference = Type.Intersect([
  IeeeReferenceBase,
  Type.Object({
    type: Type.Literal('conference'),
    conferenceName: Type.String({ description: 'Abbreviated conference name' }),
    pages: Type.Optional(IeeePages),
    location: Type.Optional(Type.Object({
      city: Type.String(),
      state: Type.Optional(Type.String()),
      country: Type.Optional(Type.String())
    })),
    editors: Type.Optional(Type.Array(IeeeAuthor)),
    volumeTitle: Type.Optional(Type.String()),
    seriesTitle: Type.Optional(Type.String()),
    edition: Type.Optional(Type.String()),
    monthDays: Type.Optional(Type.String({ description: 'e.g. "Nov. 9-12"' })),
    paperNumber: Type.Optional(Type.String()),
    doi: Type.Optional(Type.String({ pattern: '^10\\.\\d{4,}/\\S+$' })),
    url: Type.Optional(Type.String()),
    accessedDate: Type.Optional(IeeeDate),
    presented: Type.Optional(Type.Boolean({
      description: 'true if presented but not published in proceedings'
    }))
  })
])
type IeeeConference = Static<typeof IeeeConference>
```

#### Periodical

```typescript
const IeeePeriodical = Type.Intersect([
  IeeeReferenceBase,
  Type.Object({
    type: Type.Literal('periodical'),
    periodicalTitle: Type.String({ description: 'Abbreviated periodical title' }),
    volume: Type.String(),
    issueNumber: Type.Optional(Type.String()),
    pages: Type.Optional(IeeePages),
    articleId: Type.Optional(Type.String({
      description: 'Article ID when no page range exists'
    })),
    doi: Type.Optional(Type.String({ pattern: '^10\\.\\d{4,}/\\S+$' })),
    earlyAccess: Type.Optional(Type.Boolean()),
    language: Type.Optional(Type.String()),
    url: Type.Optional(Type.String()),
    accessedDate: Type.Optional(IeeeDate)
  })
])
type IeeePeriodical = Static<typeof IeeePeriodical>
```

### Top-Level Union

```typescript
const IeeeReference = Type.Union([
  IeeeBook,
  IeeeConference,
  IeeePeriodical,
  // IeeeThesis,
  // IeeeReport,
  // IeeeLecture,
  // IeeeCourse,
  // IeeeUnpublished,
  // IeeeBlog,
  // IeeeDataset,
  // IeeeNewsArticle,
  // IeeeOnlineVideo,
  // IeeeSoftware,
  // IeeeWebsite,
  // IeeePatent,
  // IeeeStandard,
  // IeeeHandbook,
  // IeeeManual,
  // IeeeLegalCitation,
  // IeeeGovernmentDocument
])
type IeeeReference = Static<typeof IeeeReference>
```

The `type` literal on each variant acts as the discriminator. TypeBox unions
matched against a `Type.Literal` field allow runtime validators to quickly
identify which branch applies.

Remaining type schemas follow the same pattern: intersect `IeeeReferenceBase`
with a type-specific object containing the `Type.Literal` discriminator and
the required/optional fields listed in the reference type docs.

For types without a personal author (Handbooks, Standards without corporate
author, online Courses), define a standalone `Type.Object` that omits `authors`
rather than intersecting with the base:

```typescript
const IeeeHandbook = Type.Object({
  type: Type.Literal('handbook'),
  title: Type.String({ minLength: 1 }),
  date: IeeeDate,
  publisher: Type.String(),
  publisherCity: Type.String(),
  publisherState: Type.Optional(Type.String()),
  edition: Type.Optional(Type.String()),
  pages: Type.Optional(IeeePages)
})
```

---

## Validation Rules

Constraints beyond what the JSON Schema shape expresses. Apply these as
refinements (`Type.Refine`) or in application-level validation logic.

### Author Count and "et al."

The schema stores all authors. The "et al." cutoff (max 6 before truncation)
is a rendering concern -- the renderer lists the first author plus "et al."
when there are 7+ authors.

### Required Field Rules

- `title`: always required, non-empty string.
- `year`: always required. Use `"(n.d.)"` if publication date is unavailable.
- `volume`: required for Periodicals.
- `conferenceName`: required for Conferences.
- `periodicalTitle`: required for Periodicals.
- `patentNumber`: required for Patents.
- `standardNumber`: required for Standards.

### DOI Format

Pattern: `^10\.\d{4,}/\S+$`. Store the bare DOI without the `doi:` prefix
(the prefix is added at render time). Example: `10.1109/LCOMM.2018.2886261`.

### URL and Accessed Date

If `url` is present, `accessedDate` should also be present. This is a soft
validation (warning) -- some URL references do not require an accessed date
(e.g., DOI-resolved URLs, stable archives).

### Month Values

IEEE months use abbreviated form with trailing period (except "May"):
`"Jan."`, `"Feb."`, `"Mar."`, `"Apr."`, `"May"`, `"Jun."`, `"Jul."`, `"Aug."`, `"Sep."`, `"Oct."`, `"Nov."`, `"Dec."`

Two-month ranges use a slash: `"Jan./Feb."`, `"Jul./Aug."`, etc.

```typescript
const IeeeMonth = Type.Union([
  Type.Literal('Jan.'), Type.Literal('Feb.'), Type.Literal('Mar.'),
  Type.Literal('Apr.'), Type.Literal('May'),  Type.Literal('Jun.'),
  Type.Literal('Jul.'), Type.Literal('Aug.'), Type.Literal('Sep.'),
  Type.Literal('Oct.'), Type.Literal('Nov.'), Type.Literal('Dec.')
])
```

For slash forms, widen with `Type.String({ pattern: '...' })`.

### Page Ranges

Pages are strings (not numbers) to handle Roman numerals, article IDs, and
en-dash ranges. `IeeePages` uses `startPage` and optional `endPage`.

### Thesis Type and Patent Country

```typescript
const ThesisType = Type.Union([
  Type.Literal('M.S. thesis'),
  Type.Literal('Ph.D. dissertation'),
  Type.Literal('Ph.D. thesis')
])
```

Patent country defaults to `"U.S."`. Non-U.S. patents include the country
code before "Patent" (e.g., `"RU"`).

---

## Rendering to IEEE String

Strategy for assembling a formatted reference string from a populated schema
object. Each reference type doc contains the exact format template; this
section describes the general rendering approach.

### Field Ordering Pattern

IEEE references follow a consistent general ordering, adapted per type:

1. **Authors** -- initials then last name, comma-separated, "and" before last
2. **Title** -- in quotes for papers/chapters; italicized for books/standards
3. **Source container** -- preceded by "in" for conference proceedings and
   book chapters; periodical title for journal articles
4. **Editors** -- if applicable, after "in Title," before publisher
5. **Edition / Volume / Series** -- when present
6. **Publisher info** -- city, state, country: publisher name
7. **Date** -- month and year, or full date for patents/news
8. **Pages** -- `pp. xxx-xxx` or `ch. x, sect. x, pp. xxx-xxx`
9. **DOI** -- `doi: 10.xxxx/xxxxx.`
10. **URL** -- `[Online]. Available: URL` (no trailing period after URL)

### Punctuation Rules

- Commas separate most fields. Periods end the reference (except when last element is a URL).
- "in" precedes conference proceedings titles and book chapter containers.
- Colon separates publisher location from name: `New York, NY, USA: Wiley`
- Parentheses for supplementary info: `(in Japanese)`, `(Justice Brandeis, dissenting)`
- Square brackets for medium/access tags: `[Online]`, `[Online Video]`, `[PowerPoint slides]`

### Discriminator-Driven Templates

The `type` field determines which rendering template to apply:

```typescript
function renderReference(ref: IeeeReference): string {
  switch (ref.type) {
    case 'book':       return renderBook(ref)
    case 'conference': return renderConference(ref)
    case 'periodical': return renderPeriodical(ref)
    // ... remaining types
  }
}
```

Each renderer follows the format template from the corresponding reference type doc.

### Author Rendering

1. Format each author as `"I. I. LastName"` (initials with periods, then last name).
2. If a suffix exists, append without comma: `"W. P. Pratt Jr."`
3. For 1 author: just the name.
4. For 2 authors: `"A. First and B. Second"`
5. For 3-6 authors: `"A. First, B. Second, and C. Third"`
6. For 7+ authors: `"A. First et al."`

### Handling Special States

- **Early access (Periodicals):** Insert "early access" after periodical title; always include DOI.
- **"To be published":** Replace date/pages with `"to be published."`
- **"Submitted for publication":** Replace source info with `"submitted for publication."`
- **Private communication:** No title; render as `"A. Author, private communication, Mon. year."`

### URL and DOI Placement

- DOI appears before URL when both are present.
- DOI format in output: `doi: 10.xxxx/xxxxx.` (with trailing period).
- URL format: `[Online]. Available: URL` (no trailing period).
- For websites, the tag is `[Online.]` (period inside bracket).
- For videos, the tag is `[Online Video]`.
- Accessed date, when present, appears before the medium tag:
  `Accessed: Mon. Day, Year. [Online]. Available: URL`
