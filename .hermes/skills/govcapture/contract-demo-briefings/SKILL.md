---
name: contract-demo-briefings
description: "Turn live SAM.gov notices into demo-ready 60-90 second contract briefings for Samrail/GovCapture landing pages, videos, and outreach."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [govcapture, samrail, sam-gov, demos, voice, landing-page]
    related_skills: [govcapture-proof-first-voice, govcapture-infrastructure]
---

# Contract Demo Briefings

Use this when building Samrail/GovCapture demos, landing-page samples, video scripts, or outreach snippets from real government contract notices.

## Core direction

The demo is not an avatar-chat UI.

The demo is Michaela reading real, current government contracts and explaining what matters like a useful note someone would get by email or in a short voice memo.

Show the work:

```text
I found this.
I read it.
Here is what matters.
Here is who should care.
Here is whether I would chase it.
```

Do not lead with abstract AI/product mechanics.

## Workflow

1. Pull current SAM.gov opportunities.
   - Prefer live notices posted in the last 7-14 days.
   - Prefer solicitations with attachments or rich notice descriptions.
   - Required proof fields: title, buyer/agency, posted date, response deadline, notice type, set-aside, NAICS/PSC, solicitation number, source link, attachment count.

2. Read the notice description.
   - Use SAM noticedesc when available.
   - Pull attachment names/counts; parse PDFs when needed for requirements, Section L/M, SOW/PWS, Q&A, wage determinations, or amendments.

3. Select demo candidates.
   - Good demo samples have a clear story: deadline pressure, unusual requirement, obvious fit filter, or understandable scope.
   - Avoid samples where the only honest output is generic.

4. Write a 60-90 second briefing.
   - No hard cutoff; make it as long as the contract needs.
   - Start with a verdict, caution, or simple orientation.
   - Mention who should care and who should skip.
   - Include one next action.
   - Keep it conversational and proof-backed.

5. Package for UI/video.
   - Landing card: title, buyer, deadline, set-aside, NAICS/PSC, one-line reason it matters, play CTA.
   - Voice/video script: spoken briefing.
   - Optional email version: same content, slightly tighter.

## Script pattern

```text
I would slow down before chasing this one.

This is [buyer] looking for [work]. The response is due [date].

The important part is [requirement/risk/scope].

If you already [fit condition], this is worth reviewing. If not, I would skip it and look for a cleaner fit.
```

Alternative opening when the opportunity is clean:

```text
This one is straightforward.

[Buyer] needs [work], and the deadline is [date]. The fit question is simple: [fit filter].
```

## Landing page section pattern

```text
Latest contracts Michaela can explain

[Contract title]
Buyer: [agency]
Deadline: [date]
Set-aside: [type]
Why it matters: [one plain-language line]
▶ Play briefing
```

## Pitfalls

- Do not fabricate proof. If attachments have not been read, say only that attachments exist.
- Do not make the page about talking to a mascot/avatar. Make it about contracts being read and explained.
- Do not describe the pipeline before showing the result.
- Do not use stale opportunities for a “latest” demo unless clearly marked as sample data.
- Do not over-compress complex contracts; if the useful explanation needs 100 seconds, let it breathe.

## References

- `references/samrail-contract-demo-explainers.md` — session-specific examples and real SAM.gov sample notices used to shape the demo format.
