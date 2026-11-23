from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image
from pypdf import PdfReader

from image_pdf_tools import images_to_pdf, pdf_to_images_zip


def _png_bytes(color):
    buffer = BytesIO()
    Image.new("RGB", (24, 18), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_multiple_images_become_one_multipage_pdf():
    result = images_to_pdf([
        ("one.png", _png_bytes("red")),
        ("two.png", _png_bytes("blue")),
    ])
    reader = PdfReader(BytesIO(result))
    assert len(reader.pages) == 2


def test_pdf_pages_export_to_png_zip():
    pdf_bytes = images_to_pdf([("one.png", _png_bytes("red")), ("two.png", _png_bytes("blue"))])
    archive_bytes = pdf_to_images_zip(pdf_bytes, image_format="PNG")
    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert archive.namelist() == ["page_001.png", "page_002.png"]
        with Image.open(BytesIO(archive.read("page_001.png"))) as image:
            assert image.format == "PNG"


def test_empty_image_selection_is_rejected():
    with pytest.raises(ValueError, match="au moins une image"):
        images_to_pdf([])


def test_invalid_pdf_is_rejected():
    with pytest.raises(ValueError, match="PDF valide"):
        pdf_to_images_zip(b"not a pdf")
