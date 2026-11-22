from __future__ import annotations

import csv
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo
import requests

LATITUDE = 47.68
LONGITUDE = 20.86
TIMEZONE = "Europe/Budapest"
BACKFILL_START_DATE = "2026-01-01"


def _fetch_open_meteo(url: str, params: dict[str, str | int | float]) -> dict[str, float]:
    """Lekéri az órás tengerszinti légnyomás adatokat az Open-Meteo API-ról."""
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    pressures = hourly.get("pressure_msl", [])

    result: dict[str, float] = {}
    for t_str, p_val in zip(times, pressures):
        if p_val is not None:
            normalized_time = t_str.replace("T", " ")
            result[normalized_time] = float(p_val)
    return result


def fetch_pressure_data() -> None:
    """Letölti és frissíti a Tiszadorogma térségi órás légnyomás adatokat a legnyomas_adatok.csv fájlba."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "legnyomas_adatok.csv")

    records: dict[str, float] = {}

    # Meglévő CSV beolvasása, ha már létezik
    if os.path.isfile(filename):
        with open(filename, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            next(reader, None)  # Fejléc átugrása
            for row in reader:
                if len(row) >= 2 and row[0] and row[1]:
                    try:
                        records[row[0]] = float(row[1].replace(",", "."))
                    except ValueError:
                        continue

    now_bp = datetime.now(ZoneInfo(TIMEZONE))
    now_str = now_bp.strftime("%Y-%m-%d %H:%M")

    try:
        # Ha még nincs (vagy üres) a fájl, letöltjük a múltbeli órás adatokat 2026-01-01-től
        if not records:
            archive_end = (now_bp - timedelta(days=5)).strftime("%Y-%m-%d")
            if archive_end >= BACKFILL_START_DATE:
                archive_data = _fetch_open_meteo(
                    "https://archive-api.open-meteo.com/v1/archive",
                    {
                        "latitude": LATITUDE,
                        "longitude": LONGITUDE,
                        "start_date": BACKFILL_START_DATE,
                        "end_date": archive_end,
                        "hourly": "pressure_msl",
                        "timezone": TIMEZONE,
                    },
                )
                records.update(archive_data)

        # Utolsó 7 nap + mai nap eddigi órás adatai
        recent_data = _fetch_open_meteo(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "past_days": 7,
                "forecast_days": 1,
                "hourly": "pressure_msl",
                "timezone": TIMEZONE,
            },
        )
        for t_str, p_val in recent_data.items():
            if t_str <= now_str:
                records[t_str] = p_val

        # Időrendbe rendezés és mentés
        sorted_items = sorted(records.items(), key=lambda x: x[0])
        with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Időpont", "Légnyomás (hPa)"])
            for t_str, p_val in sorted_items:
                writer.writerow([t_str, f"{p_val:.1f}"])

        print(f"Sikeres légnyomás mentés! Összes órás rekord: {len(sorted_items)} ({filename})")

    except requests.exceptions.RequestException as e:
        print(f"Hálózati hiba történt a légnyomás adatok lekérésekor: {e}")
    except Exception as e:
        print(f"Váratlan hiba történt a légnyomás mentésekor: {e}")


if __name__ == "__main__":
    fetch_pressure_data()
