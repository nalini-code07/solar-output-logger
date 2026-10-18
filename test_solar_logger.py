import os
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from solar_logger import (
    fetch_today,
    create_table,
    save_output,
    get_all_rows,
    format_row,
    main,
)


class TestSolarLogger(unittest.TestCase):

    def test_fetch_today(self):
        mock_response = Mock()
        mock_response.json.return_value = {
            "date": "2026-10-18",
            "energy_kwh": 25.5,
        }
        mock_response.raise_for_status.return_value = None

        with patch("solar_logger.requests.get", return_value=mock_response):
            result = fetch_today("https://example.com/solar")

        self.assertEqual(result, ("2026-10-18", 25.5))

    def test_fetch_today_request_error(self):
        with patch(
            "solar_logger.requests.get",
            side_effect=requests.RequestException("API error"),
        ):
            with self.assertRaises(requests.RequestException):
                fetch_today("https://example.com/solar")

    def test_create_table(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            conn = sqlite3.connect(db_path)

            try:
                create_table(conn)
                result = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='daily_output'"
                ).fetchone()

                self.assertIsNotNone(result)
            finally:
                conn.close()

    def test_save_and_get_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")

            save_output(db_path, "2026-10-18", 25.5)
            rows = get_all_rows(db_path)

            self.assertEqual(rows, [("2026-10-18", 25.5)])

    def test_duplicate_date_updates_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")

            save_output(db_path, "2026-10-18", 25.5)
            save_output(db_path, "2026-10-18", 30.0)

            rows = get_all_rows(db_path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0], ("2026-10-18", 30.0))

    def test_get_all_rows_sorted_by_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")

            save_output(db_path, "2026-10-19", 30.0)
            save_output(db_path, "2026-10-17", 20.0)

            rows = get_all_rows(db_path)

            self.assertEqual(
                rows,
                [
                    ("2026-10-17", 20.0),
                    ("2026-10-19", 30.0),
                ],
            )

    def test_format_row(self):
        result = format_row("2026-10-18", 25.5)

        self.assertEqual(result, "2026-10-18: 25.5 kWh")

    def test_main_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")

            with (
                patch("solar_logger.DB_PATH", db_path),
                patch(
                    "solar_logger.fetch_today",
                    return_value=("2026-10-18", 25.5),
                ),
                patch("builtins.print") as mock_print,
            ):
                result = main(["solar_logger.py"])

            self.assertEqual(result, 0)
            mock_print.assert_called_with("2026-10-18: 25.5 kWh")

    def test_main_request_error(self):
        with patch(
            "solar_logger.fetch_today",
            side_effect=requests.RequestException("API error"),
        ), patch("builtins.print") as mock_print:
            result = main(["solar_logger.py"])

        self.assertEqual(result, 1)
        mock_print.assert_called_once()

        self.assertIn(
            "Could not fetch solar data:",
            mock_print.call_args[0][0],
        )


if __name__ == "__main__":
    unittest.main()
    