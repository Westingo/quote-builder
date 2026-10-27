import unittest
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch
import scan_import

VALID = '{"proposal":{"for":"Customer"},"gates":[{"lines":[{"text":"Gate","qty":2,"amount":"$100"}]}],"warranties":["Second","First"]}'

def result(text=VALID, status='completed', output=None):
    return NS(output_text=text, status=status, output=output or [])

class LunaTests(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        for target, kwargs in [
            ('openai.OpenAI', {'return_value':self.client}),
            ('scan_import.openai_api_key', {'return_value':'test-only'}),
            ('scan_import.build.load_codes', {'return_value':({}, {})}),
            ('scan_import._import_claude', {'side_effect':AssertionError('Unexpected Claude charge')})
        ]:
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_default_image_and_mapping(self):
        self.client.responses.create.return_value = result()
        job, _ = scan_import.import_scan(b'image', 'image/png')
        self.assertEqual(job['gates'][0]['lines'][0]['amount'], '$100')
        self.assertEqual(job['warranties'], [{'text':'Second'}, {'text':'First'}])
        args=self.client.responses.create.call_args.kwargs
        self.assertEqual(args['model'], 'gpt-6-luna')
        self.assertEqual(args['reasoning'], {'effort':'low'})
        self.assertEqual(args['input'][0]['content'][0]['type'], 'input_image')
        self.client.close.assert_called_once()

    def test_pdf_payload(self):
        self.client.responses.create.return_value = result()
        scan_import.import_scan(b'pdf', 'application/octet-stream', 'Quote.PDF')
        media=self.client.responses.create.call_args.kwargs['input'][0]['content'][0]
        self.assertEqual(media['type'], 'input_file')
        self.assertTrue(media['file_data'].startswith('data:application/pdf;base64,'))

    def test_truncated_response_retried_once(self):
        self.client.responses.create.side_effect=[result(status='incomplete'), result()]
        scan_import.import_scan(b'image', 'image/png')
        self.assertEqual(self.client.responses.create.call_count, 2)
        self.assertEqual(self.client.responses.create.call_args.kwargs['max_output_tokens'], 16000)

    def test_invalid_shape_fails_without_claude(self):
        self.client.responses.create.return_value=result('{"gates":[null]}')
        with self.assertRaisesRegex(RuntimeError, 'current quote has not been changed'):
            scan_import.import_scan(b'image','image/png')
        self.assertEqual(self.client.responses.create.call_count,2)
        self.client.close.assert_called_once()

    def test_refusal_no_retry(self):
        self.client.responses.create.return_value=result(output=[NS(content=[NS(type='refusal')])])
        with self.assertRaisesRegex(RuntimeError,'declined'):
            scan_import.import_scan(b'image','image/png')
        self.assertEqual(self.client.responses.create.call_count,1)

    def test_api_error_no_provider_fallback(self):
        self.client.responses.create.side_effect=RuntimeError('API unavailable')
        with self.assertRaisesRegex(RuntimeError,'API unavailable'):
            scan_import.import_scan(b'image','image/png')
        self.assertEqual(self.client.responses.create.call_count,1)
        self.client.close.assert_called_once()

    def test_missing_key_no_request(self):
        with patch('scan_import.openai_api_key',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'openai_api_key.txt'):
                scan_import.import_scan(b'image','image/png')
        self.client.responses.create.assert_not_called()

    def test_invalid_provider_no_request(self):
        with self.assertRaises(ValueError):
            scan_import.import_scan(b'image','image/png',provider='unknown')
        self.client.responses.create.assert_not_called()

    def test_endpoint_defaults_and_explicit_selection(self):
        import asyncio
        import httpx
        import app
        async def check():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app.app), base_url="http://test") as client:
                with patch('scan_import.import_scan',return_value=({},'')) as scan:
                    response = await client.post('/api/import', files={'file':('scan.pdf',b'pdf','application/pdf')})
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(scan.call_args.kwargs['provider'],'luna')
                    response = await client.post('/api/import', files={'file':('scan.pdf',b'pdf','application/pdf')},data={'provider':'claude'})
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(scan.call_args.kwargs['provider'],'claude')
        asyncio.run(check())

if __name__ == '__main__':
    unittest.main()
