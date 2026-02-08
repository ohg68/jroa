import base64
import os

import fitz  # PyMuPDF


def get_pdf_info(path: str) -> dict:
    doc = fitz.open(path)
    info = {
        "total_pages": len(doc),
        "file_size": os.path.getsize(path),
    }
    doc.close()
    return info


def optimize_pdf(input_path: str) -> str:
    """Optimize PDF by cleaning metadata, compressing, and linearizing."""
    doc = fitz.open(input_path)
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_optimized{ext}"

    for page in doc:
        image_list = page.get_images(full=True)
        for img in image_list:
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n >= 5:  # CMYK -> RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                pix = None
            except Exception:
                continue

    doc.save(output_path, garbage=4, deflate=True, clean=True, linear=True)
    doc.close()
    return output_path


def extract_text_from_pdf(path: str) -> list[str]:
    """Extract text content from each page."""
    doc = fitz.open(path)
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return pages_text


def extract_pages_as_images(path: str, dpi: int = 150) -> list[str]:
    """Render each page as a base64 PNG image."""
    doc = fitz.open(path)
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        if pix.width > 2000 or pix.height > 2000:
            scale = 2000 / max(pix.width, pix.height)
            mat_small = fitz.Matrix(zoom * scale, zoom * scale)
            pix = page.get_pixmap(matrix=mat_small)

        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append(b64)

    doc.close()
    return images
