from __future__ import annotations

import unittest

from rent_pulse.ingestion.parser import parse_dataset_bytes


class ParserTests(unittest.TestCase):
    def test_parse_csv_bytes(self) -> None:
        rows = parse_dataset_bytes(b"id,name\n1,Ada\n2,Grace\n", "csv")
        self.assertEqual(rows[0]["id"], "1")
        self.assertEqual(rows[1]["name"], "Grace")

    def test_parse_json_list(self) -> None:
        rows = parse_dataset_bytes(b'[{"id": 1, "name": "Ada"}]', "json")
        self.assertEqual(rows, [{"id": 1, "name": "Ada"}])


if __name__ == "__main__":
    unittest.main()
