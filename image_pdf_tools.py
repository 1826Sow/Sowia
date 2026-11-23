"""Safe, bounded conversions between common image formats and PDF."""
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageOps
import pypdfium2 as pdfium

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 50 * 1024 * 1024
MAX_IMAGES = 40
MAX_PDF_BYTES = 30 * 1024 * 1024
MAX_PDF_PAGES = 30
MAX_RENDER_PIXELS = 40_000_000


def _normalise_image(payload):
    if not isinstance(payload, (bytes, bytearray)) or not payload:
        raise ValueError("Une image sélectionnée est vide ou illisible.")
    if len(payload) > MAX_IMAGE_BYTES:
        raise ValueError("Chaque image doit peser 20 Mo maximum.")
    try:
        with Image.open(BytesIO(payload)) as source:
            if source.width < 1 or source.height < 1 or source.width * source.height > MAX_RENDER_PIXELS:
                raise ValueError("Les dimensions de l’image sont invalides ou trop importantes.")
            source.load()
            image = ImageOps.exif_transpose(source)
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            return image.copy()
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Une image est endommagée ou utilise un format non pris en charge.") from exc


def images_to_pdf(named_images):
    """Create one multi-page PDF from uploaded (filename, bytes) image pairs."""
    if not isinstance(named_images, (list, tuple)) or not named_images:
        raise ValueError("Sélectionnez au moins une image.")
    if len(named_images) > MAX_IMAGES:
        raise ValueError(f"Vous pouvez convertir au maximum {MAX_IMAGES} images à la fois.")
    total = 0
    pages = []
    try:
        for filename, payload in named_images:
            total += len(payload) if isinstance(payload, (bytes, bytearray)) else 0
            if total > MAX_TOTAL_IMAGE_BYTES:
                raise ValueError("Le poids total des images ne doit pas dépasser 50 Mo.")
            pages.append(_normalise_image(payload))
        output = BytesIO()
        first, *remaining = pages
        first.save(output, format="PDF", save_all=True, append_images=remaining, resolution=150.0)
        return output.getvalue()
    finally:
        for page in pages:
            page.close()


def pdf_to_images_zip(pdf_bytes, image_format="PNG", scale=1.5):
    """Render each PDF page into PNG/JPG files and return a ZIP archive."""
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes:
        raise ValueError("Sélectionnez un PDF valide.")
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("Le PDF ne doit pas dépasser 30 Mo.")
    output_format = str(image_format or "PNG").upper()
    if output_format not in {"PNG", "JPG"}:
        raise ValueError("Choisissez le format PNG ou JPG.")
    try:
        document = pdfium.PdfDocument(bytes(pdf_bytes))
    except Exception as exc:
        raise ValueError("Le PDF est illisible, endommagé ou protégé par mot de passe.") from exc
    archive_buffer = BytesIO()
    try:
        page_count = len(document)
        if page_count < 1:
            raise ValueError("Le PDF ne contient aucune page.")
        if page_count > MAX_PDF_PAGES:
            raise ValueError(f"La conversion est limitée à {MAX_PDF_PAGES} pages par opération.")
        with ZipFile(archive_buffer, "w", compression=ZIP_DEFLATED) as archive:
            for index in range(page_count):
                page = document[index]
                bitmap = None
                image = None
                try:
                    page_width, page_height = page.get_size()
                    estimated_pixels = int(page_width * scale * 72) * int(page_height * scale * 72)
                    if estimated_pixels > MAX_RENDER_PIXELS:
                        raise ValueError("Une page dépasse la limite de résolution autorisée.")
                    bitmap = page.render(scale=scale)
                    image = bitmap.to_pil()
                    if image.width * image.height > MAX_RENDER_PIXELS:
                        raise ValueError("Une page dépasse la limite de résolution autorisée.")
                    buffer = BytesIO()
                    if output_format == "JPG":
                        image.convert("RGB").save(buffer, format="JPEG", quality=92, optimize=True)
                        extension = "jpg"
                    else:
                        image.save(buffer, format="PNG", optimize=True)
                        extension = "png"
                    archive.writestr(f"page_{index + 1:03d}.{extension}", buffer.getvalue())
                finally:
                    for resource in (image, bitmap, page):
                        close = getattr(resource, "close", None)
                        if callable(close):
                            try:
                                close()
                            except Exception:
                                pass
        return archive_buffer.getvalue()
    finally:
        close = getattr(document, "close", None)
        if callable(close):
            close()
