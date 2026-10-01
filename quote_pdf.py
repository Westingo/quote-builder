"""Store editable quote data as a standard PDF file attachment."""
import pymupdf

import quote_transfer

MAX_PDF_BYTES = 25 * 1024 * 1024
ATTACHMENT = "quote.metroquote"


def embed(pdf_bytes, job):
    data = quote_transfer.export_quote(job)
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        if ATTACHMENT in pdf.embfile_names():
            pdf.embfile_del(ATTACHMENT)
        pdf.embfile_add(ATTACHMENT, data, filename=ATTACHMENT,
                       desc="Editable Metro Quote Builder data")
        return pdf.tobytes()


def extract(pdf_bytes):
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds the 25 MB limit.")
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise ValueError("Unlock this PDF before importing it.")
            if ATTACHMENT not in pdf.embfile_names():
                raise ValueError("This PDF has no editable quote attached. Ask the sender to use Build PDF in Quote Builder, or import it with Start from a Scan for an AI draft.")
            info = pdf.embfile_info(ATTACHMENT)
            if info["size"] > quote_transfer.MAX_BYTES:
                raise ValueError("Attached quote exceeds the 5 MB limit.")
            return quote_transfer.import_quote(pdf.embfile_get(ATTACHMENT))
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise ValueError("This PDF could not be read. Choose a PDF made with Build PDF.") from exc
