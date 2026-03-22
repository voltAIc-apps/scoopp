# scoopp — extension spec

This file lives in the `voltAIc-apps/scoopp` repo root alongside `CLAUDE.md`.
It describes the new features to be added to scoopp as part of the booking system project.

Existing scoopp functionality (crawl, status, result, list, health endpoints) is unchanged.
Do not modify existing endpoints or models unless explicitly stated here.

---

## What is being added

Two new capabilities:

1. **Company research pipeline** — given a company name and a person name, scoopp discovers
   the company website, crawls it, searches for the person's LinkedIn profile, and compiles
   a structured enrichment object.

2. **Email dispatch** — after research completes, scoopp can optionally send a formatted
   briefing email to a specified address, using a configured mail provider.

These are exposed as two new endpoints: `POST /research` and `GET /research/{research_id}`.

---

## New endpoint: `POST /research`

Triggers a research job. Returns immediately with a job ID.
All work happens in a background task — the caller does not wait for research to complete.

**Authentication:** `X-API-Key` header required (same key pattern as existing auth — add to
`.env` as `API_KEY` if not already present).

**Request body:**
```json
{
  "company_name":  "Musterfirma GmbH",
  "person_name":   "Max Mustermann",
  "person_email":  "max@musterfirma.de",
  "format":        "brief",
  "mail_to":       "anna@simplify-erp.de",
  "mail_subject":  "New booking: Max Mustermann (Musterfirma GmbH) · Tue 25 Mar 14:00",
  "mail_context": {
    "consultant_name": "Anna Becker",
    "meeting_date":    "Tuesday, 25 March 2026",
    "meeting_time":    "14:00–14:30 CET",
    "topic":           "ERP rollout",
    "meet_link":       "https://meet.google.com/abc-defg-hij"
  },
  "context": {
    "page_url":     "https://simplify-erp.de/pricing",
    "utm_source":   "google",
    "utm_campaign": "erp-q1",
    "custom": {
      "product": "ERP Cloud",
      "plan":    "Enterprise"
    }
  }
}
```

All fields except `company_name` and `person_name` are optional.
If `mail_to` is absent: research runs and result is stored, but no email is sent.
If `context` is absent: research runs normally; context section is omitted from the email.

**Response (immediate, before research starts):**
```json
{
  "research_id": "uuid",
  "status":      "queued"
}
```

**`format` field:**
- `"brief"` (default) — homepage crawl only, 3–5 sentence summary. Used by the booking flow.
- `"detailed"` — full site crawl up to depth 2. For future use; not triggered by the booking
  widget in MVP.

---

## New endpoint: `GET /research/{research_id}`

Returns the status and result of a research job.

**Authentication:** `X-API-Key` header required.

**Response:**
```json
{
  "research_id": "uuid",
  "status":      "queued | running | done | failed",
  "result": {
    "company": {
      "name":        "Musterfirma GmbH",
      "website":     "https://musterfirma.de",
      "description": "Musterfirma GmbH is a mid-sized manufacturer...",
      "industry":    "Manufacturing",
      "size":        "50–200 employees",
      "recent_news": "Musterfirma announced a new product line in January 2026."
    },
    "person": {
      "name":         "Max Mustermann",
      "linkedin_url": "https://linkedin.com/in/max-mustermann-abc123"
    },
    "format": "brief"
  }
}
```

`result` is `null` while `status` is `queued` or `running`.
`result` is populated when `status` is `done`.
`result` may be partially populated if some steps failed — see error handling below.

---

## Research pipeline (background task)

Implemented with FastAPI `BackgroundTasks`, consistent with the existing crawl pattern.
The pipeline runs the following steps in sequence after `POST /research` returns.

### Step 1 — Discover company URL

Search for `"{company_name}"` using Brave Search API.
Extract the company's own website URL from the results.
Criteria: prefer the first result that is not LinkedIn, Xing, Crunchbase, or a directory site.
If no confident URL is found: set `company.website = null`, skip step 2, continue to step 3.

Config: `BRAVE_API_KEY` in `.env`.

### Step 2 — Crawl company website

Use existing crawl4AI infrastructure (same code path as the existing `/crawl` endpoint).

For `brief`: `crawl_depth=0`, timeout 8 seconds. Crawl homepage only.
For `detailed`: `crawl_depth=2`, timeout 30 seconds.

From the crawled Markdown, extract:
- `description`: 3–5 sentences summarising what the company does.
- `industry`: sector if identifiable from the content.
- `size`: employee count or range if mentioned.
- `recent_news`: one or two sentences about the most recent news item found, if any.

If crawl times out or fails: set crawl fields to `null`, continue to step 3.

### Step 3 — LinkedIn profile lookup

Search: `"{person_name}" "{person_email domain}" site:linkedin.com/in`
where `{person_email domain}` is the domain part of `person_email` (e.g. `musterfirma.de`).

Take the first result URL that matches the pattern `linkedin.com/in/{slug}`.
Do NOT fetch or scrape the LinkedIn page. The URL is the output.

Confidence check: the result URL must contain `linkedin.com/in/` and the slug must not be
a generic word (e.g. `linkedin.com/in/jobs` is not a person profile). If the check fails:
set `person.linkedin_url = null`. Never include a guessed URL.

### Step 4 — Compile result and update job status

Write the completed research object to SQLite (extend the existing jobs table or add a new
`research_jobs` table — follow whichever pattern is already established in `db.py`).
Update job status to `done`.

### Step 5 — Send briefing email (if `mail_to` is present)

Send to `mail_to` using the configured mail provider.

**Subject:** `mail_subject` from the request verbatim.

**Body (HTML + plain text fallback):**

```
Hi {mail_context.consultant_name},

You have a new 30-minute intro call booked.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEETING DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When:        {mail_context.meeting_date} · {mail_context.meeting_time}
With:        {person.name} · {person_email}
Company:     {company.name}
Topic:       {mail_context.topic}
Google Meet: {mail_context.meet_link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABOUT {company.name | UPPERCASE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[include each field only if not null]

{company.description}

Website:     {company.website}
Industry:    {company.industry}
Size:        {company.size}
Recent news: {company.recent_news}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABOUT {person.name | UPPERCASE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LinkedIn: {person.linkedin_url}
[if null: "LinkedIn profile not found automatically."]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW THEY FOUND YOU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[include this section only if context is present and non-empty]

Page:      {context.page_title} — {context.page_url}
Source:    {context.utm_source} / {context.utm_medium} / {context.utm_campaign}
[any context.custom fields as key: value pairs]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Google Calendar invite has been sent to your calendar.
All other attendees have also been invited directly.

– Booking system
```

---

## New file layout

```
app/
  routers/
    crawl.py        # existing — unchanged
    research.py     # NEW — POST /research, GET /research/{id}
  services/
    researcher.py   # NEW — pipeline steps 1–4
    mailer.py       # NEW — email dispatch
  models/
    research.py     # NEW — Pydantic request/response models
```

---

## `.env` additions

```
BRAVE_API_KEY=...
MAIL_PROVIDER=sendgrid        # sendgrid | brevo | ses
MAIL_API_KEY=...
MAIL_FROM=sales@simplify-erp.de
API_KEY=...                   # inbound auth — add if not already present
```

---

## Error handling

- Brave Search unavailable → set `company.website = null`, skip crawl. Continue pipeline.
- Crawl timeout or failure → set crawl-derived fields to `null`. Continue pipeline.
- LinkedIn search returns no confident match → set `linkedin_url = null`. Never guess.
- Email send fails → log the error. Set job status to `done` regardless (research itself
  succeeded). Do not retry in MVP.
- If all steps fail → set job status to `failed`. Log each step's error individually.
- Never let a single step failure abort the entire pipeline. Each step is independently
  try/caught.

---

## Roadmap (out of scope for MVP)

- Retry logic for failed email sends
- `detailed` format triggered from external callers
- Webhook callback URL — instead of polling `GET /research/{id}`, caller provides a URL
  that scoopp POSTs the result to when done
- Multiple search provider support (SerpAPI as fallback to Brave)
- Result caching — if the same company was researched in the last 24h, return cached result
  without re-crawling
