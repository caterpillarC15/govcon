from pathlib import Path

from api.agent.tools.parse_pdf import parse_pdf


def make_text_pdf(path: Path, lines: list[str]) -> None:
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path))
    y = 760
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()
    c.save()


def make_blank_pdf(path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as f:
        writer.write(f)


def test_parse_pdf_extracts_page_level_chunks(tmp_path):
    pdf = tmp_path / "solicitation.pdf"
    make_text_pdf(pdf, [
        "Solicitation: VA facilities support",
        "Set-aside: Total Small Business",
        "Deadline: May 21, 2026",
        "Contractor must provide preventive maintenance and references.",
    ])

    out = parse_pdf(pdf)

    assert out.doc_id == "solicitation"
    assert out.page_count == 1
    assert not out.unparseable
    assert len(out.chunks) == 1
    assert out.chunks[0].page_number == 1
    assert "Total Small Business" in out.chunks[0].text
    assert out.chunks[0].char_count == len(out.chunks[0].text)


def test_parse_pdf_marks_image_or_blank_pdf_unparseable(tmp_path):
    pdf = tmp_path / "blank.pdf"
    make_blank_pdf(pdf)

    out = parse_pdf(pdf)

    assert out.page_count == 1
    assert out.unparseable
    assert out.chunks == []
