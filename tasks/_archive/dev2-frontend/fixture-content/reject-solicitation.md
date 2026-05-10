# Source text — reject fixture solicitation (§11.1 demo)

Copy this into a Word/LibreOffice doc and export to PDF. Render to **2 pages**. Synthetic content.

**Critical:** strong capability/NAICS language on page 1; the **clearance blocker on page 2** (so the evidence-snippet → PDF deep-link demonstrates verifiability).

---

```
DEFENSE INFORMATION SYSTEMS AGENCY
Mission Partner Cybersecurity Office

REQUEST FOR PROPOSAL
Solicitation Number:     DISA-26-R-0103
Title:                   Classified Network Cybersecurity Assessment Services
NAICS Code:              541512 — Computer Systems Design Services
Set-Aside:               Total Small Business Set-Aside
Place of Performance:    Fort Meade, MD (on-site work required for classified
                         systems; remote work prohibited)
Period of Performance:   Base year + two option years
Proposal Due Date:       July 1, 2026, 3:00 PM Eastern


SECTION B — SCOPE OF WORK

The contractor shall provide cybersecurity assessment services for DISA
classified network enclaves, including:

  - Vulnerability scanning of classified networks
  - Penetration testing across SECRET-level systems
  - Configuration review against DISA STIGs
  - Threat modeling and red-team operations
  - Remediation guidance and verification testing

This procurement is for unclassified-output deliverables based on
classified-system assessment. All on-site activity is performed in
accredited classified spaces.


SECTION L — INSTRUCTIONS TO OFFERORS

L.1  Format
     Volume I: Technical Approach (30 pages)
     Volume II: Past Performance (10 pages)
     Volume III: Pricing
     Volume IV: Required Documents and Personnel Security

L.2  Submission
     Proposals shall be submitted electronically through the DoD
     procurement portal.

L.3  Technical Approach
     Offerors shall describe methodology, tools, team composition,
     and prior experience performing assessments against classified
     networks operating under DISA STIGs.


SECTION M — EVALUATION FACTORS

  Factor 1 — Technical Approach              40% weight
  Factor 2 — Past Performance                25% weight
  Factor 3 — Price                           20% weight
  Factor 4 — Personnel Security              15% weight  (PASS/FAIL)

  Note: Factor 4 is a pass/fail eligibility gate. Offerors not meeting
  the personnel security requirements (see L.4) will be eliminated
  from consideration.
```

(end of page 1 — page 2 begins)

```
SECTION L.4 — PERSONNEL SECURITY (MANDATORY ELIGIBILITY)

L.4.1  Clearance Requirement

       ALL PROPOSED KEY PERSONNEL — including but not limited to the
       Program Manager, Lead Security Engineer, Lead Penetration
       Tester, and any individual performing on-site work in the
       classified enclave — SHALL HOLD AN ACTIVE U.S. GOVERNMENT
       SECRET CLEARANCE OR HIGHER prior to contract award.

       Personnel without an active Secret clearance at the time of
       award are not eligible to perform under this contract.
       Interim clearances are not acceptable.

L.4.2  Facility Clearance

       Offerors shall hold or be eligible to hold a facility clearance
       at the SECRET level or higher under the National Industrial
       Security Program (NISP).

L.4.3  Citizenship

       All performing personnel shall be U.S. citizens.


SECTION H — SPECIAL PROVISIONS

H.1  Small Business Set-Aside
     Set aside 100% for small business concerns under NAICS 541512.

H.2  Insurance
     Commercial general liability insurance, $2M aggregate.

H.3  Sensitive Information
     This solicitation does not contain classified information.
     The performance environment is classified at the SECRET level;
     all reports submitted to the Government shall be unclassified.


SECTION I — CONTRACT CLAUSES

Standard DoD FAR clauses apply. DFARS clauses for classified
operations apply during performance only.


END OF SOLICITATION
```

---

## Authoring notes

- **Page 1 must include strong language for capability and NAICS.** This is what makes the §11.1 demo work — capability scores high, but the page-2 blocker forces reject regardless. Specifically: "Vulnerability scanning... Penetration testing... Configuration review against DISA STIGs..." → A5 extracts these as `technical` requirements with high confidence; A6 scores capability ≥ 15/20 since profile capabilities match.
- **Page 2 carries the blocker.** The clearance requirement is in unambiguous, all-caps language: "SHALL HOLD AN ACTIVE U.S. GOVERNMENT SECRET CLEARANCE." This phrasing extracts clean from any LLM and unambiguously matches A6's eligibility short-circuit pattern.
- The "interim clearances are not acceptable" note prevents the LLM from softening the requirement.
- Citizenship requirement (L.4.3) is a secondary eligibility gate — even if clearance were resolved, the LLM should still see this as a `security` requirement.
- Place of performance is on-site at Fort Meade — a regional gap but secondary to the clearance blocker.
- Tuned so capability scores 15-20/20, NAICS 10/10, but eligibility 0/15 → total ~50, decision = reject (with hard short-circuit).
- Practice the demo click: from the timeline, click reject card → click clearance evidence → PDF opens at page 2 → cite verbatim.
