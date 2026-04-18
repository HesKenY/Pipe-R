---
name: Clean Money Corporation (CMC)
description: S-corp owned by Ken Deibel + Sean Bedard that sells ACE (CHERP rebrand) to construction companies. Repo HesKenY/CMC, Netlify-hosted.
type: project
originSessionId: 3bf2fe6f-d592-495f-b593-e98003f3c998
---
**What**: Clean Money Corporation (CMC) is a US-registered S-corporation
owned by Ken Deibel and Sean Bedard. It's the commercial front for
selling **ACE** — a rebrand / resale packaging of CHERP — to other
construction companies.

**Domain**: cleanmoneycorporation.com (Netlify-hosted)

**Repo**: `HesKenY/CMC` (public, created 2026-04-13) — marketing site.
Branch: `main`. Netlify auto-deploys from main.

**Owners / emails**:
- Ken Deibel — product & engineering — `kdeibel@cleanmoneycorporation.com`
- Sean Bedard — field ops & sales — `sbedard@cleanmoneycorporation.com`

**Site structure**:
- `/` wedge landing (thin-edge offer, 3 promises)
- `/ace` product page (9-feature grid, 3-tier pricing: Wedge $149, ACE $399, Enterprise custom)
- `/about` team + origin story + 4 values
- `/contact` Netlify form → Sean's email (dashboard setup required once)
- `/thanks` post-submit confirmation

**Design**: Clean professional (NOT CHERP's sci-fi dark). Teal accent
(`--accent: #0ea5a4`), deep navy ink, Inter font, mobile-first.
Brand pack at `C:/Users/Ken/Desktop/CMC Builkd DOc/Logo/` (note the
typo in the folder name — it's "Builkd DOc" not "Build Doc").

**Marketing strategy**: two-page funnel. Wedge landing is the thin-edge
offer to get customers in the door ($149 entry tier). ACE page is the
full-depth pitch. The sibling plan around CHERP's ownership migration
(offline-first + employee_id + Nest backend adapter) feeds directly
into what CMC can sell.

**Pilot customers**: JSBackyard and REVV are queued as the first two
Nest-backed ACE deployments — see `project_pilot_customers.md`.

**Why: How to apply:**
- Why: CMC is the commercial layer above CHERP. CHERP is the product;
  CMC is the company that sells it. Don't confuse the two repos or
  conflate the design languages (CHERP is sci-fi dark, CMC is clean
  corporate).
- How to apply: When Ken asks about "the website", default to the CMC
  marketing site. When he asks about "the app" or "cherp.live", default
  to CHERP. ACE refers to the product branding that CMC uses to sell
  CHERP externally.

**One-time Netlify setup remaining**:
1. Connect `HesKenY/CMC` in Netlify dashboard
2. Set custom domain `cleanmoneycorporation.com`
3. Configure Forms → New submission notification → email to
   `sbedard@cleanmoneycorporation.com`
