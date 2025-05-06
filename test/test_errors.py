# **************************************************************************************

# @package        samps
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import unittest

from samps import (
    SerialReadError,
    SerialTimeoutError,
    SerialWriteError,
)

# **************************************************************************************


class TestSerialReadErrorError(unittest.TestCase):
    def test_inheritance(self):
        """Test that SerialReadError inherits from the built-in Exception class."""
        self.assertTrue(issubclass(SerialReadError, Exception))

    def test_error_message(self):
        """Test that the error message is correctly set and retrieved."""
        test_message = "This is a test error message."
        error = SerialReadError(test_message)
        self.assertEqual(str(error), test_message)

    def test_raising_error(self):
        """
        Test that raising SerialReadError with a specific message
        results in that message being available on the exception.
        """
        test_message = "An error occurred."
        with self.assertRaises(SerialReadError) as context:
            raise SerialReadError(test_message)
        self.assertEqual(str(context.exception), test_message)


# **************************************************************************************


class TestSerialTimeoutError(unittest.TestCase):
    def test_inheritance(self):
        """Test that SerialTimeoutError inherits from the built-in Exception class."""
        self.assertTrue(issubclass(SerialTimeoutError, Exception))

    def test_error_message(self):
        """Test that the error message is correctly set and retrieved."""
        test_message = "This is a test error message."
        error = SerialTimeoutError(test_message)
        self.assertEqual(str(error), test_message)

    def test_raising_error(self):
        """
        Test that raising SerialTimeoutError with a specific message
        results in that message being available on the exception.
        """
        test_message = "An error occurred."
        with self.assertRaises(SerialTimeoutError) as context:
            raise SerialTimeoutError(test_message)
        self.assertEqual(str(context.exception), test_message)


# **************************************************************************************


class TestSerialWriteError(unittest.TestCase):
    def test_inheritance(self):
        """Test that SerialWriteError inherits from the built-in Exception class."""
        self.assertTrue(issubclass(SerialWriteError, Exception))

    def test_error_message(self):
        """Test that the error message is correctly set and retrieved."""
        test_message = "This is a test error message."
        error = SerialWriteError(test_message)
        self.assertEqual(str(error), test_message)

    def test_raising_error(self):
        """
        Test that raising SerialWriteError with a specific message
        results in that message being available on the exception.
        """
        test_message = "An error occurred."
        with self.assertRaises(SerialWriteError) as context:
            raise SerialWriteError(test_message)
        self.assertEqual(str(context.exception), test_message)


# **************************************************************************************
