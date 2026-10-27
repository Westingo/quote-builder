"""Carry editable quote data in a standard Word custom XML part."""
import io
import zipfile
from xml.etree import ElementTree as ET

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part

import quote_transfer

MAX_BYTES = 25 * 1024 * 1024
PART = "customXml/metroQuote.xml"
TAG = "{urn:metro:quote-builder:1}quote"


def embed(path, job):
    root = ET.Element(TAG)
    root.text = quote_transfer.export_quote(job).decode("utf-8")
    doc = Document(path)
    part = Part(PackURI('/' + PART), 'application/xml',
                ET.tostring(root, encoding='utf-8', xml_declaration=True), doc.part.package)
    doc.part.relate_to(part, RT.CUSTOM_XML)
    doc.save(path)


def extract(data):
    if len(data) > MAX_BYTES:
        raise ValueError("Word file exceeds the 25 MB limit.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            # Word can rename custom XML parts when saving a document.
            for info in archive.infolist():
                if not info.filename.startswith('customXml/') or not info.filename.endswith('.xml'):
                    continue
                if info.file_size > quote_transfer.MAX_BYTES * 6:
                    raise ValueError("Attached quote exceeds the size limit.")
                raw = archive.read(info)
                if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
                    raise ValueError("Unsupported XML in Word file.")
                root = ET.fromstring(raw)
                if root.tag == TAG:
                    return quote_transfer.import_quote((root.text or '').encode('utf-8'))
    except (zipfile.BadZipFile, ET.ParseError, RuntimeError, OSError) as exc:
        raise ValueError("This Word file could not be read. Choose a .docx built by Quote Builder.") from exc
    raise ValueError("This Word file has no editable quote attached. On the original computer, open the saved quote and use Save editable copy, or rebuild it with the updated Quote Builder.")
