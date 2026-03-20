# Technical Approach & Architecture

## Problem Statement

Electoral Commission of India (ECI) affidavits (Form 26) are submitted as PDF 
documents by election candidates. These documents contain critical information 
including the candidate's PAN number, personal details, and election constituency.

The challenge is that these PDFs are:
- Mixed language (English + Tamil + Hindi on same page)
- Sometimes scanned images rather than digital text
- Contain handwritten entries (especially PAN numbers in older formats)
- Follow slightly different formats across different states and years

The goal is to reliably extract structured data — especially the PAN number — 
from these varied documents and store it in a database.

---

## Extraction Pipeline
```
PDF Input
   │
   ├─── Layer 1: pdfplumber
   │         Extracts embedded digital text directly from PDF
   │         Fast, free, no API needed
   │         Works well for digital PDFs
   │         Fails on scanned PDFs and Tamil, Hindi table structures
   │
   ├─── Layer 2: Tesseract OCR
   │         Converts each PDF page to image
   │         Runs optical character recognition
   │         Handles scanned PDFs that pdfplumber cannot read
   │         Trained on English + Tamil + Hindi character sets
   │         Always runs alongside pdfplumber 
   │         Combined text from both layers fed to field extractor
   │
   ├─── Layer 3: Groq AI Vision (fallback only)
   │         Only triggers if PAN not found after layers 1 and 2
   │         Sends page images to Groq's LLaMA vision model via API
   │         Handles complex layouts and handwritten content
   │         Subject to API rate limits (free tier)
   │
   ▼
Field Extraction (Regex)
   │
   ├─── PAN Number
   ├─── Mobile Number  
   ├─── Email Address
   ├─── Age
   ├─── Address
   ├─── Constituency
   └─── Father's / Spouse's Name
   │
   ▼
PAN Validation + Confidence Scoring
   │
   ▼
MySQL Storage + CSV Export
```

---

## How Each Layer Works

### Layer 1 — pdfplumber

pdfplumber reads the internal structure of a PDF file and extracts text that 
is digitally embedded.
For ECI affidavits, this works well for:
- The e-stamp certificate page (candidate name, certificate number)
- English text sections (notarial certificate, additional affidavit)
- Mobile numbers, email addresses in English sections

It fails for:
- Tamil, Hindi language table rows (the PAN income table)
- Scanned/photographed pages
- Older Bihar state affidavit formats

### Layer 2 — Tesseract OCR

Tesseract is an open-source OCR (Optical Character Recognition) that
works completely offline on the machine 

**How it works:**
1. Each PDF page is rendered as a high-resolution image (150 DPI)
2. Tesseract analyzes the image pixel by pixel
3. It identifies characters using trained language models
4. Returns the recognized text as a string

**Language models used:**
- `eng` — English character recognition
- `tam` — Tamil character recognition  
- `hin` — Hindi (Devanagari) character recognition

Running all three together allows Tesseract to recognize mixed-language content 
on the same page. For example, a page with Tamil body text but English PAN numbers 
in a table — Tesseract can read both.

**Why always run Tesseract?**

pdfplumber reads Tamil text as garbled Latin characters 
(e.g., `6sr Ocoi ooruorflan`) because Tamil Unicode is not properly embedded in 
many scanned PDFs. The garbled text has high character count so it passes length 
checks, but contains no useful information. Running Tesseract alongside pdfplumber 
and combining both outputs ensures the PAN table is read correctly even when 
pdfplumber fails.

### Layer 3 — Groq AI

When Tesseract also fails to find a PAN — typically on 
handwritten Hindi affidavits — the page image is sent to Groq's API.

**How it works:**
1. PDF page rendered as image (same as Tesseract)
2. Image converted to base64 string
3. Sent to Groq API with instruction: "Extract all text from this page"
4. Groq's LLaMA model reads the image and returns text
5. Text passed to field extractor for PAN detection

**When it triggers:**
Only when both pdfplumber and Tesseract find zero valid PANs in combined text. 
For the test dataset, this triggered only for a Bihar Hindi handwritten affidavit.

**Limitation:**
Even Groq cannot guarantee correct character recognition for handwritten PANs. 
The extracted PAN may have 1-2 OCR errors which are flagged in confidence scoring.

---

## Transliteration

Tamil and Hindi text extracted by Tesseract is in Unicode script 
(e.g., `விண்ணப்பதாரர்` or `स्वयं`). Standard Python regex cannot match 
English patterns like PAN format against this text.

**The transliteration step:**
The `indic_transliteration` library converts Tamil/Hindi Unicode to ITRANS 
(a standard romanization scheme):
```
Tamil:   விண்ணப்பதாரர்  →  viNNappathaarar
Hindi:   स्वयं           →  svayaM
```

This is done after Tesseract OCR runs. The transliterated text is then combined 
with pdfplumber text and passed to regex-based field extraction.

**Why this matters for PAN:**
PAN numbers are always written in English even in Tamil/Hindi affidavits. 
Transliteration ensures the surrounding context text doesn't interfere with 
regex matching. Without transliteration, Tamil & Hindi Unicode characters could 
break regex boundary detection.

---

## PAN Extraction Logic

PAN format: `AAAAA9999A` (5 letters, 4 digits, 1 letter)

**Step 1 — Direct regex search:**
```
[A-Z]{5}[0-9]{4}[A-Z]
```
Searches entire combined text for any 10-character string matching PAN format.

**Step 2 — OCR correction (if no direct match):**
Common OCR misreads are corrected:
```
0 → O  (zero looks like letter O)
1 → I  (one looks like letter I)
2 → Z  (two looks like letter Z)
5 → S  (five looks like letter S)
8 → B  (eight looks like letter B)
```
After correction, pattern match is attempted again.

**Step 3 — Candidate PAN selection:**
Multiple PANs may be found (candidate + spouse + dependents).
The candidate's PAN is always row 1 of the income declaration table.
Logic checks for PAN appearing after `1.` row marker or `self` keyword.

**Corrected flag:**
If OCR correction was needed, `pan_corrected = True` is set.
This reduces confidence score and adds a manual verification note.

---

## PAN Confidence Scoring

Confidence is calculated purely from pattern analysis — no external verification:

| Check | Points | Rationale |
|-------|--------|-----------|
| Matches `AAAAA9999A` format | +0.4 | Basic validity |
| 4th char in P/C/H/F/A/T/B | +0.2 | Valid entity type codes |
| First 3 chars are letters | +0.1 | OCR sometimes puts digits here |
| 5th char is a letter | +0.1 | Should always be alphabetic |
| Chars 6-9 are digits | +0.2 | OCR sometimes puts letters here |

**Important limitation:**
A score of 1.0 means the PAN format is perfect — it does not confirm the PAN 
is correct, exists or belongs to the candidate.

---

## Database Design

### Duplicate Prevention
`UNIQUE KEY uq_source_file (source_file)` ensures the same PDF cannot be 
inserted twice. `ON DUPLICATE KEY UPDATE` allows re-processing to update 
existing records rather than failing silently.

### Only insert if PAN found
Records are only inserted to the database if a valid PAN is extracted. 
This prevents storing incomplete records from non-affidavit documents 
like nomination receipts.

---

## Challenges & Solutions

| Challenge | Root Cause | Solution |
|-----------|-----------|----------|
| Tamil table not readable | pdfplumber skips Tamil Unicode tables | Always run Tesseract alongside pdfplumber |
| Spouse PAN extracted instead of candidate | Multiple PANs in document, wrong one picked first | Row 1 detection + self keyword matching |
| Handwritten PANs misread | OCR cannot reliably read handwriting | clean_ocr_pan() correction + confidence flag |
| Hindi nomination receipts have no PAN | Different document type, not Form 26 | Skip with warning, log reason |
| pdfplumber garbled text passes length check | Garbled Tamil looks like long text | Always run Tesseract regardless of text length |
| Groq rate limits on free tier | Too many API calls in short time | Groq only triggers as last resort, sleep between calls |

---

## Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| PDF text extraction | pdfplumber | Best for digital PDFs, table extraction |
| OCR | Tesseract 5.x | Free, offline, multi-language |
| AI fallback | Groq API | Free tier, vision capable |
| Field parsing | Python regex | Fast, reliable for structured forms |
| Transliteration | indic_transliteration | Tamil/Hindi to Latin conversion |
| Database | MySQL 8.0 | Structured data, ACID compliance |
| API | Flask | Lightweight, simple REST endpoints |
| Logging | Python logging | File + console, daily rotation |