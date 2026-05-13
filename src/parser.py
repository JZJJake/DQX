import os
import chardet
from docx import Document
import win32com.client
import fitz  # PyMuPDF
from paddleocr import PaddleOCR
import tempfile
import logging

# Initialize PaddleOCR globally to avoid reloading the model for every page
# Use use_angle_cls=True to automatically rotate images if needed
# lang='ch' supports Chinese and English, plus some symbols
_ocr = None
def get_ocr():
    global _ocr
    if _ocr is None:
        # We initialize it only when needed to save memory if OCR isn't used
        _ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _ocr

def parse_txt_md(filepath):
    try:
        with open(filepath, 'rb') as f:
            raw_data = f.read()

        result = chardet.detect(raw_data)
        encoding = result['encoding'] or 'utf-8'

        return raw_data.decode(encoding, errors='replace')
    except Exception as e:
        logging.error(f"Error reading TXT/MD {filepath}: {e}")
        return ""

def parse_docx(filepath):
    try:
        doc = Document(filepath)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return "\n".join(text)
    except Exception as e:
        logging.error(f"Error reading DOCX {filepath}: {e}")
        return ""

def parse_doc_wps(filepath):
    """
    Uses COM to open Word (or WPS if Word isn't available).
    Since we are on Windows, win32com should work for .doc and .wps.
    """
    word = None
    doc = None
    try:
        # Try launching Word first
        try:
            word = win32com.client.DispatchEx("Word.Application")
        except Exception:
            # Fallback to WPS
            try:
                word = win32com.client.DispatchEx("KWPS.Application")
            except Exception as e:
                logging.error("MS Word and WPS are not available or COM dispatch failed.")
                return ""

        word.Visible = False
        # Filepath must be absolute for COM
        abs_filepath = os.path.abspath(filepath)
        doc = word.Documents.Open(abs_filepath)

        text = doc.Content.Text
        # Clean up some weird COM chars like \r
        text = text.replace('\r', '\n')
        return text
    except Exception as e:
        logging.error(f"Error reading DOC/WPS {filepath}: {e}")
        return ""
    finally:
        if doc:
            try:
                doc.Close(False)
            except:
                pass
        if word:
            try:
                word.Quit()
            except:
                pass

def parse_pdf(filepath):
    """
    Extracts text from PDF. If a page has little to no text, assumes it's an image
    and runs OCR on it.
    """
    try:
        doc = fitz.open(filepath)
        text_pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Try basic text extraction
            page_text = page.get_text("text").strip()

            # If there's barely any text, it might be a scanned PDF or image-based PDF
            if len(page_text) < 50:
                # Render page to image
                pix = page.get_pixmap(dpi=200) # 200 DPI is usually good for OCR
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_filename = tmp.name

                pix.save(tmp_filename)

                try:
                    ocr = get_ocr()
                    result = ocr.ocr(tmp_filename, cls=True)
                    ocr_text = []
                    if result and result[0]:
                        for line in result[0]:
                            # line is [ [ [x, y], ... ], (text, confidence) ]
                            ocr_text.append(line[1][0])
                    page_text += "\n" + "\n".join(ocr_text)
                finally:
                    if os.path.exists(tmp_filename):
                        os.remove(tmp_filename)

            text_pages.append(page_text)

        return "\n".join(text_pages)
    except Exception as e:
        logging.error(f"Error reading PDF {filepath}: {e}")
        return ""

def parse_document(filepath):
    """
    Main entrypoint. Routes to the appropriate parser based on extension.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext in ['.txt', '.md']:
        return parse_txt_md(filepath)
    elif ext == '.docx':
        return parse_docx(filepath)
    elif ext in ['.doc', '.wps']:
        return parse_doc_wps(filepath)
    elif ext == '.pdf':
        return parse_pdf(filepath)
    else:
        logging.error(f"Unsupported file format: {ext}")
        return ""
