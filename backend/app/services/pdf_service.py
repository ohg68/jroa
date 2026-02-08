import os
import base64
import fitz  # PyMuPDF


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload(filename: str, content: bytes) -> str:
    path = os.path.join(UPLOAD_DIR, filename)
    # Avoid overwriting: add suffix if exists
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(path):
        path = os.path.join(UPLOAD_DIR, f"{base}_{counter}{ext}")
        counter += 1
    with open(path, "wb") as f:
        f.write(content)
    return path


def get_pdf_info(path: str) -> dict:
    doc = fitz.open(path)
    info = {
        "total_pages": len(doc),
        "file_size": os.path.getsize(path),
    }
    doc.close()
    return info


def optimize_pdf(input_path: str) -> str:
    """Optimize PDF by reducing image quality and removing unnecessary data."""
    doc = fitz.open(input_path)
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_optimized{ext}"

    for page in doc:
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n >= 5:  # CMYK
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                # Reduce resolution if image is large
                if pix.width > 1200 or pix.height > 1200:
                    scale = 1200 / max(pix.width, pix.height)
                    mat = fitz.Matrix(scale, scale)
                    pix = fitz.Pixmap(pix, 0)  # remove alpha if present
                pix = None  # free memory
            except Exception:
                continue

    doc.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
        linear=True,
    )
    doc.close()
    return output_path


def extract_pages_as_images(path: str, dpi: int = 150) -> list[str]:
    """Extract each page of the PDF as a base64-encoded PNG image."""
    doc = fitz.open(path)
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        # Limit size: if too large, reduce
        if pix.width > 2000 or pix.height > 2000:
            scale = 2000 / max(pix.width, pix.height)
            mat_small = fitz.Matrix(zoom * scale, zoom * scale)
            pix = page.get_pixmap(matrix=mat_small)

        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append(b64)

    doc.close()
    return images


def extract_text_from_pdf(path: str) -> list[str]:
    """Extract text from each page of the PDF."""
    doc = fitz.open(path)
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())
    doc.close()
    return pages_text
