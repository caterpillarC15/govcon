"""build_pdf.py — Generate fixtures/reject/attachments/RFP-003.pdf.

Run:   uv run python fixtures/reject/build_pdf.py
Idempotent: overwrites the existing file on each run.
Requires:  reportlab (listed in pyproject.toml dev deps)
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent / "attachments" / "RFP-003.pdf"

# ── Document metadata ────────────────────────────────────────────────────────
SOLICITATION_NUMBER = "DOD-CNDO-2026-044"
TITLE = "Classified Network Defense Operations Support"
AGENCY = "Department of Defense"
OFFICE = "Defense Information Systems Agency (DISA) — Cyber Directorate"
NAICS = "541512 — Computer Systems Design Services"
SET_ASIDE = "8(a) Set-Aside"
DUE_DATE = "August 1, 2026, 2:00 PM Eastern Time"
PERIOD_OF_PERFORMANCE = "12-month base period + two (2) one-year option periods"
CLASSIFICATION = "UNCLASSIFIED // FOR OFFICIAL USE ONLY (FOUO)"


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
        sp(0.3),
        p(CLASSIFICATION, normal),
        sp(0.3),
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
            "<b>Place of Performance:</b> Fort Meade, MD — Sensitive Compartmented "
            "Information Facility (SCIF). All work under this contract is performed "
            "at a designated government SCIF. No remote or telework arrangements are permitted.",
            normal,
        ),
        sp(0.4),
        p(
            "This procurement is a <b>8(a) Set-Aside</b> reserved exclusively for "
            "SBA-certified 8(a) Business Development Program participants. Only firms "
            "holding current, active SBA 8(a) certification at the time of proposal "
            "submission are eligible to compete for this award.",
            normal,
        ),
        sp(0.2),
        p(
            "All offerors and all personnel proposed to perform under this contract must "
            "hold active Top Secret security clearances with Sensitive Compartmented "
            "Information (SCI) eligibility at the time of proposal submission. "
            "Clearance sponsorship is NOT available under this contract. "
            "The Government will not grant interim clearances for purposes of performance.",
            normal,
        ),
        sp(0.2),
        p(
            "Proposals must be submitted via SIPRNet secure email to the designated "
            "Contracting Officer. Unclassified submissions via SAM.gov will not be accepted. "
            "Access to proposal submission instructions requires an active TS/SCI clearance.",
            normal,
        ),
        PageBreak(),
    ]

    # ── PAGE 2: Section C — Statement of Work ───────────────────────────────
    story += [
        p("SECTION C — STATEMENT OF WORK", h1),
        sp(0.2),
        p("C.1 Background and Mission Context", h2),
        p(
            "The Department of Defense (DOD) operates a global classified network "
            "infrastructure supporting warfighting, intelligence, and command-and-control "
            "functions. Classified DOD enclaves — including SECRET and TOP SECRET//SCI "
            "networks — face continuous, sophisticated threats from nation-state adversaries "
            "and Advanced Persistent Threat (APT) actors. The mission of this contract is "
            "to provide continuous, expert-level network defense operations across DOD "
            "classified enclave infrastructure at Fort Meade, MD.",
            normal,
        ),
        sp(0.15),
        p(
            "The contractor will embed cleared personnel within a SCIF environment, "
            "operating alongside DOD Cyber Mission Forces (CMF), the DOD Cyber Crime "
            "Center (DC3), and US Cyber Command (US-CYBERCOM). All work is performed "
            "on classified networks. Personnel who cannot obtain and maintain active "
            "Top Secret clearances with SCI eligibility are ineligible to perform any "
            "task under this contract.",
            normal,
        ),
        sp(0.2),
        p("C.2 Continuous Monitoring of Classified DOD Networks", h2),
        p(
            "The contractor shall provide continuous 24/7/365 monitoring of classified "
            "DOD network infrastructure within designated SCIFs at Fort Meade. Monitoring "
            "activities include: (a) real-time analysis of network traffic on SECRET and "
            "TOP SECRET network segments; (b) correlation of intrusion detection system "
            "(IDS) and host-based security system (HBSS) alerts; (c) identification of "
            "anomalous traffic patterns indicative of APT lateral movement; and (d) "
            "continuous dashboard monitoring of classified SIEM feeds. All monitoring "
            "is conducted from within the SCIF using government-furnished classified "
            "workstations. No unclassified connectivity is permitted during operations.",
            normal,
        ),
        sp(0.15),
        p("C.3 Incident Response within SCIFs", h2),
        p(
            "The contractor shall provide Incident Response (IR) services for classified "
            "security incidents affecting DOD enclave networks. IR responsibilities include: "
            "(a) initial triage and classification of suspected breaches or intrusion events "
            "on SECRET and TS/SCI network segments; (b) forensic analysis of classified "
            "endpoints, servers, and network appliances within SCIF boundaries; (c) "
            "containment, eradication, and recovery activities coordinated with the "
            "Government IR lead; (d) preparation of classified incident reports compliant "
            "with CJCSI 6510.01F and DoDD 8530.01; and (e) briefings to senior DOD "
            "leadership within designated SAPs as required. All incident documentation "
            "shall be classified at the appropriate level and stored on government-furnished "
            "classified systems only.",
            normal,
        ),
        sp(0.15),
        p("C.4 Threat Hunting Against APT-Tier Adversaries", h2),
        p(
            "The contractor shall conduct proactive threat hunting operations targeting "
            "APT-tier nation-state adversaries known to target DOD classified networks. "
            "Threat hunting activities shall include: (a) hypothesis-driven hunting "
            "campaigns based on current classified threat intelligence products disseminated "
            "by NSA/CSS, DIA, and US-CYBERCOM J2; (b) analysis of classified MITRE ATT&CK "
            "for ICS and Enterprise threat actor profiles; (c) custom signature development "
            "for classified IDS/IPS platforms; and (d) adversary emulation exercises using "
            "classified red team indicators. Hunting results shall be briefed weekly to "
            "the DOD Contracting Officer's Representative (COR) in a classified setting.",
            normal,
        ),
        sp(0.15),
        p("C.5 Coordination with DOD CIRT and US-CYBERCOM JFHQ-DODIN", h2),
        p(
            "The contractor shall coordinate directly with the DOD Computer Incident "
            "Response Team (CIRT) and the Joint Force Headquarters — Department of Defense "
            "Information Networks (JFHQ-DODIN) under US Cyber Command. Coordination "
            "activities include: (a) daily operations synchronization calls (classified); "
            "(b) submission of cyber incident reports via classified DOD reporting channels "
            "(SIPR/JWICS); (c) participation in classified threat intelligence sharing "
            "sessions with JFHQ-DODIN and allied Cyber Mission Forces; and (d) support "
            "for DOD Inspector General (IG) audits and assessments as directed. "
            "All coordination occurs within classified environments. The contractor's "
            "cleared personnel must be authorized for access to relevant SAPs as required "
            "by the Government Security Officer.",
            normal,
        ),
        PageBreak(),
    ]

    # ── PAGE 3: Section H, L, M — Special Requirements, Instructions, Evaluation
    story += [
        p("SECTION H — SPECIAL CONTRACT REQUIREMENTS", h1),
        sp(0.2),
        p("H.1 Security Clearance Requirements", h2),
        p(
            "<b>H.1.1 Mandatory Clearance Level.</b> All personnel performing under this "
            "contract shall hold an active Top Secret clearance with SCI eligibility "
            "at the time of proposal submission. Clearance sponsorship is NOT available "
            "under this contract. Offerors that cannot demonstrate a cleared workforce "
            "meeting this requirement at the time of proposal submission will be deemed "
            "ineligible for award without further evaluation.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.1.2 Continuous Clearance Maintenance.</b> All contractor personnel must "
            "maintain their Top Secret clearance with SCI eligibility throughout the "
            "period of performance. Any personnel whose clearances are suspended, "
            "revoked, or not renewed must be immediately removed from contract performance "
            "and replaced with equally or more highly cleared personnel within five (5) "
            "business days. The contractor shall notify the Contracting Officer within "
            "24 hours of any clearance action affecting personnel assigned to this contract.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.1.3 Key Personnel Clearance Certification.</b> With the proposal, the "
            "offeror shall submit a signed Personnel Security Certification (PSC) confirming "
            "that all proposed Key Personnel hold current, active TS/SCI clearances. "
            "The PSC shall be signed by the offeror's Facility Security Officer (FSO) "
            "and submitted via SIPRNet. Proposals submitted without a valid PSC will "
            "be rejected as technically unacceptable.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.1.4 SIPRNet Infrastructure Requirement.</b> The contractor must maintain "
            "an active SIPRNet connection at their cleared facility prior to award. "
            "Proposals must include the contractor's SIPRNet IP address for communications. "
            "All proposal submissions, correspondence, and deliverables under this contract "
            "are transmitted via SIPRNet or hand-carried by cleared personnel. No NIPRNet "
            "or unclassified email communication is permitted for official contract matters.",
            normal,
        ),
        sp(0.2),
        p("H.2 SBA 8(a) Set-Aside Requirements", h2),
        p(
            "<b>H.2.1 8(a) Certification Mandatory.</b> This procurement is reserved for "
            "SBA-certified 8(a) Business Development Program participants in good standing. "
            "Offerors must hold current, active SBA 8(a) certification at the time of "
            "proposal submission. Certification must remain active through contract award. "
            "Proposals from firms that are not SBA-certified 8(a) participants will be "
            "rejected without evaluation.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.2.2 8(a) Documentation Required.</b> The offeror shall submit with its "
            "proposal a copy of its current SBA 8(a) certification letter issued by the "
            "Small Business Administration. The letter must be dated within 12 months of "
            "proposal due date. The offeror's SBA case number shall appear in the "
            "certification documentation. Proposals lacking valid 8(a) certification "
            "documentation will be rejected as technically unacceptable.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>H.2.3 Subcontracting Limitations.</b> Consistent with SBA 8(a) program "
            "limitations on subcontracting, the prime contractor shall perform at least "
            "50% of the cost of the contract with its own workforce. Subcontracting "
            "to non-8(a) firms is permitted only for non-primary requirements and must "
            "be approved in advance by the SBA and the Contracting Officer.",
            normal,
        ),
        sp(0.25),
        p("SECTION L — INSTRUCTIONS TO OFFERORS", h1),
        sp(0.2),
        p("L.1 SIPRNet Submission Only", h2),
        p(
            "All proposals must be submitted via SIPRNet secure email to the Contracting "
            "Officer at the SIPRNet address provided in the classified amendment to this "
            "solicitation. Unclassified submissions via SAM.gov, commercial email, or any "
            "other unclassified channel will NOT be accepted and will be rejected without "
            "evaluation. Offerors without SIPRNet access are ineligible to submit proposals "
            "under this solicitation, as SIPRNet access requires an active TS/SCI clearance.",
            normal,
        ),
        sp(0.15),
        p("L.2 Volume Structure", h2),
        p(
            "Proposals shall consist of four volumes submitted via SIPRNet: "
            "Volume I — Technical Approach (classified, page limit: 40 pages); "
            "Volume II — Personnel Security Certification and Key Personnel Resumes "
            "(classified, no page limit); Volume III — 8(a) Certification Documentation "
            "(unclassified, submitted separately via hand delivery to the Contracting "
            "Officer if SIPRNet not available for this volume); "
            "Volume IV — Price/Cost (unclassified, page limit: none).",
            normal,
        ),
        sp(0.15),
        p("L.3 Proposal Validity Period", h2),
        p(
            "Proposals shall remain valid for a minimum of 180 days after the proposal "
            "due date. Proposals with shorter validity periods may be rejected at the "
            "Government's discretion. The Government anticipates award within 120 days "
            "of proposal due date, subject to security clearance verification timelines.",
            normal,
        ),
        sp(0.25),
        p("SECTION M — EVALUATION CRITERIA", h1),
        sp(0.2),
        p("M.1 Evaluation Method — Best Value Tradeoff", h2),
        p(
            "Award will be made using a Best Value Tradeoff source selection. Evaluation "
            "factors, listed in descending order of importance, are: (1) Clearance Posture "
            "(eliminatory gate); (2) Technical Approach; (3) Past Performance with "
            "classified cybersecurity work; (4) Price/Cost. Technical factors, when "
            "combined, are more important than Price.",
            normal,
        ),
        sp(0.15),
        p("M.2 Clearance Posture — Eliminatory Gate", h2),
        p(
            "<b>M.2.1 Gate Criteria.</b> Before any other evaluation factor is considered, "
            "the Government will verify that all proposed Key Personnel hold active "
            "Top Secret clearances with SCI eligibility and that the offeror holds "
            "a valid SBA 8(a) certification. Proposals that fail either gate — "
            "insufficient clearance posture OR absence of valid 8(a) certification — "
            "will be rejected without further evaluation. No exceptions or waivers "
            "are available for these eliminatory requirements.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>M.2.2 Clearance Verification.</b> The Contracting Officer will verify "
            "clearance status through the Joint Personnel Adjudication System (JPAS) "
            "or its successor system. Offerors are responsible for ensuring their "
            "personnel's clearance information is current in JPAS at the time of "
            "proposal submission. Discrepancies between the submitted PSC and JPAS "
            "records will result in proposal rejection.",
            normal,
        ),
        sp(0.15),
        p("M.3 Technical Approach", h2),
        p(
            "Technical Approach will be evaluated on: (a) demonstrated understanding "
            "of classified network defense operations and APT threat landscape; "
            "(b) proposed methodology for continuous monitoring of TS/SCI network "
            "segments; (c) incident response procedures tailored to SCIF environments; "
            "and (d) threat hunting approach leveraging classified intelligence sources. "
            "Proposals will be rated Outstanding, Good, Acceptable, Marginal, or "
            "Unacceptable on Technical Approach.",
            normal,
        ),
        sp(0.15),
        p("M.4 Past Performance with Classified Work", h2),
        p(
            "Past Performance will be evaluated based on the quality and relevance of "
            "prior classified cybersecurity engagements. Relevant experience includes "
            "prior DOD, IC, or other federal classified network defense contracts. "
            "Unclassified past performance may be submitted but carries less weight "
            "than classified engagements. Offerors with no relevant classified past "
            "performance will receive a Neutral rating. Past Performance ratings: "
            "Substantial Confidence, Satisfactory Confidence, Limited Confidence, "
            "No Confidence, or Neutral.",
            normal,
        ),
        sp(0.15),
        p("M.5 Price/Cost", h2),
        p(
            "Price will be evaluated for reasonableness, completeness, and realism. "
            "Offerors must provide fully-burdened labor rates for all proposed cleared "
            "labor categories, reflecting appropriate cleared-workforce compensation "
            "premiums. Price will not be scored; however, a significantly higher price "
            "than the Government cost estimate must be justified by clearly superior "
            "non-price factors to result in award.",
            normal,
        ),
    ]

    doc.build(story)
    size_kb = OUT.stat().st_size // 1024
    print(f"Wrote {OUT}  ({size_kb} KB)")


if __name__ == "__main__":
    build()
