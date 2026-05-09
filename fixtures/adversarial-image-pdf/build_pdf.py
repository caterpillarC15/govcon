"""Build the adversarial image-only PDF. pypdf must NOT be able to extract text."""
from pathlib import Path
import io
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "attachments" / "RFP-IMAGE.pdf"


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # 1700x2200 ~= LETTER at 200 dpi
    img = Image.new("RGB", (1700, 2200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((100, 200), "REQUEST FOR PROPOSAL", fill=(0, 0, 0), font=font)
    draw.text((100, 400), "Solicitation TEST-IMG-2026-001", fill=(0, 0, 0), font=font)
    draw.text((100, 600), "[image of text -- should not parse]", fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    c = canvas.Canvas(str(OUT), pagesize=LETTER, invariant=1)
    c.setProducer("govcapture-fixture")
    c.setCreator("build_pdf.py")
    c.setPageCompression(0)
    c.drawImage(ImageReader(buf), 0, 0, width=LETTER[0], height=LETTER[1])
    c.showPage()
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
