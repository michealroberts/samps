# **************************************************************************************

# @package        astral-uv-python-package-template
# @license        MIT License Copyright (c) 2025 Michael J. Roberts

# **************************************************************************************

import unittest
from typing import Tuple

from astral_uv_python_package_template import __license__, __version__

# **************************************************************************************


def parse_semantic_version(value: str) -> Tuple[int, int, int]:
    # Split off anything after the first dash (e.g. '-rc.1', '-beta', etc.)
    version = value.split("-", 1)[0]

    # Split the main part on '.' and map them to integers
    major, minor, patch = version.split(".")

    return (int(major), int(minor), int(patch))


# **************************************************************************************


class TestBase(unittest.TestCase):
    def test_license(self) -> None:
        self.assertEqual(__license__, "MIT")

    def test_version(self):
        major, minor, patch = parse_semantic_version(__version__)
        # Assert that major, minor and patch should all be valid integers:
        self.assertIsInstance(major, int)
        self.assertIsInstance(minor, int)
        self.assertIsInstance(patch, int)


# **************************************************************************************

if __name__ == "__main__":
    unittest.main()

# **************************************************************************************
