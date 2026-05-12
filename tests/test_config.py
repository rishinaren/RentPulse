from __future__ import annotations

import unittest

from rent_pulse.config import RentPulseConfig, load_sources


class ConfigTests(unittest.TestCase):
    def test_load_sources_includes_required_datasets(self) -> None:
        config = RentPulseConfig.from_env()
        source_names = {source.name for source in load_sources(config)}
        self.assertIn("zillow_zori_zip", source_names)
        self.assertIn("nyc_dob_approved_permits", source_names)
        self.assertIn("mta_subway_stations", source_names)
        self.assertIn("listing_snapshots", source_names)

    def test_listing_source_uses_file_seed_by_default(self) -> None:
        config = RentPulseConfig.from_env()
        listing_source = next(source for source in load_sources(config) if source.name == "listing_snapshots")
        self.assertTrue(listing_source.resolved_url().startswith("file://"))


if __name__ == "__main__":
    unittest.main()
