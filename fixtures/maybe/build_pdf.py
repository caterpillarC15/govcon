"""build_pdf.py — Generate fixtures/maybe/attachments/RFP-002.pdf.

Run:   uv run python fixtures/maybe/build_pdf.py
Idempotent: overwrites the existing file on each run.
Requires:  reportlab (listed in pyproject.toml dev deps)
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent / "attachments" / "RFP-002.pdf"

# ── Document metadata ────────────────────────────────────────────────────────
SOLICITATION_NUMBER = "VA-SIEM-2026-118"
TITLE = "Enterprise SIEM Deployment and Managed Detection Services"
AGENCY = "Department of Veterans Affairs"
OFFICE = "Veterans Affairs Technology Acquisition Center (TAC)"
NAICS = "541512 — Computer Systems Design Services"
SET_ASIDE = "Total Small Business Set-Aside"
DUE_DATE = "July 30, 2026, 5:00 PM Eastern Time"
PERIOD_OF_PERFORMANCE = "12-month base period + four (4) one-year option periods"
SUBMISSION_URL = "https://sam.gov/opp/example-maybe"


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        invariant=1,
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    normal = styles["Normal"]
    title_style = styles["Title"]

    def p(text: str, style=normal) -> Paragraph:
        return Paragraph(text, style)

    def sp(n: float = 0.15) -> Spacer:
        return Spacer(1, n * inch)

    story = []

    # ── PAGE 1: Cover Page ────────────────────────────────────────────────────
    story += [
        sp(0.5),
        p("REQUEST FOR PROPOSAL", title_style),
        sp(0.2),
        p(SOLICITATION_NUMBER, title_style),
        sp(0.4),
        p(TITLE, h1),
        sp(0.4),
        p(f"<b>Issuing Agency:</b> {AGENCY}", normal),
        sp(0.1),
        p(f"<b>Contracting Office:</b> {OFFICE}", normal),
        sp(0.1),
        p(f"<b>Solicitation Number:</b> {SOLICITATION_NUMBER}", normal),
        sp(0.1),
        p(f"<b>NAICS Code:</b> {NAICS}", normal),
        sp(0.1),
        p(f"<b>Set-Aside:</b> {SET_ASIDE}", normal),
        sp(0.1),
        p(f"<b>Proposal Due Date:</b> {DUE_DATE}", normal),
        sp(0.1),
        p(f"<b>Period of Performance:</b> {PERIOD_OF_PERFORMANCE}", normal),
        sp(0.1),
        p(
            "<b>Place of Performance:</b> Multiple VA Medical Centers (VAMCs) across the "
            "Continental United States (CONUS). On-site presence is required at contractor-operated "
            "Security Operations Center (SOC) facilities.",
            normal,
        ),
        sp(0.1),
        p(f"<b>SAM.gov Link:</b> {SUBMISSION_URL}", normal),
        sp(0.4),
        p(
            "This is a competitive acquisition set aside exclusively for Small Business concerns "
            "under FAR 19.502-2. No security clearance is required. The Government intends to "
            "award a single Firm-Fixed-Price (FFP) contract for managed cybersecurity services "
            "across the VA enterprise.",
            normal,
        ),
        sp(0.2),
        p(
            "All interested offerors must be registered in the System for Award Management "
            "(SAM.gov) at the time of proposal submission and remain registered through award.",
            normal,
        ),
        PageBreak(),
    ]

    # ── PAGE 2: Section C — Statement of Work ───────────────────────────────
    story += [
        p("SECTION C — STATEMENT OF WORK", h1),
        sp(0.2),
        p("C.1 Background", h2),
        p(
            "The Department of Veterans Affairs (VA) operates one of the largest healthcare "
            "information technology environments in the federal government, spanning more than "
            "170 VA Medical Centers (VAMCs) and hundreds of community-based outpatient clinics "
            "across the Continental United States (CONUS). VA's enterprise cybersecurity posture "
            "requires continuous monitoring, threat detection, and rapid incident response to "
            "protect sensitive Veteran health data and critical clinical systems.",
            normal,
        ),
        sp(0.15),
        p(
            "VA seeks to deploy and operate a unified enterprise Security Information and Event "
            "Management (SIEM) platform capable of ingesting, correlating, and acting upon security "
            "telemetry from all 170+ VAMCs. The contractor will serve as VA's primary managed "
            "detection and response partner, operating a dedicated Security Operations Center (SOC) "
            "on a continuous basis throughout the life of the contract.",
            normal,
        ),
        sp(0.15),
        p("C.2 Enterprise SIEM Deployment", h2),
        p(
            "The contractor shall deploy, configure, and integrate an enterprise SIEM solution "
            "across all VA Medical Centers within the base period. Specific requirements include:",
            normal,
        ),
        sp(0.1),
        p("C.2.1 Platform Deployment", h2),
        p(
            "The contractor shall install and configure SIEM collectors, forwarders, and aggregation "
            "nodes at each VAMC. The SIEM platform must meet FedRAMP Moderate authorization "
            "requirements. All data must remain within CONUS boundaries. The contractor shall "
            "complete deployment at a minimum of 20 VAMCs per month, achieving full deployment "
            "within the first nine (9) months of the base period.",
            normal,
        ),
        sp(0.1),
        p("C.2.2 Continuous Tuning and Content Engineering", h2),
        p(
            "Following initial deployment, the contractor shall perform continuous tuning of SIEM "
            "detection rules, correlation logic, and alert thresholds. Content engineering tasks "
            "include developing custom detection use cases aligned with the MITRE ATT&CK framework, "
            "with particular emphasis on healthcare-sector threat actors and ransomware indicators "
            "of compromise (IOCs). The contractor shall deliver monthly Tuning Status Reports.",
            normal,
        ),
        sp(0.1),
        p("C.2.3 Threat Hunting", h2),
        p(
            "The contractor shall conduct proactive threat hunting operations across the VA SIEM "
            "environment. Threat hunting cadence shall be no less than weekly. The contractor "
            "shall employ hypothesis-driven hunting methodologies aligned with NIST SP 800-61 "
            "and shall deliver a Threat Hunting Report no later than five (5) business days "
            "following each hunting cycle.",
            normal,
        ),
        sp(0.1),
        p("C.2.4 Integration with VA SOC Infrastructure", h2),
        p(
            "The contractor shall integrate the enterprise SIEM with VA's existing SOC "
            "infrastructure, including VA's Security Operations and Response platform, the "
            "VA Cybersecurity Operations Center (CSOC), and ticketing/case management systems. "
            "Integration shall enable bi-directional alert sharing and automated ticket creation "
            "for incidents meeting defined severity thresholds.",
            normal,
        ),
        sp(0.2),
        p("C.3 Managed Detection and Response", h2),
        p(
            "The contractor shall provide Managed Detection and Response (MDR) services in "
            "support of VA enterprise security operations. MDR services shall include: "
            "(a) 24/7 alert triage and investigation; (b) incident escalation per VA-defined "
            "playbooks; (c) containment guidance and coordination with VA SOC personnel; "
            "and (d) post-incident reporting within 72 hours of incident closure.",
            normal,
        ),
        sp(0.2),
        p("C.4 Past Performance Requirements", h2),
        p(
            "<b>C.4.1 Scale Requirements.</b> Offerors shall demonstrate past performance on a "
            "minimum of three (3) federal engagements of similar size, scope, and complexity "
            "within the past five (5) years. For purposes of this requirement, 'similar' is "
            "defined as a federal cybersecurity managed services or SIEM deployment engagement "
            "with a minimum contract value of $5,000,000 per engagement.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>C.4.2 Cumulative Value Threshold.</b> The three (3) qualifying engagements "
            "referenced in C.4.1 must total no less than $25,000,000 in cumulative contract "
            "value. Offerors that cannot demonstrate $25,000,000 in cumulative past performance "
            "across qualifying engagements will be deemed ineligible for award unless proposing "
            "as a prime-subcontractor team where the aggregate demonstrated experience of all "
            "team members meets this threshold.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>C.4.3 Documentation Required.</b> For each qualifying engagement, the offeror "
            "shall provide: (a) contract number and award date; (b) agency/customer name and "
            "contracting officer point of contact with current telephone number and email; "
            "(c) period of performance (start and end dates); (d) final or estimated contract "
            "value; and (e) a narrative of no more than two (2) pages describing scope, number "
            "of endpoints monitored, SIEM platform employed, and SOC staffing levels maintained.",
            normal,
        ),
        PageBreak(),
    ]

    # ── PAGE 3: Section H, L, M — SOC Requirement, Instructions, Evaluation ─
    story += [
        p("SECTION H — SPECIAL CONTRACT REQUIREMENTS", h1),
        sp(0.2),
        p("H.1 24/7/365 SOC Staffing Requirement", h2),
        p(
            "<b>H.1.1 Continuous Operations Mandate.</b> Contractor must maintain a "
            "CONUS-staffed Tier 1/2/3 Security Operations Center (SOC) operating "
            "24 hours per day, 7 days per week, 365 days per year (24/7/365) from the "
            "date of contract award. Operations may not be interrupted for holidays, "
            "inclement weather, or scheduled maintenance windows without prior written "
            "approval from the VA Contracting Officer's Representative (COR).",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.1.2 Tier Staffing Levels.</b> At all times, the contractor SOC shall "
            "maintain minimum staffing of: (a) Tier 1 — Alert Triage Analysts: no fewer "
            "than three (3) analysts on duty at any given time; (b) Tier 2 — Incident "
            "Response Analysts: no fewer than two (2) analysts on duty during primary "
            "business hours (0600-2200 Eastern) and at least one (1) analyst on-call "
            "during off-hours; (c) Tier 3 — Senior Threat Analysts / Architects: at "
            "least one (1) senior analyst reachable within 30 minutes at all times. "
            "Staffing rosters and on-call schedules shall be provided to the COR monthly.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.1.3 CONUS-Only Staffing.</b> All SOC personnel performing work under "
            "this contract must be physically located within the Continental United States. "
            "Offshore or near-shore staffing arrangements are expressly prohibited. The "
            "contractor shall certify CONUS staffing compliance in each monthly status report.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.1.4 Response Time SLAs.</b> The contractor shall meet the following "
            "service level agreements: Priority 1 (Critical) alerts — initial triage within "
            "15 minutes of detection; Priority 2 (High) alerts — initial triage within "
            "60 minutes; Priority 3 (Medium) alerts — initial triage within 4 hours; "
            "Priority 4 (Low) alerts — initial triage within 24 hours. Failure to meet "
            "Priority 1 or Priority 2 SLAs in any given month at a rate exceeding 5% "
            "may result in performance deductions per Section H.2.",
            normal,
        ),
        sp(0.2),
        p("H.2 Performance Incentives and Deductions", h2),
        p(
            "The contract includes a Performance-Based Service Acquisition (PBSA) framework. "
            "Monthly performance against SLAs defined in H.1.4 will be evaluated. Contractors "
            "that consistently meet or exceed SLA targets may be eligible for performance "
            "incentive payments at the Contracting Officer's discretion. Consistent SLA "
            "failures may result in deductions from monthly invoices at a rate of 1% per "
            "percentage point of SLA miss beyond the 5% threshold, up to a maximum deduction "
            "of 10% of the monthly invoice.",
            normal,
        ),
        sp(0.25),
        p("SECTION L — INSTRUCTIONS TO OFFERORS", h1),
        sp(0.2),
        p("L.1 General Instructions", h2),
        p(
            "Proposals shall be submitted electronically via SAM.gov by the date and time "
            "specified on the cover page. Late proposals will not be accepted. Offerors are "
            "responsible for ensuring timely receipt. Proposals submitted by email, fax, or "
            "hard copy will not be accepted.",
            normal,
        ),
        sp(0.15),
        p("L.2 Electronic Submission via SAM.gov", h2),
        p(
            "All proposal volumes shall be uploaded through the SAM.gov opportunity portal at "
            f"{SUBMISSION_URL} no later than {DUE_DATE}. Proposals must be submitted in "
            "PDF format. File size limit: 100 MB per volume. The Government is not responsible "
            "for technical difficulties encountered during upload.",
            normal,
        ),
        sp(0.15),
        p("L.3 Volume Structure", h2),
        p(
            "Proposals shall consist of three volumes: Volume I — Technical Approach (page limit: "
            "50 pages); Volume II — Past Performance (page limit: 30 pages, plus attachments); "
            "Volume III — Price/Cost (no page limit). Each volume shall be uploaded as a separate "
            "PDF. Offerors proposing as a prime-subcontractor team shall include past performance "
            "documentation for all team members in Volume II.",
            normal,
        ),
        sp(0.15),
        p("L.4 Teaming and Subcontracting", h2),
        p(
            "Offerors that do not individually satisfy the past performance requirements of "
            "Section C.4 or the SOC staffing requirements of Section H.1 are encouraged to "
            "propose as part of a prime-subcontractor team. All teaming arrangements must be "
            "documented via a signed Teaming Agreement submitted with Volume I. The prime "
            "contractor bears full contractual responsibility for all work performed by "
            "subcontractors. Subcontractor past performance may be submitted in Volume II "
            "and will be evaluated on the same criteria as prime contractor past performance.",
            normal,
        ),
        sp(0.25),
        p("SECTION M — EVALUATION CRITERIA", h1),
        sp(0.2),
        p("M.1 Evaluation Method", h2),
        p(
            "Award will be made using Lowest Price Technically Acceptable (LPTA) source "
            "selection procedures. The Government will first evaluate all proposals for "
            "technical acceptability and past performance acceptability. Only proposals "
            "found technically acceptable and past-performance acceptable will advance "
            "to price evaluation. Award will be made to the lowest-priced technically "
            "and past-performance acceptable offeror.",
            normal,
        ),
        sp(0.15),
        p("M.2 Technical Acceptability Gate", h2),
        p(
            "A proposal is technically acceptable if it demonstrates: (a) a credible plan "
            "to deploy the SIEM across all 170+ VAMCs within the base period; (b) evidence "
            "of prior SIEM deployment experience at federal scale; and (c) proposed SOC staffing "
            "levels meeting the minimums specified in Section H.1.2. Proposals not meeting "
            "all three criteria will be rated Technically Unacceptable and will not advance.",
            normal,
        ),
        sp(0.15),
        p("M.3 Past Performance Acceptability Gate", h2),
        p(
            "A proposal is past-performance acceptable if the offeror (or the prime-subcontractor "
            "team) demonstrates cumulative past performance of no less than $25,000,000 across "
            "a minimum of three (3) qualifying federal cybersecurity engagements within the past "
            "five (5) years, as specified in Section C.4. Proposals that do not meet the "
            "$25,000,000 cumulative threshold will be rated Past Performance Unacceptable "
            "and will not advance to price evaluation.",
            normal,
        ),
        sp(0.15),
        p("M.4 Price Evaluation", h2),
        p(
            "Price will be evaluated for reasonableness and completeness. Offerors must "
            "provide fully-burdened labor rates for all proposed labor categories, a "
            "SIEM platform licensing cost breakdown, and travel/ODC estimates. "
            "Unbalanced pricing may be cause for proposal rejection. Award will be "
            "made to the lowest total evaluated price (base + all option years) among "
            "technically and past-performance acceptable proposals.",
            normal,
        ),
    ]

    doc.build(story)
    size_kb = OUT.stat().st_size // 1024
    print(f"Wrote {OUT}  ({size_kb} KB)")


if __name__ == "__main__":
    build()
