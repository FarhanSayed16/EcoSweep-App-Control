# EcoSweep Research Paper — Format Guide

## Files Generated

| File | Description |
|------|-------------|
| **ECOSWEEP-RESEARCH-PAPER-IEEE-v3.docx** | EcoSweep paper (enhanced: 10 figure placeholders, richer content) |
| **ECOSWEEP-RESEARCH-PAPER-IEEE-v2.docx** | Previous version |
| **Conference-template-A4.doc** | Your conference template (original) |
| **paper format ieee.pdf** | IEEE formatting reference |
| **generate_ieee_paper.py** | Script to regenerate the .docx |

## Format Applied (per paper format ieee.pdf and Conference-template-A4.doc)

- **Page size:** A4 (210 × 297 mm)
- **Margins:** Top 19 mm, Bottom 43 mm, Left/Right 14.32 mm
- **Font:** Times New Roman, 10 pt body
- **Title:** 24 pt, centered (style: paper title; no sub-titles)
- **Authors:** 5-line block per author (line 1: name; line 2: dept; line 3: org; line 4: City, Country; line 5: email)
- **Abstract:** "Abstract—" with em dash, italic run-in head; no symbols, special chars, footnotes, or math
- **Keywords:** "Keywords—" with em dash
- **Sections:** I. INTRODUCTION (Heading 1)
- **Subsections:** A. Background (Heading 2)
- **Tables:** TABLE I. style head above table; Table Grid style
- **Figures:** Fig. 1. caption below (placeholders only)
- **References:** [1] format; punctuation follows bracket [2]

## Two-Column Layout

The IEEE template uses a two-column layout for the main body (after Abstract/Keywords). To apply:
- In Word: select body text → Layout → Columns → Two
- Or copy content into `Conference-template-A4.doc` (which already has two-column format)

## Using With Your Conference Template

If `Conference-template-A4.doc` uses a two-column layout or other specific styles:

1. **Option A — Copy into template**
   - Open `Conference-template-A4.doc` in Word
   - Delete the template’s sample content (keep styles/layout)
   - Open `ECOSWEEP-RESEARCH-PAPER-IEEE.docx`
   - Copy all content (Ctrl+A, Ctrl+C) and paste into the template (Ctrl+V)
   - If needed, apply the template’s “Normal” or “Body Text” style to pasted paragraphs

2. **Option B — Use as-is**
   - Open `ECOSWEEP-RESEARCH-PAPER-IEEE.docx`
   - Go to Layout → Columns → Two (if the conference requires two columns)
   - Adjust page setup as required

## Regenerating the Document

After editing `ECOSWEEP-RESEARCH-PAPER.md` or `generate_ieee_paper.py`:

```powershell
cd d:\Robot_newcontrol\docs
python generate_ieee_paper.py
```

This creates `ECOSWEEP-RESEARCH-PAPER-IEEE-v3.docx` (edit the script to change the output filename).

## Placeholders to Replace

- `[Author Names]`, `[College/University Name]`, `[Email]`
- `[TBD]` in Tables IV, V, VI (experimental results, cost)
- Reference entries marked `[To be filled: ...]`
- **Figure placeholders (Fig. 1–10)** — replace with actual images:
  - Fig. 1: System architecture (UML: docs/diagrams/ecosweep-fig1-system-architecture.puml)
  - Fig. 2: Hardware assembly photo
  - Fig. 3: YOLO detection screenshot
  - Fig. 4: State machine (UML: docs/diagrams/ecosweep-fig4-state-machine.puml)
  - Fig. 5: Key components close-up
  - Fig. 6: Data flow (docs/diagrams/ecosweep-data-flow.puml)
  - Fig. 7: Test environment photo
  - Fig. 8: Mobile app screenshots
  - Fig. 9: Results chart
  - Fig. 10: Manhole concept (docs/diagrams/ecosweep-fig7-manhole-concept.puml)
