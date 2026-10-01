"""Formatting survives transfers and reaches actual Word paragraph/cell settings."""
from pathlib import Path
import tempfile
import unittest

from docx import Document
from docx.shared import Inches
from docx.enum.table import WD_ALIGN_VERTICAL

import build
import proposal
import quote_transfer
import quote_format


def fixture():
    return {"proposal": {"for": "Formatting check"}, "gates": [
        {"title": "Aligned items", "format": {"font_size": 9, "space_after": 5}, "lines": [
            {"qty": 2, "text": "First description line\nSecond description line\nThird description line", "amount": "100", "format": {"amount_align": "top", "bold": True}},
            {"qty": 1, "text": "Text starts at the quantity column and wraps to that same position. " * 3, "amount": "200", "format": {"start": "quantity", "wrap": "start", "amount_align": "center", "underline": True}},
            {"text": "Full-width note with no quantity marker. " * 3, "format": {"start": "left", "font_size": 10}}]},
        {"title": "New-page section", "format": {"page_break": True, "keep_together": True}, "lines": [{"text": "Section kept together", "qty": 1}]}],
        "options": [{"title": "Detailed option", "format": {"font_size": 9}, "lines": [{"amount_note": "Amount at top", "amount": "300", "format": {"amount_align": "top"}}]}]}


class FormatTests(unittest.TestCase):
    def test_transfer_and_docx_formatting(self):
        job = fixture()
        self.assertEqual(quote_transfer.import_quote(quote_transfer.export_quote(job)), job)
        data, index = build.load_codes()
        normalized = build.build_doc(job, data, index)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.docx"
            proposal.build_proposal(normalized, str(path))
            doc = Document(path)
        gate = doc.tables[1]
        first = gate.cell(1, 0).paragraphs[0]
        self.assertTrue(all(r.bold for r in first.runs))
        self.assertEqual(first.runs[-1].font.size.pt, 9)
        self.assertIn("\nSecond", first.text)
        self.assertEqual(first.paragraph_format.space_after.pt, 5)
        self.assertEqual(gate.cell(1, 1).vertical_alignment, WD_ALIGN_VERTICAL.TOP)
        second = gate.cell(2, 0).paragraphs[0]
        self.assertTrue(all(r.underline for r in second.runs))
        self.assertAlmostEqual(second.paragraph_format.left_indent.inches, 0.62, places=3)
        self.assertNotIn("1)", second.text)
        self.assertEqual(gate.cell(2, 1).vertical_alignment, WD_ALIGN_VERTICAL.CENTER)
        third = gate.cell(3, 0).paragraphs[0]
        self.assertEqual(third.paragraph_format.left_indent, 0)
        self.assertTrue(doc._element.xpath('.//w:br[@w:type="page"]'))
        self.assertTrue(doc.tables[2].cell(0, 0).paragraphs[0].paragraph_format.keep_with_next)
        self.assertEqual(doc.tables[3].cell(1, 1).vertical_alignment, WD_ALIGN_VERTICAL.TOP)

    def test_bad_format_is_rejected(self):
        for value in ({"font_size": 0}, {"line_spacing": float('nan')}, {"start": "bad"}, {"page_break": "yes"}, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                quote_format.validate(value)


if __name__ == "__main__":
    unittest.main()
