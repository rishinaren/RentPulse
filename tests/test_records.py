from __future__ import annotations

import unittest

from rent_pulse.config import DatasetSource
from rent_pulse.records import build_raw_records, stable_hash


class RecordTests(unittest.TestCase):
    def test_stable_hash_is_order_independent(self) -> None:
        self.assertEqual(stable_hash({"b": 2, "a": 1}), stable_hash({"a": 1, "b": 2}))

    def test_build_raw_records_uses_primary_key(self) -> None:
        source = DatasetSource(
            name="listing_snapshots",
            dataset_type="listings",
            url="file://data/sample/listing_snapshots.csv",
            primary_key=("listing_id", "snapshot_date"),
        )
        records = build_raw_records(
            [{"listing_id": "rp-1", "snapshot_date": "2026-04-30", "rent": "3000"}],
            source,
            run_id="test",
        )
        self.assertEqual(records[0]["source_row_id"], "rp-1|2026-04-30")
        self.assertEqual(records[0]["dataset_type"], "listings")


if __name__ == "__main__":
    unittest.main()
