import io
import re
from pypdf import PdfReader
from fastapi import HTTPException, UploadFile


def clean_extracted_text(text: str) -> str:
    """
    Basic cleanup for PDF-extracted text.
    """
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse too many blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


async def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Read uploaded PDF and return cleaned extracted text.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported for file upload."
        )

    try:
        contents = await file.read()
        pdf_stream = io.BytesIO(contents)
        reader = PdfReader(pdf_stream)

        page_texts = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            if extracted.strip():
                page_texts.append(extracted)

        full_text = "\n\n".join(page_texts)
        cleaned_text = clean_extracted_text(full_text)

        if not cleaned_text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract readable text from the PDF."
            )

        return cleaned_text

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse PDF: {str(exc)}"
        ) from exc