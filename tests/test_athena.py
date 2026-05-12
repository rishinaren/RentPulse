from __future__ import annotations

import unittest

from rent_pulse.aws.athena import AthenaValidator


class AthenaValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = AthenaValidator.__new__(AthenaValidator)

    def test_required_dataset_presence_fails_when_missing_sources(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "loaded 5 of 6 required datasets"):
            self.validator._validate_result_rows("required_dataset_presence", [{"loaded_dataset_count": "5"}])

    def test_duplicate_record_hashes_fails_when_rows_returned(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "duplicate_record_hashes failed"):
            self.validator._validate_result_rows(
                "duplicate_record_hashes",
                [{"dataset_name": "listing_snapshots", "record_hash": "abc123"}],
            )

    def test_listing_snapshot_price_quality_fails_on_invalid_rents(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "2 listing snapshots have invalid rent"):
            self.validator._validate_result_rows(
                "listing_snapshot_price_quality",
                [{"invalid_listing_rent_count": "2"}],
            )

    def test_validation_passes_for_clean_duplicate_result(self) -> None:
        self.assertEqual(self.validator._validate_result_rows("duplicate_record_hashes", []), "passed")


if __name__ == "__main__":
    unittest.main()
