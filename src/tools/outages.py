"""
Power outage checker for Elektrodistribucija MK.
Uses the public API directly — no browser needed.
"""

import requests
from datetime import datetime, date

API_URL = "https://portal-api.elektrodistribucija.mk/DSO/Prekini/ZemiPrekini"

# Map of region names (Macedonian) to kecId numbers
REGIONS = {
    "скопје": [10, 38, 39],
    "тетово": [11],
    "охрид": [12],
    "битола": [13],
    "прилеп": [14],
    "велес": [15],
    "куманово": [16],
    "штип": [17],
    "струмица": [18],
    "гостивар": [19],
    "кичево": [21],
    "струга": [22],
    "кавадарци": [25],
    "гевгелија": [28],
    "кочани": [30],
    "делчево": [32],
    "кратово": [35],
}


def get_outages(region: str = None, for_date: str = None) -> list[dict]:
    """
    Fetch power outages, optionally filtered by region name and/or date (YYYY-MM-DD).
    Returns a list of outage dicts.
    """
    r = requests.get(
        API_URL,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://elektrodistribucija.mk/"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()

    # Filter by date
    if for_date:
        target = date.fromisoformat(for_date)
        data = [
            o for o in data
            if datetime.fromisoformat(o["pocetok"]).date() == target
            or datetime.fromisoformat(o["kraj"]).date() == target
        ]

    # Filter by region
    if region:
        key = region.lower().strip()
        kec_ids = None
        for name, ids in REGIONS.items():
            if key in name or name in key:
                kec_ids = ids
                break
        if kec_ids:
            data = [o for o in data if o.get("kecId") in kec_ids]

    # Deduplicate by prekinID + nasMesto
    seen = set()
    unique = []
    for o in data:
        key = (o["prekinID"], o["nasMesto"])
        if key not in seen:
            seen.add(key)
            unique.append(o)

    return unique


def format_outages(outages: list[dict]) -> str:
    if not outages:
        return "No planned power outages found."

    lines = [f"** {len(outages)} planned outage(s) found:**\n"]
    for o in outages:
        start = datetime.fromisoformat(o["pocetok"]).strftime("%d %b %Y %H:%M")
        end = datetime.fromisoformat(o["kraj"]).strftime("%H:%M")
        lines.append(
            f"*{o['nasMesto']}*\n"
            f"   {o['adresa']}\n"
            f"   {start} - {end}\n"
            f"   Type: {o['tipPrekin']}\n"
        )
    return "\n".join(lines)
