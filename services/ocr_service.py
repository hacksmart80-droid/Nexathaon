import os
import threading
from paddleocr import PaddleOCR
from services.image_processor import preprocess_image_for_ocr
from services.pdf_processor import process_pdf

class OCRService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # Initialized on demand
        self.ocr_engine = None

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_engine(self):
        if self.ocr_engine is None:
            # show_log=False to prevent terminal spam and maintain privacy
            self.ocr_engine = PaddleOCR(use_angle_cls=False, lang='en', show_log=False)
        return self.ocr_engine

    def extract_text_from_image(self, image_path):
        """
        Runs image preprocessing and local PaddleOCR on an image file.
        Returns: {"raw_text": str, "lines": list[str], "line_count": int, "error": str or None}
        """
        if not os.path.exists(image_path):
            return {"raw_text": "", "lines": [], "line_count": 0, "error": "Image file not found."}

        try:
            processed_path = preprocess_image_for_ocr(image_path)
            engine = self._get_engine()
            ocr_result = engine.ocr(processed_path, cls=False)

            lines = []
            if ocr_result and len(ocr_result) > 0 and ocr_result[0]:
                for item in ocr_result[0]:
                    if item and len(item) > 1 and item[1]:
                        text = str(item[1][0]).strip()
                        if text:
                            lines.append(text)

            raw_text = "\n".join(lines)
            return {
                "raw_text": raw_text,
                "lines": lines,
                "line_count": len(lines),
                "error": None if lines else "We couldn't clearly read this document. Upload a clearer copy or enter the information manually."
            }
        except Exception as e:
            return {
                "raw_text": "",
                "lines": [],
                "line_count": 0,
                "error": f"OCR processing failed: {str(e)}"
            }

    def extract_text(self, file_path):
        """
        Unified extraction for PDFs and Images.
        For PDFs: checks selectable text layer first, falls back to OCR if scanned.
        For Images: runs image enhancement and OCR.
        """
        if not os.path.exists(file_path):
            return {"raw_text": "", "lines": [], "line_count": 0, "error": "File not found."}

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            pdf_res = process_pdf(file_path)
            if pdf_res.get("has_digital_text"):
                return {
                    "raw_text": pdf_res["direct_text"],
                    "lines": pdf_res["direct_lines"],
                    "line_count": len(pdf_res["direct_lines"]),
                    "error": None
                }
            elif pdf_res.get("page_image_paths"):
                all_lines = []
                for img_p in pdf_res["page_image_paths"]:
                    page_ocr = self.extract_text_from_image(img_p)
                    all_lines.extend(page_ocr.get("lines", []))
                
                raw_text = "\n".join(all_lines)
                return {
                    "raw_text": raw_text,
                    "lines": all_lines,
                    "line_count": len(all_lines),
                    "error": None if all_lines else "Scanned PDF could not be read clearly. You can verify details manually."
                }
            else:
                return {
                    "raw_text": "",
                    "lines": [],
                    "line_count": 0,
                    "error": pdf_res.get("error") or "Could not extract content from PDF."
                }
        else:
            return self.extract_text_from_image(file_path)

ocr_service = OCRService.get_instance()
