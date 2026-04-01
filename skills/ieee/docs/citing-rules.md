# IEEE Citing and Formatting Mechanics

Rules for in-text citations, author name formatting, reference punctuation, title abbreviations, and DOI/URL placement. Based on the IEEE Reference Style Guide for Authors.

## In-Text Citation Syntax

References appear on the line in square brackets, inside the punctuation. They may be treated grammatically as **nouns** or as **footnote numbers**:

- As nouns: "According to [1]"; "as demonstrated in [2]"; "as shown by Brown [4], [5]"
- As footnotes: "...the results are shown [3]."
- Multiple references: "as mentioned earlier [2], [4], [5], [6], [7], [9]"
- With author names: "Smith [4] and Brown and Jones [5]"; "Wood et al. [7]"

### Reference ranges

Do **not** use en dashes for reference ranges. Write out all reference numbers individually:

- **Wrong:** `[1]--[4]`
- **Correct:** `[1], [2], [3], [4]`

### "et al." in text

Use "et al." when **three or more** author names are given for a reference cited in text.

### Citing parts of a reference

To cite a specific part, append it after the reference number with a comma:

```
[3, Thm. 1]        -- theorem
[3, Lemma 2]       -- lemma
[3, pp. 5--10]     -- page range
[3, eq. (2)]       -- equation
[3, Fig. 1]        -- figure
[3, Appendix I]    -- appendix
[3, Sect. 4.5]     -- section
[3, Ch. 2, pp. 5--10]  -- chapter and pages
[3, Algorithm 5]   -- algorithm
```

### No "ibid." or "op. cit."

Never use "ibid." or "op. cit." in IEEE references. These refer to a previous reference and must be eliminated. Instead, always repeat the earlier reference number. If the "ibid." gives a new page number or other information, use the part-citation forms above.

**Note:** Editing references may require careful renumbering of both the reference list and all in-text citations.

## Author Name Formatting

### Initials before last name

In all references, the given name of the author or editor is abbreviated to the initial only and **precedes** the last name:

```
A. B. Author
M. Smith Jr.
R. Barnett Sr.
L. Molignaro III
```

### No commas around suffixes

Do **not** use commas around Jr., Sr., and III in names:

- **Correct:** `Michael Smith Jr.`; `Ray Barnett Sr.`; `Lucas Molignaro III`
- **Wrong:** `Michael Smith, Jr.`; `Lucas Molignaro, III`

### Author count and "et al."

- **IEEE publications:** List all authors up to six names. If there are more than six, use the primary author's name followed by "et al."
- **Non-IEEE publications:** "et al." may be used if additional author names are not provided.

### Editor notation

Use "Ed." after a single editor's name and "Eds." after multiple editors:

```
J. S. Brake, Ed.
P. G. Harper and B. S. Wherret, Eds.
```

When a book has editors instead of authors, the notation follows the name(s):

```
M. Abramowitz and I. A. Stegun, Eds., Handbook of Mathematical Functions...
```

## General Reference Punctuation

### Title formatting

- **Paper and article titles** are enclosed in quotation marks: `"Name of paper,"`
- **Book, journal, and periodical titles** are in italics: `*Title of Published Book*`
- Periodical titles of only one word are not abbreviated but fully spelled out (e.g., *Science*, *Nature*)

### Ending punctuation

- Every reference ends with a **period**, including those with a DOI.
- **Exception:** references ending with a URL do not get a trailing period.
- If a reference contains both a DOI (or accessed date) and a URL, the DOI or accessed date is placed first followed by a period, then the URL (no period).

### One number, one reference

Do not combine references. There must be only **one reference per number**.

### Date requirements

All references must include at least a year of publication (or year of the accessed date). If no date is available, use `(n.d.)` in the position where the date would normally appear:

```
BAR50 Series Infineon PIN Diode Datasheet. (n.d.). [Online].
    Available: http://www.infineon.com
```

### Two-month issues

When a reference cites two months for the same issue, separate them with a slash:

```
Jul./Aug. 2023
```

### Early access articles

Early access articles should use the "Date of Publication" rather than the volume/issue publication date. Articles published within a volume use the volume and issue publication date.

## Abbreviation Rules and Patterns

### Systematic abbreviation rules for periodical titles

These rules apply when abbreviating periodical and conference names in references:

1. **"-ology" endings** -- truncate after "-ol.":
   - Gastroenterology --> Gastroenterol.
   - Endocrinology --> Endocrinol.
   - Technology --> Technol.

2. **"-graphy" endings** -- truncate after "-gr.":
   - Oceanography --> Oceanogr.
   - Crystallography --> Crystallogr.

3. **Compound words** -- abbreviate using the abbreviation of the last word:
   - Bioengineering --> Bioeng.
   - Nanobioscience --> Nanobiosci.

4. **One abbreviation for multiple forms** -- some abbreviations cover variant word forms:
   - "Mathematical" and "Mathematics" are both "Math."
   - "Medical" and "Medicine" are both "Med."
   - "Computational," "Computer(s)," and "Computing" are all "Comput."

5. **If no abbreviation exists** and the word cannot be abbreviated by the rules above, spell it out in full.

### Conference name abbreviations

Conference names use ordinal numbers and omit articles/prepositions:

| Written Out | Abbreviated |
|-------------|-------------|
| First | 1st |
| Second | 2nd |
| Third | 3rd |
| Fourth/nth | 4th/nth |
| Proceedings | Proc. |
| Conference | Conf. |
| Symposium | Symp. |
| International | Int. |
| Workshop | Workshop (no abbreviation) |

Omit most articles and prepositions ("of the", "on"):

```
Proceedings of the 1996 Robotics and Automation Conference
  --> Proc. 1996 Robot. Automat. Conf.
```

### Common abbreviations in references

The most frequently used abbreviations in IEEE references:

| Full Word | Abbreviation |
|-----------|-------------|
| Proceedings | Proc. |
| Conference | Conf. |
| International | Int. |
| Symposium | Symp. |
| Transactions | Trans. |
| Department | Dept. |
| University | Univ. |
| Laboratory(ies) | Lab. |
| Institute | Inst. |
| American | Amer. |
| Association | Assoc. |
| Society | Soc. |
| Technology | Technol. |
| Electronic | Electron. |
| Communications | Commun. |
| Computer(s)/Computing | Comput. |
| Informatics | Inform. |
| Information | Inf. |
| Applications/Applied | Appl. |
| Engineering | Eng. |
| Science | Sci. |
| National | Nat. |
| Research | Res. |
| Review | Rev. |
| Digest | Dig. |
| Record | Rec. |
| Colloquium | Colloq. |
| Annual | Annu. |
| Technical | Tech. |
| Theoretical | Theor. |

## DOI and URL Placement

### DOI format

DOIs use the format `doi: 10.xxxx/xxxxx.` (lowercase "doi", followed by a colon, then the identifier, ending with a period).

### Placement order

The order of DOI, accessed date, and URL in a reference follows these patterns (from most to least complete):

1. `Accessed: Mon. Day, Year. doi: 10.xxxx/xxxxx. [Online]. Available: URL` (no period at end)
2. `Accessed: Mon. Day, Year. [Online]. Available: URL` (no period at end)
3. `Accessed: Mon. Day, Year. doi: 10.xxxx/xxxxx.` (period at end)
4. `doi: 10.xxxx/xxxxx. URL` (no period at end)
5. `doi: 10.xxxx/xxxxx.` (period at end, when no URL)
6. `URL` (no period at end)

### Key rules

- References ending with a URL have **no trailing period**.
- References ending with a DOI **do** have a trailing period.
- When both DOI/accessed date and URL are present, the DOI or accessed date comes first, followed by a period, then the URL.
- The "Available" notation uses the form: `[Online]. Available: URL`

### Accessed date format

```
Accessed: May 19, 2014.
Accessed: Feb. 28, 2010.
```

The style is `Accessed: Abbrev. Month Day, Year.` -- note the period at the end. The placement of the accessed date should match how it is provided in the final author-submitted version.

### Complete examples

```
The Terahertz Wave eBook. ZOmega Terahertz Corp., 2014.
    Accessed: May 19, 2014. [Online]. Available:
    https://www.scribd.com/document/322662319/Thz-zomega-ebook-pdf

G. O. Young, "Synthetic structure of industrial plastics," in
    Plastics, vol. 3, J. Peters, Ed., 2nd ed. New York, NY, USA:
    McGraw-Hill, 1964, pp. 15--64. [Online]. Available:
    https://www.scirp.org
```

## URL Line-Breaking Rules

When a URL must be broken across lines, follow these rules to avoid ambiguity:

### Break after

- A slash (`/`)
- A double slash (`//`)
- A period (`.`)

### Break before

- A tilde (`~`)
- A hyphen (`-`) -- but do **not** break after a hyphen (to avoid confusion with hyphenation); do not add hyphens or spaces; do not let addresses hyphenate
- An underscore (`_`)
- A question mark (`?`)
- A percent symbol (`%`)

### Break before or after

- An equal sign (`=`)
- An ampersand (`&`)
- An "at" symbol (`@`) -- follow the same rule as for `=` and `&`

### Example

A URL like `https://example.com/path/to/resource?id=123&type=pdf` could be broken as:

```
https://example.com/path/to/
resource?id=123&type=pdf
```

or:

```
https://example.com/path/to/resource
?id=123&
type=pdf
```
