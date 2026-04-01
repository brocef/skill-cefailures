# IEEE Academic Reference Types

Reference format templates and examples for the 7 academic-oriented categories from the IEEE Reference Style Guide for Authors. Each category lists the basic format, subtypes, required/optional fields, representative examples, and notes on special cases.

Field abbreviations used below: Dept. = Department, Univ. = University, Conf. = Conference, Proc. = Proceedings, Symp. = Symposium, Int. = International, Rep. = Report.

---

## Conferences and Conference Proceedings (C)

**Basic Format:**
`[#] A. B. Author, "Title of paper," in Abbreviated Name of Conf., City, State, Country, year, pp. xxx-xxx.`

**Subtypes:**
- Conference paper (presented, not published in proceedings)
- Conference proceedings in print
- Conference proceedings with DOI
- Conference proceedings with editors
- Conference proceedings with location
- Conference proceedings with series title, volume title, and edition
- Conference paper online
- Conference proceedings online

**Required Fields:** author, title, conference_name, year
**Optional Fields:** location (city, state, country), pages, doi, editors, volume_title, series_title, edition, month_days, paper_number, url, medium_type

**Examples:**

[1] J. G. Kreifeldt, "An analysis of surface-detected EMG as an amplitude-modulated noise," presented at the 1989 Int. Conf. Med. Biol. Eng., Chicago, IL, USA, Nov. 9-12, 1989.

[2] S. P. Bingulac, "On the compatibility of adaptive controllers," in Proc. 4th Annu. Allerton Conf. Circuit Syst. Theory, New York, NY, USA, 1994, pp. 8-16.

[3] G. Veruggio, "The EURON roboethics roadmap," in Proc. Humanoids '06: 6th IEEE-RAS Int. Conf. Humanoid Robots, 2006, pp. 612-617, doi: 10.1109/ICHR.2006.321337.

[4] A. Amador-Perez and R. A. Rodriguez-Solis, "Analysis of a CPW-fed annular slot ring antenna using DOE," in Proc. IEEE Antennas Propag. Soc. Int. Symp., A. Amador-Perez and R. A. Rodriguez-Solis, Eds. Jul. 2006, pp. 4301-4304.

[5] T. Schubert, "Real challenges and solutions for validating system-on-chip high level formal verification of next-generation microprocessors," in Proc. 40th Design Automat. Conf. (DAC'03), Jun. 2-6, 2003. [Online]. Available: https://www.dac.com/content/40th-dac

**Common Conference Name Abbreviations:**

| Full Word | Abbreviation | Full Word | Abbreviation |
|-----------|-------------|-----------|-------------|
| Annals | Ann. | Proceedings | Proc. |
| Annual | Annu. | Record | Rec. |
| Colloquium | Colloq. | Symposium | Symp. |
| Conference | Conf. | Technical Digest | Tech. Dig. |
| Congress | Congr. | Technical Paper | Tech. Paper |
| Convention | Conv. | Workshop | Workshop |
| Digest | Dig. | First | 1st |
| Exposition | Expo. | Second | 2nd |
| International | Int. | Third | 3rd |
| Meeting | Meeting | Fourth/nth | 4th/nth |
| National | Nat. | | |

**Notes:**
- Use "presented at the" for unpublished conference papers (no page numbers); use "in" for published proceedings.
- All published conference/proceedings papers must have page numbers.
- Conference names use standard abbreviations: Proc., Conf., Symp., Int., Annu., etc. Omit articles/prepositions like "of the" and "on."
- Ordinal numbers in conference names use numerical form (1st, 2nd, 3rd, 4th).
- For U.S. locations, "USA" must be included after city and state abbreviation.
- If the year appears in the conference title, it may be omitted from the end of the reference.
- For online conference papers (not in proceedings), use sentence-style format: `A. B. Author. (Date). Title. Presented at Conf. [Online]. Available: URL`
- For online proceedings, append `[Online]. Available: URL` to the standard format.

---

## Periodicals (M)

**Basic Format:**
`[#] A. B. Author, "Name of paper," Abbrev. Title of Periodical, vol. x, no. x, pp. xxx-xxx, Abbrev. Month, year.`

**Subtypes:**
- Basic periodical (with pages)
- Periodical with Article ID (no page range)
- Periodical with DOI
- Periodical in early access
- Periodical in other language
- Periodicals online
- Virtual journal
- To be published
- Submitted for publication

**Required Fields:** author, title, periodical_title, volume, year
**Optional Fields:** issue_number, pages, article_id, doi, month, language, accessed_date, url, early_access_flag

**Examples:**

[1] M. Ito et al., "Can the application of amorphous oxide TFT be an electrophoretic display?," J. Non-Cryst. Solids, vol. 354, no. 19, pp. 2777-2782, Feb. 2008.

[2] J. Zhang and N. Tansu, "Optical gain and laser characteristics of InGaN quantum wells on ternary InGaN substrates," IEEE Photon. J., vol. 5, no. 2, Apr. 2013, Art no. 2600111.

[3] F. Vatta, A. Soranzo, and F. Babich, "More accurate analysis of sum-product decoding of LDPC codes using a Gaussian approximation," IEEE Commun. Lett., early access, Dec. 11, 2018, doi: 10.1109/LCOMM.2018.2886261.

**Notes:**
- Periodical titles of only one word are not abbreviated (e.g., Science, Nature).
- Prior to 1988, IEEE Transactions volume numbers carried the journal acronym (e.g., vol. AC-26). The only exception is Proceedings of the IEEE, which never carried an acronym.
- When both issue number and month are available for IEEE Transactions, include both.
- Article ID replaces page numbers when there is no page range. Be aware that an article ID may erroneously appear as a page number in source files -- query the author if the page number looks wrong (single long number, non-sequential range, or vol. with pp. 1-XX).
- For DOI references, append `doi: 10.xxxx/xxxxx` after the year.
- Early access: always state "early access", include the online version date, and include the DOI. The DOI is essential as it will not change. Once an article is in early access at the publisher, cite that version, not the arXiv version.
- "To be published" -- use when the paper has been accepted or scheduled but not yet published as early access. Never use "to appear in." Example: `E. H. Miller, "A note on reflector arrays," IEEE Trans. Antennas Propag., to be published.`
- "Submitted for publication" -- use when the paper has not yet been accepted. Example: `C. K. Kim, "Effect of gamma rays on plasma," submitted for publication.`
- For other-language periodicals, add `(in Language)` after the title.
- For translated references, append translation info in parentheses: `(Transl.: translator, organization, Rep. number, date)`.
- For online periodicals, append `[Online]. Available: URL` and optionally `Accessed: Month Day, Year`.
- Virtual journals use editor names, issue title, and journal title: `Ed(s)., "Title of Issue," in Title of Journal, month year. [Online]. Available: URL`
- A special issue with no author uses the issue title as the title element.

---

## Theses and Dissertations (Q)

**Basic Format:**
`[#] A. B. Author, "Title of thesis," M.S. thesis, Abbrev. Dept., Abbrev. Univ., City of Univ., Abbrev. State, Country, year.`
`[#] A. B. Author, "Title of dissertation," Ph.D. dissertation, Abbrev. Dept., Abbrev. Univ., City of Univ., Abbrev. State, Country, year.`

**Subtypes:**
- M.S. thesis (print)
- Ph.D. dissertation (print)
- Ph.D. thesis (print)
- M.S. thesis (online)
- Ph.D. dissertation (online)
- Ph.D. thesis (online)

**Required Fields:** author, title, degree_type (M.S. thesis / Ph.D. dissertation / Ph.D. thesis), department, university, city, year
**Optional Fields:** state, country, report_number, url

**Examples:**

[1] J. O. Williams, "Narrow-band analyzer," Ph.D. dissertation, Dept. Elect. Eng., Harvard Univ., Cambridge, MA, USA, 1993.

[2] N. Kawasaki, "Parametric study of thermal and chemical nonequilibrium nozzle flow," M.S. thesis, Dept. Electron. Eng., Osaka Univ., Osaka, Japan, 1993.

**Notes:**
- The state abbreviation is omitted if the university name includes the state name (e.g., "Univ. California, Berkeley" -- no state abbreviation needed).
- Defer to the author's use of "thesis" vs "dissertation" -- these differ by degree and institution and should not be changed based on degree level.
- For online theses, append `[Online]. Available: URL` to the standard format.

---

## Reports (N)

**Basic Format:**
`[#] A. B. Author, "Title of report," Abbrev. Name of Co., City of Co., Abbrev. State, Country, Rep. xxx, year.`

**Subtypes:**
- Technical report (print)
- Technical memorandum (print)
- Scientific report (print)
- Report online

**Required Fields:** author, title, institution_name, institution_city, report_designation, year
**Optional Fields:** state, country, volume, url, accessed_date, report_type (Tech. Rep., Tech. Memo., Sci. Rep., White Paper)

**Examples:**

[1] E. E. Reber, R. L. Michell, and C. J. Carter, "Oxygen absorption in the Earth's atmosphere," Aerospace Corp., Los Angeles, CA, USA, Tech. Rep. TR-0200 (4230-46)-3, Nov. 1988.

[2] J. H. Davis and J. R. Cogdell, "Calibration program for the 16-foot antenna," Elect. Eng. Res. Lab., Univ. Texas, Austin, Tech. Memo. NGL-006-69-3, Nov. 15, 1987.

[3] R. J. Hijmans and J. van Etten, "Raster: Geographic analysis and modeling with raster data," R Package Version 2.0-12, Jan. 12, 2012. [Online]. Available: http://CRAN.R-project.org/package=raster

**Notes:**
- The institution name and location follow the title, before the report number and date.
- Report number formatting varies: Tech. Rep., Tech. Memo., Sci. Rep., Rep., Contract number, etc. Use whatever designation the source provides.
- For reports within a larger document, use `in "Parent Title"` before the institution.
- For online reports, add `[Online]. Available: URL` and optionally `Accessed: Month Day, Year` to the end.
- Include volume information when applicable (e.g., `vol. 2` at the end).

---

## Lectures (G)

**Basic Format:**
`[#] A. B. Author. (Year). Title of lecture [Type of Medium]. Available: URL`

**Subtypes:**
- Lecture notes (online)
- Lecture online (from a university)

**Required Fields:** author_or_institution, title, year
**Optional Fields:** medium_type (PowerPoint slides, Online, etc.), url

**Examples:**

[1] J. Barney. (2011). Documenting literature [PowerPoint slides]. Available: http://moodle.cotr/english/gill

[2] Argosy University Online. (2012). Information literacy and communication: Module 2 filing and organization. [Online]. Available: http://www.myeclassonline.com

**Notes:**
- Lectures use sentence-style formatting (periods between elements) rather than comma-separated format.
- The medium type is placed in square brackets after the title: [PowerPoint slides], [Online], [PDF], etc.
- For university-sourced lectures, the institution name replaces the author field.
- The year is placed in parentheses after the author/institution name.

---

## Courses (D)

**Basic Format (online course):**
`[#] Name of University. (Year). Title of course. [Online]. Available: URL`

**Basic Format (coursepack):**
`[#] A. B. Instructor. Title of coursepack. (Semester). Title of course. University/Publisher location: University/Publisher name.`

**Subtypes:**
- Online course
- Coursepack

**Required Fields (online course):** institution_name, title, year, url
**Optional Fields (online course):** medium_type

**Required Fields (coursepack):** instructor, coursepack_title, semester, course_title, location, publisher
**Optional Fields (coursepack):** (none specified)

**Examples:**

[1] Argosy University Online. (2012). Information literacy and communication. [Online]. Available: http://www.myeclassonline.com

[2] Q. Oden. Mud and Bones-Geology Coursepack. (2014, Winter). GEOG 042. Cranbrook, Canada: College of the Rockies

**Notes:**
- Online courses use sentence-style formatting with the institution as author.
- Coursepacks include the semester in parentheses (e.g., "(2014, Winter)") and end with the publisher location and name separated by a colon.
- The course title in a coursepack may be a course code (e.g., GEOG 042).

---

## Unpublished (S)

**Basic Format (private communication):**
`[#] A. B. Author, private communication, Abbrev. Month, year.`

**Basic Format (unpublished paper):**
`[#] A. B. Author, "Title of paper," unpublished.`

**Basic Format (arXiv preprint):**
`[#] A. B. Author, "Title of paper," year, arXiv:number.`

**Subtypes:**
- Private communication
- Unpublished manuscript
- Repository paper (computer group repository, etc.)
- arXiv preprint

**Required Fields (private communication):** author, month, year
**Optional Fields (private communication):** (none)

**Required Fields (unpublished paper):** author, title
**Optional Fields (unpublished paper):** (none)

**Required Fields (arXiv preprint):** author, title, year, arxiv_id
**Optional Fields (arXiv preprint):** (none)

**Examples:**

[1] A. Harrison, private communication, May 1995.

[2] B. Smith, "An approach to graphs of linear forms," unpublished.

[3] S. Urazhdin, N. O. Birge, W. P. Pratt Jr., and J. Bass, "Current-driven magnetic excitations in permalloy-based multilayer nanopillars," 2003, arXiv:0303149.

**Notes:**
- Private communications have no title -- use the phrase "private communication" directly.
- Unpublished papers use "unpublished" (no quotes in the reference) as the final element. This is distinct from "submitted for publication" (which belongs under Periodicals, category M).
- Distinguish between "to be published" (accepted, use in Periodicals), "submitted for publication" (under review, use in Periodicals), and "unpublished" (no submission, use here).
- arXiv preprints use the format `arXiv:number` (e.g., arXiv:0303149) as the final element. Once an article is in early access at a publisher, cite the publisher version instead of the arXiv version.
