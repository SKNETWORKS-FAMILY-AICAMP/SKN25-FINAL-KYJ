from __future__ import annotations

import unittest

from foldmind_ai_core.core.domain.models.confidence import Confidence
from foldmind_ai_core.shared.validation import InvalidInputError


class ConfidenceDomainTests(unittest.TestCase):
    def test_confidence_rejects_out_of_range_values(self) -> None:
        confidence = Confidence(1.0)

        self.assertEqual(confidence.value, 1.0)
        with self.assertRaises(InvalidInputError):
            Confidence(1.1)
        with self.assertRaises(InvalidInputError):
            Confidence(float("nan"))


if __name__ == "__main__":
    unittest.main()
