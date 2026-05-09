"""build_pdf.py — Generate fixtures/strong-pursue/attachments/RFP-001.pdf.

Run:   uv run python fixtures/strong-pursue/build_pdf.py
Idempotent: overwrites the existing file on each run.
Requires:  reportlab (listed in pyproject.toml dev deps)
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent / "attachments" / "RFP-001.pdf"

# ── Document metadata ────────────────────────────────────────────────────────
SOLICITATION_NUMBER = "DOI-CMS-2026-001"
TITLE = "Cloud Migration Support Services for the Office of the Chief Information Officer"
AGENCY = "Department of the Interior"
OFFICE = "Office of the Chief Information Officer (OCIO)"
NAICS = "541512 — Computer Systems Design Services"
SET_ASIDE = "Total Small Business Set-Aside"
DUE_DATE = "June 15, 2026, 5:00 PM Eastern Time"
PERIOD_OF_PERFORMANCE = "12-month base period + two (2) one-year option periods"
SUBMISSION_URL = "https://sam.gov/opp/example-strong-pursue"


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
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
        p("<b>Place of Performance:</b> Washington, DC (remote work acceptable for most tasks)", normal),
        sp(0.1),
        p(f"<b>SAM.gov Link:</b> {SUBMISSION_URL}", normal),
        sp(0.4),
        p(
            "This is a competitive acquisition set aside exclusively for Small Business concerns "
            "under FAR 19.502-2. No security clearance is required. The Government intends to "
            "award a single Indefinite-Delivery Indefinite-Quantity (IDIQ) contract.",
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

    # ── PAGE 2: Section C — Technical Requirements ───────────────────────────
    story += [
        p("SECTION C — STATEMENT OF WORK", h1),
        sp(0.2),
        p("C.1 Background", h2),
        p(
            "The Department of the Interior (DOI), Office of the Chief Information Officer (OCIO) "
            "requires cloud migration support services to modernize legacy information systems. "
            "DOI currently operates numerous on-premises systems that require migration to "
            "AWS GovCloud (US) to improve security posture, reduce operational costs, and align "
            "with the Federal Cloud Computing Strategy (Cloud Smart).",
            normal,
        ),
        sp(0.15),
        p("C.2 Scope of Work", h2),
        p(
            "The contractor shall provide cloud migration support services encompassing all phases "
            "of the migration lifecycle. Tasks include but are not limited to:",
            normal,
        ),
        sp(0.1),
        p("C.2.1 Cloud-Readiness Assessments", h2),
        p(
            "The contractor shall conduct comprehensive cloud-readiness assessments for legacy DOI "
            "systems identified by the Government. Each assessment shall include: (a) analysis of "
            "current architecture, dependencies, and data flows; (b) identification of migration "
            "complexity and risk factors; (c) TCO modeling comparing on-premises vs. cloud "
            "operational costs; and (d) a readiness scorecard delivered in a Government-approved "
            "format within 30 days of task order award.",
            normal,
        ),
        sp(0.1),
        p("C.2.2 Migration Roadmaps Targeting AWS GovCloud", h2),
        p(
            "Based on assessment findings, the contractor shall develop detailed migration roadmaps "
            "targeting AWS GovCloud (US) regions. Roadmaps shall specify: (a) migration strategy "
            "per application (lift-and-shift, refactor, replatform, or retire); (b) sequencing "
            "and dependency order; (c) resource estimates and staffing plan; (d) risk register and "
            "mitigation strategies; and (e) FedRAMP compliance checkpoints.",
            normal,
        ),
        sp(0.1),
        p("C.2.3 Lift-and-Shift and Refactor Migrations", h2),
        p(
            "The contractor shall execute approved migration roadmaps. Both lift-and-shift "
            "(rehost) and refactor (re-architect) migration patterns are in scope. The contractor "
            "shall follow DOI OCIO security baseline requirements and obtain ATO continuation or "
            "new ATO as applicable. All production cutovers shall be executed during approved "
            "change windows with documented rollback procedures.",
            normal,
        ),
        sp(0.1),
        p("C.2.4 Post-Migration Support", h2),
        p(
            "Following each application migration, the contractor shall provide 90 days of "
            "post-migration hypercare support. Support shall include: (a) performance monitoring "
            "and optimization; (b) incident response with 4-hour SLA for Priority 1 issues; "
            "(c) cost optimization reviews at 30, 60, and 90 days; and (d) knowledge transfer "
            "sessions for DOI operations staff.",
            normal,
        ),
        PageBreak(),
    ]

    # ── PAGE 3: Section L & M — Instructions and Evaluation ─────────────────
    story += [
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
            "PDF format. File size limit: 50 MB per volume. The Government is not responsible "
            "for technical difficulties encountered during upload.",
            normal,
        ),
        sp(0.15),
        p("L.3 Volume Structure", h2),
        p(
            "Proposals shall consist of three volumes: Volume I — Technical Approach (page limit: "
            "40 pages); Volume II — Past Performance (page limit: 20 pages); Volume III — Price "
            "(no page limit). Each volume shall be uploaded as a separate PDF.",
            normal,
        ),
        sp(0.15),
        p("L.4 Past Performance Requirements", h2),
        p(
            "Offerors shall provide a minimum of two (2) federal cloud migration engagements "
            "completed within the past five (5) years. Each reference shall include: (a) contract "
            "number; (b) agency/customer name and contracting officer contact; (c) period of "
            "performance; (d) contract value; (e) description of cloud migration scope, including "
            "platforms migrated and AWS services utilized; and (f) relevance narrative (1 page max "
            "per reference).",
            normal,
        ),
        sp(0.15),
        p("L.5 Conflict of Interest", h2),
        p(
            "Offerors shall disclose any actual or potential organizational conflicts of interest "
            "(OCI) in accordance with FAR Subpart 9.5. The Contracting Officer will evaluate "
            "disclosed conflicts and may request mitigation plans prior to award.",
            normal,
        ),
        sp(0.25),
        p("SECTION M — EVALUATION CRITERIA", h1),
        sp(0.2),
        p("M.1 Best-Value Tradeoff", h2),
        p(
            "Award will be made on a best-value basis using a tradeoff process. Non-price factors "
            "collectively are significantly more important than price. The Government may pay a "
            "price premium for a technically superior proposal.",
            normal,
        ),
        sp(0.15),
        p("M.2 Evaluation Factors", h2),
        p(
            "Proposals will be evaluated under the following factors in descending order of importance:",
            normal,
        ),
        sp(0.1),
        p(
            "<b>Factor 1 — Technical Approach</b>: The Government will evaluate the offeror's "
            "understanding of the requirement, soundness of the proposed technical approach, "
            "staffing plan (including key personnel qualifications), and management approach. "
            "Subfactors: (a) Technical Understanding and Approach; (b) Staffing and Key Personnel; "
            "(c) Management and Quality Assurance.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>Factor 2 — Past Performance</b>: The Government will evaluate the relevance and "
            "quality of the offeror's recent and relevant past performance on federal cloud "
            "migration contracts. Offerors with no relevant past performance will receive a "
            "Neutral rating. A minimum of two (2) federal references with completed cloud "
            "migrations in the past five (5) years is required.",
            normal,
        ),
        sp(0.1),
        p(
            "<b>Factor 3 — Price</b>: The Government will evaluate the total evaluated price "
            "across all contract line items (CLINs) for the base period and all option periods. "
            "Price realism analysis will be performed. Unbalanced pricing may be cause for "
            "proposal rejection.",
            normal,
        ),
        sp(0.2),
        p("M.3 Adjectival Ratings", h2),
        p(
            "Technical Approach and Past Performance will be rated as: Outstanding, Good, "
            "Acceptable, Marginal, or Unacceptable. Price will be evaluated for fairness and "
            "realism but will not receive an adjectival rating.",
            normal,
        ),
        sp(0.25),
        p("SECTION K — REPRESENTATIONS AND CERTIFICATIONS", h1),
        sp(0.15),
        p(
            "By submitting a proposal, the offeror certifies that it meets all applicable "
            "representations and certifications required under FAR 52.204-8 (Annual "
            "Representations and Certifications). Small Business concerns must be certified "
            "in SAM.gov under NAICS 541512 with the applicable size standard of $34 million "
            "in average annual receipts.",
            normal,
        ),
        sp(0.15),
        p(
            "There is NO requirement for a security clearance under this solicitation. All work "
            "will be performed on unclassified systems at the impact level of FedRAMP Moderate. "
            "The 8(a) Business Development Program does NOT apply to this acquisition.",
            normal,
        ),
    ]

    doc.build(story)
    size_kb = OUT.stat().st_size // 1024
    print(f"Wrote {OUT}  ({size_kb} KB)")


if __name__ == "__main__":
    build()
