import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import scan_import


def response(text, reason='end_turn'):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)], stop_reason=reason)


class ScanRetryTests(unittest.TestCase):
    def run_scan(self, responses):
        client = MagicMock()
        client.messages.create.side_effect = responses
        with patch('anthropic.Anthropic', return_value=client), patch.object(scan_import, 'api_key', return_value='test-only'), patch.object(scan_import.build, 'load_codes', return_value=({}, {})), patch.object(scan_import, 'MODEL', 'claude-opus-4-8'):
            result = scan_import.import_scan(b'fake-image', 'image/png')
        return result, client

    def test_valid_response_needs_one_call(self):
        result, client = self.run_scan([response('{"proposal":{"for":"Customer"},"gates":[]}')])
        self.assertEqual(result[0]['proposal']['for'], 'Customer')
        self.assertEqual(client.messages.create.call_count, 1)
        client.close.assert_called_once()

    def test_missing_delimiter_retries_original_scan(self):
        result, client = self.run_scan([response('{"proposal":{} "gates":[]}'), response('{"proposal":{},"gates":[{"lines":[{"text":"8 inch unit","qty":1}]}],"warranties":["Second","First"]}')])
        self.assertEqual(result[0]['gates'][0]['lines'][0]['text'], '8 inch unit')
        self.assertEqual(result[0]['warranties'], [{'text':'Second'}, {'text':'First'}])
        calls = client.messages.create.call_args_list
        self.assertEqual(calls[1].kwargs['max_tokens'], 16000)
        self.assertEqual(calls[0].kwargs['messages'][0]['content'][0], calls[1].kwargs['messages'][0]['content'][0])

    def test_truncated_valid_json_is_retried(self):
        _, client = self.run_scan([response('{"proposal":{}}', 'max_tokens'), response('{"proposal":{}}')])
        self.assertEqual(client.messages.create.call_count, 2)

    def test_repeated_invalid_response_is_readable(self):
        with self.assertRaisesRegex(RuntimeError, 'current quote has not been changed'):
            self.run_scan([response('{bad'), response('{bad')])

    def test_bad_shape_is_retried(self):
        _, client = self.run_scan([response('{"gates":[null]}'), response('{"proposal":{}}')])
        self.assertEqual(client.messages.create.call_count, 2)

    def test_refusal_does_not_retry(self):
        with self.assertRaisesRegex(RuntimeError, 'declined'):
            self.run_scan([response('', 'refusal')])

if __name__ == '__main__':
    unittest.main()
