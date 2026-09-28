"""Draft previews must resolve export content without persisting jobs."""
import unittest
from unittest.mock import patch

import app


class PreviewTests(unittest.TestCase):
    def setUp(self):
        data = {
            "N": [{"code": "N38", "description": "Tariff one"},
                  {"code": "N39", "description": "Tariff two"}],
            "Other": [{"code": "INTRO1", "description": "Introduction"}],
            "Gate": [{"code": "6", "description": "Gate _ wide", "section": "scope"}],
        }
        index = {i["code"]: [(s, i)] for s, items in data.items() for i in items}
        patcher = patch.object(app.builder, "load_codes", return_value=(data, index))
        renderer = patch.object(app.word_preview, "render", side_effect=lambda doc: {"ok": True, "doc": doc})
        renderer.start()
        self.addCleanup(renderer.stop)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_empty_draft_does_not_save_or_build(self):
        with patch.object(app.os, "makedirs") as mkdir, patch.object(app.builder, "main") as build:
            result = app.api_preview({})
        self.assertTrue(result["ok"])
        self.assertEqual(result["doc"]["header"]["for"], "")
        mkdir.assert_not_called()
        build.assert_not_called()

    def test_resolved_and_edited_content_with_options(self):
        result = app.api_preview({
            "gates": [{"title": "Gate A", "lines": [
                {"code": "6", "qty": 2, "fills": ["24 feet"]},
                {"code": "6", "text": "Custom description", "amount": "50%"},
                {"amount_note": "By others", "amount": "Excluded"}]}],
            "options": [{"text": "Deduct", "amount": "25", "deduct": True}],
            "notes": ["N38"], "total": "200"})
        doc = result["doc"]
        self.assertEqual(doc["gates"][0]["lines"][0]["text"], "Gate 24 feet wide.")
        self.assertEqual(doc["gates"][0]["lines"][1]["text"], "Custom description.")
        self.assertEqual(doc["gates"][0]["lines"][1]["amount"], "50%")
        self.assertTrue(doc["options"][0]["deduct"])
        self.assertEqual(doc["notes"], ["Tariff one"])
        self.assertEqual(doc["total"], "200")

    def test_unresolved_code_returns_error(self):
        result = app.api_preview({"gates": [{"title": "Gate", "lines": [{"code": "missing"}]}]})
        self.assertEqual(result.status_code, 400)

    def test_word_failure_is_explicit_not_an_approximate_preview(self):
        with patch.object(app.word_preview, "render", side_effect=RuntimeError("Word unavailable")):
            result = app.api_preview({})
        self.assertEqual(result.status_code, 503)
        self.assertIn(b"Word unavailable", result.body)


if __name__ == "__main__":
    unittest.main()
