import os
import sqlite3
import sys

import requests

API_URL = "https://api.example.com/solar?date=today"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "solar.db")


def fetch_today(url):
    """Ask the API for today's output and return (date, energy_kwh)."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data["date"], float(data["energy_kwh"])


def create_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS daily_output (date TEXT PRIMARY KEY, energy_kwh REAL)"
    )


def save_output(db_path, date, energy_kwh):
    """Store one day's output. If the date is already there, update it."""
    conn = sqlite3.connect(db_path)
    try:
        create_table(conn)
        cur = conn.cursor()
        cur.execute(
            "UPDATE daily_output SET energy_kwh = ? WHERE date = ?",
            (energy_kwh, date),
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO daily_output (date, energy_kwh) VALUES (?, ?)",
                (date, energy_kwh),
            )
        conn.commit()
    finally:
        conn.close()


def get_all_rows(db_path):
    conn = sqlite3.connect(db_path)
    try:
        create_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT date, energy_kwh FROM daily_output ORDER BY date")
        return cur.fetchall()
    finally:
        conn.close()


def format_row(date, energy_kwh):
    return f"{date}: {energy_kwh} kWh"


def main(argv):
    url = argv[1] if len(argv) > 1 else API_URL
    try:
        date, energy_kwh = fetch_today(url)
    except requests.RequestException as error:
        print(f"Could not fetch solar data: {error}")
        return 1
    save_output(DB_PATH, date, energy_kwh)
    for row_date, row_energy in get_all_rows(DB_PATH):
        print(format_row(row_date, row_energy))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
