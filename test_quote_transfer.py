"""Transfer real editable data, preserving isolation and rejecting bad uploads."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
import quote_backup
import quote_pdf
import quote_transfer as transfer
import pymupdf


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p = patch.object(app, "JOBS", self.temp.name)
        p.start()
        self.addCleanup(p.stop)
        backups = patch.dict("os.environ", {"QUOTE_BACKUP_DIR": str(Path(self.temp.name) / "backups")})
        backups.start()
        self.addCleanup(backups.stop)
        self.client = TestClient(app.app)
        self.job = {
            "slug": "do-not-overwrite",
            "proposal": {"for": "Liv’s customer", "ccb": "123", "cc": "CUSTOM"},
            "gate_summary": ["Gate B", "Gate A"],
            "gates": [{"title": "Gate B", "lines": [
                {"code": "RETIRED", "text": "Liv’s custom wording × 2", "qty": 2, "label": "Supply", "amount": "125"},
                {"text": "Indented note", "sub": True},
                {"amount_note": "By others", "amount": "Excluded"}]}],
            "options": [{"title": "Detailed option", "lines": [{"text": "Custom", "qty": 1}], "amount": "200", "deduct": True},
                        {"kind": "block", "title": "Low Voltage", "bullets": ["First", "Second"], "priced": [{"label": "Single", "amount": "50"}]}],
            "notes": [{"code": "N1", "text": "Saved note"}, {"text": "Custom note"}],
            "warranties": [{"text": "Liv warranty"}], "exclusions": [], "total": "1,234.50"}

    def upload(self, data):
        return self.client.post("/api/quote/import", files={"file": ("quote.metroquote", data)})

    def test_roundtrip_saved_copies_and_build_isolation(self):
        exported = self.client.post("/api/quote/export", json=self.job)
        self.assertEqual(exported.status_code, 200)
        self.assertIn(".metroquote", exported.headers["content-disposition"])
        expected = {k: v for k, v in self.job.items() if k != "slug"}
        first = self.upload(exported.content).json()
        second = self.upload(exported.content).json()
        self.assertNotEqual(first["slug"], second["slug"])
        self.assertEqual(first["job"], expected)
        self.assertEqual(self.client.get("/api/job/" + first["slug"]).json(), expected)
        edited = copy.deepcopy(first["job"])
        edited.update(slug=first["slug"], total="999")
        with patch.object(app.builder, "main", return_value="Proposal.docx"):
            result = self.client.post("/api/build", json=edited)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["slug"], first["slug"])
        self.assertEqual(self.client.get("/api/job/" + second["slug"]).json(), expected)
        self.assertFalse((Path(self.temp.name) / "do-not-overwrite").exists())

    def test_invalid_files_do_not_save(self):
        valid = json.loads(transfer.export_quote(self.job))
        bad_shape = copy.deepcopy(valid)
        bad_shape["job"]["gates"][0]["lines"] = [None]
        bad_block = copy.deepcopy(valid)
        del bad_block["job"]["options"][1]["priced"]
        for data in (b"not json", b"{}", b"%PDF-1.7", json.dumps(dict(valid, version=2)).encode(),
                     json.dumps(bad_shape).encode(), json.dumps(bad_block).encode(), b"x" * (transfer.MAX_BYTES + 1)):
            with self.subTest(data=data[:80]):
                self.assertEqual(self.upload(data).status_code, 400)
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_saved_wording_builds_without_source_products(self):
        job = transfer.import_quote(transfer.export_quote(self.job))
        data, index = app.builder.load_codes()
        self.assertNotIn("RETIRED", index)
        doc = app.builder.build_doc(job, data, index)
        self.assertIn("Liv’s custom wording", str(doc))
        self.assertIn("Saved note", str(doc))

    def pdf_bytes(self):
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((72, 72), "Metro test proposal - page unchanged")
            return pdf.tobytes()

    def test_pdf_roundtrip_preserves_visible_page(self):
        original = self.pdf_bytes()
        embedded = quote_pdf.embed(original, self.job)
        expected = transfer.import_quote(transfer.export_quote(self.job))
        self.assertEqual(quote_pdf.extract(embedded), expected)
        with pymupdf.open(stream=original, filetype="pdf") as before, pymupdf.open(stream=embedded, filetype="pdf") as after:
            self.assertEqual(before[0].get_pixmap().samples, after[0].get_pixmap().samples)
            self.assertEqual(after.embfile_names(), [quote_pdf.ATTACHMENT])
        result = self.client.post("/api/quote/import", files={"file": ("Liv.pdf", embedded)})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["job"], expected)
        self.assertTrue(Path(result.json()["backup"]).is_file())

    def test_plain_pdf_does_not_save_or_call_ai(self):
        with patch.object(app.scan_import, "import_scan") as scan:
            result = self.client.post("/api/quote/import", files={"file": ("plain.pdf", self.pdf_bytes())})
        self.assertEqual(result.status_code, 400)
        self.assertIn("no editable quote", result.json()["error"])
        scan.assert_not_called()
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_backup_revisions_and_failed_backup_warning(self):
        first = quote_backup.save(self.job, "liv")
        updated = copy.deepcopy(self.job)
        updated["total"] = "456"
        second = quote_backup.save(updated, "liv")
        self.assertNotEqual(first, second)
        self.assertEqual(transfer.import_quote(Path(first).read_bytes())["total"], "1,234.50")
        self.assertEqual(transfer.import_quote(Path(second).read_bytes())["total"], "456")
        with patch.object(app.builder, "main", return_value="Proposal.docx"), patch.object(quote_backup, "save", side_effect=PermissionError("Folder unavailable")):
            result = self.client.post("/api/build", json=self.job).json()
        self.assertTrue(result["ok"])
        self.assertIsNone(result["backup"])
        self.assertIn("backup failed", result["warnings"][0])

    def test_pdf_build_download_and_word_failure(self):
        with patch.object(app.builder, "main", side_effect=lambda folder: str(Path(folder) / "Proposal.docx")), patch.object(app.word_preview, "export_pdf", return_value=self.pdf_bytes()):
            first = self.client.post("/api/build?pdf=true", json=self.job).json()
            second = self.client.post("/api/build?pdf=true", json=self.job).json()
        self.assertNotEqual(first["pdf"], second["pdf"])
        download = self.client.get(f'/download/{first["slug"]}/{first["pdf"]}')
        self.assertEqual(download.headers["content-type"], "application/pdf")
        self.assertEqual(quote_pdf.extract(download.content)["proposal"], self.job["proposal"])
        with patch.object(app.builder, "main", return_value="Proposal.docx"), patch.object(app.word_preview, "export_pdf", side_effect=RuntimeError("Word unavailable")):
            result = self.client.post("/api/build?pdf=true", json=self.job).json()
        self.assertTrue(result["ok"])
        self.assertIsNone(result["pdf"])
        self.assertIn("PDF was not created", result["warnings"][0])
        self.assertTrue(Path(result["backup"]).exists())


if __name__ == "__main__":
    unittest.main()
