"""Install metadata and root-scoped service worker delivery."""
import unittest

from fastapi.testclient import TestClient
from app import app


class PwaTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_install_assets(self):
        response = self.client.get('/static/manifest.webmanifest')
        self.assertEqual(response.status_code, 200)
        manifest = response.json()
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['display'], 'standalone')
        for icon in manifest['icons']:
            image = self.client.get(icon['src'])
            self.assertEqual(image.status_code, 200)
            self.assertTrue(image.content.startswith(b'\x89PNG\r\n\x1a\n'))
            size = int(icon['sizes'].split('x')[0])
            self.assertEqual(int.from_bytes(image.content[16:20], 'big'), size)
            self.assertEqual(int.from_bytes(image.content[20:24], 'big'), size)

    def test_worker_is_root_scoped_and_revalidated(self):
        response = self.client.get('/sw.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response.headers['content-type'])
        self.assertEqual(response.headers['service-worker-allowed'], '/')
        self.assertEqual(response.headers['cache-control'], 'no-cache')

    def test_offline_notice_is_standalone(self):
        response = self.client.get('/static/offline.html')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Connect to Quote Builder', response.text)
        self.assertNotIn('<script src=', response.text)
        self.assertNotIn('<link rel="stylesheet"', response.text)


if __name__ == '__main__':
    unittest.main()
