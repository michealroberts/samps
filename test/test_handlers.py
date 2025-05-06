# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import unittest
from time import sleep

from samps.handlers import ReadTimeoutHandler

# **************************************************************************************


class TestReadTimeoutHandler(unittest.TestCase):
    def test_no_timeout(self):
        handler = ReadTimeoutHandler(None)
        handler.start()
        self.assertFalse(handler.has_expired())
        self.assertIsNone(handler.remaining())
        self.assertIn("timeout=None", repr(handler))

    def test_timeout_not_expired(self):
        handler = ReadTimeoutHandler(2.0)
        handler.start()
        self.assertFalse(handler.has_expired())
        remaining = handler.remaining()
        self.assertTrue(0.0 < remaining <= 2.0)

    def test_timeout_expired(self):
        handler = ReadTimeoutHandler(0.5)
        handler.start()
        sleep(0.6)
        self.assertTrue(handler.has_expired())
        self.assertEqual(handler.remaining(), 0.0)

    def test_reset(self):
        handler = ReadTimeoutHandler(0.1)
        handler.start()
        sleep(0.2)
        self.assertTrue(handler.has_expired())
        handler.reset()
        self.assertFalse(handler.has_expired())
        self.assertTrue(0.0 < handler.remaining() <= 0.1)

    def test_start(self):
        handler = ReadTimeoutHandler(0.1)
        handler.start()
        self.assertFalse(handler.has_expired())


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
