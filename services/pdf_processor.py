import os
import pymupdf  # PyMuPDF
from PIL import Image
import io

MAX_PDF_PAGES = 5

def process_pdf(pdf_path, output_dir=None):
    """
    Analyzes a PDF file:
    1. Checks if it contains selectable digital text.
    2. If text is sufficient (> 50 readable characters), extracts digital text lines.
    3. If scanned or sparse, renders pages as high-resolution PNG images (300 DPI) for OCR.
    Returns:
    {
        "has_digital_text": bool,
        "direct_text": str,
        "direct_lines": list[str],
        "page_image_paths": list[str],
        "page_count": int,
        "error": str or None
    }
    """
    result = {
        "has_digital_text": False,
        "direct_text": "",
        "direct_lines": [],
        "page_image_paths": [],
        "page_count": 0,
        "error": None
    }

    if not os.path.exists(pdf_path):
        result["error"] = "PDF file not found."
        return result

    if not output_dir:
        output_dir = os.path.dirname(pdf_path)

    try:
        doc = pymupdf.open(pdf_path)
        total_pages = min(len(doc), MAX_PDF_PAGES)
        result["page_count"] = total_pages

        combined_text = []
        all_lines = []

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_text = page.get_text("text").strip()
            if page_text:
                combined_text.append(page_text)
                for line in page_text.splitlines():
                    cleaned_line = line.strip()
                    if cleaned_line:
                        all_lines.append(cleaned_line)

        raw_text_str = "\n".join(combined_text)
        
        # If there is meaningful extracted digital text (more than 50 characters)
        if len(raw_text_str.strip()) >= 50:
            result["has_digital_text"] = True
            result["direct_text"] = raw_text_str
            result["direct_lines"] = all_lines
        else:
            # Document appears to be a scanned PDF; render pages to images for OCR
            result["has_digital_text"] = False
            for page_idx in range(total_pages):
                page = doc[page_idx]
                # Render page at 2.0x zoom (approx 150-200 DPI, sharp for OCR)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2.0, 2.0))
                img_path = os.path.join(output_dir, f"page_{page_idx + 1}.png")
                pix.save(img_path)
                result["page_image_paths"].append(img_path)

        doc.close()
    except Exception as e:
        result["error"] = f"Could not process PDF: {str(e)}"

    return result
