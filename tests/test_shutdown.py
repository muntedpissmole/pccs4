import threading
import unittest
from unittest.mock import MagicMock, patch

import app as pccs_app


class ShutdownApiTests(unittest.TestCase):
    def test_issue_host_shutdown_invokes_sudo(self):
        with patch("app.subprocess.Popen") as popen:
            popen.return_value = MagicMock()
            self.assertTrue(pccs_app._issue_host_shutdown())
            popen.assert_called_once()
            args = popen.call_args[0][0]
            self.assertEqual(args, ["sudo", "-n", "shutdown", "-h", "now"])

    def test_cleanup_best_effort_times_out_without_blocking(self):
        barrier = threading.Event()

        def slow_cleanup():
            barrier.wait(timeout=2)

        with patch("app.cleanup", side_effect=slow_cleanup):
            with patch("app.logger") as logger:
                pccs_app._cleanup_best_effort(timeout_s=0.05)
                logger.warning.assert_called_once()
                self.assertIn("did not finish", logger.warning.call_args[0][0])


if __name__ == "__main__":
    unittest.main()