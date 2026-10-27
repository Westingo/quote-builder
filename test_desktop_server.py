"""A second desktop window must never rely on the first window's server."""
import socket
import unittest
from unittest.mock import patch

import desktop


class DesktopServerTests(unittest.TestCase):
    def test_second_window_reserves_independent_port(self):
        with patch.object(desktop, 'PORT', 0):
            first = desktop._reserve_server_socket()
        self.addCleanup(first.close)
        first_port = first.getsockname()[1]
        with patch.object(desktop, 'PORT', first_port):
            second = desktop._reserve_server_socket()
        self.addCleanup(second.close)
        self.assertNotEqual(first_port, second.getsockname()[1])
        first.close()
        with socket.create_connection(second.getsockname(), timeout=2):
            pass


if __name__ == '__main__':
    unittest.main()
