# build_ics.py
# -*- coding: utf-8 -*-
"""iCalendar (.ics) per lag, per åldersgrupp, ur data.json. Ported från
alingsas-ahus-beach-2026/build_ics.py."""

import os
import json
from datetime import datetime, timezone

import config

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(ROOT, "data.json")
SKIP = {"u15"}
PRODID = "-//Alingsas HK//Ahus Beach Handboll//SV"
SOURCE_NOTE = "Källa: ahusbeachhandboll.cupmanager.net"

# === VERBATIM-kopierade hjälpare från live build_ics.py: ===
#   ms_to_utc, slug_ascii, esc, fold


def ms_to_utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slug_ascii(s):
    import unicodedata, re
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def esc(t):
    return (t.replace("\\", "\\\\").replace(";", "\\;")
             .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, start, limit = [], 0, 75
    while start < len(raw):
        end = min(start + limit, len(raw))
        while end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        parts.append(raw[start:end]); start = end; limit = 74
    return parts[0].decode("utf-8") + "".join("\r\n " + p.decode("utf-8") for p in parts[1:])


def uid_for(m):
    base = f"{m['slug']}-vs-{slug_ascii(m['mots'])}-{slug_ascii(str(m['grupp']))}"
    return f"{base}@ahusbeach.cupmanager.net"


def vevent(m, label, duration_min, seq, dtstamp):
    dur_ms = duration_min * 60 * 1000
    dtstart = ms_to_utc(m["start_ms"])
    dtend = ms_to_utc(m["start_ms"] + dur_ms)
    summary = f"{label}: {m['hemma']} – {m['borta']}"
    location = f"Bana {m['bana']}, Åhus Beach Handboll, Åhus"
    desc = (f"{m['grupp']}\\nAlingsås spelar {m['hb'].lower()}lag mot {m['mots']}.\\n"
            f"Avspark {m['tid']} (lokal tid).\\n{SOURCE_NOTE}")
    return ["BEGIN:VEVENT", f"UID:{uid_for(m)}", f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}", f"DTEND:{dtend}", f"SUMMARY:{esc(summary)}",
            f"LOCATION:{esc(location)}", f"DESCRIPTION:{desc}", f"SEQUENCE:{seq}",
            f"LAST-MODIFIED:{dtstamp}", "STATUS:CONFIRMED", "TRANSP:OPAQUE", "END:VEVENT"]


def build_calendar(rows, cal_name, cal_desc, label, duration_min, seq, dtstamp):
    rows = sorted(rows, key=lambda m: (m["start_ms"], str(m["bana"])))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(cal_name)}",
             "X-WR-TIMEZONE:Europe/Stockholm", f"X-WR-CALDESC:{esc(cal_desc)}",
             "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    for m in rows:
        lines += vevent(m, label, duration_min, seq, dtstamp)
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


def main():
    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    seq = int(data.get("meta", {}).get("seq", 1))
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for age_slug, g in data.get("groups", {}).items():
        if age_slug in SKIP:
            continue
        out_dir = os.path.join(ROOT, age_slug, "ics")
        os.makedirs(out_dir, exist_ok=True)
        dur = g["profile"]["duration_min"]
        by_team = {}
        for m in g["matches"]:
            by_team.setdefault(m["slug"], []).append(m)
        with open(os.path.join(out_dir, "alla.ics"), "w", encoding="utf-8", newline="") as f:
            f.write(build_calendar(g["matches"], f"Alingsås HK {g['label']} (alla) – Åhus Beach",
                                   f"Alla lag i {g['label']}. {SOURCE_NOTE}",
                                   g["label"], dur, seq, dtstamp))
        for t in g["teams"]:
            with open(os.path.join(out_dir, f"{t['slug']}.ics"), "w",
                      encoding="utf-8", newline="") as f:
                f.write(build_calendar(by_team.get(t["slug"], []),
                                       f"{t['team_name']} – Åhus Beach",
                                       f"{g['label']}. {SOURCE_NOTE}",
                                       g["label"], dur, seq, dtstamp))
    print("iCal genererad per åldersgrupp")


if __name__ == "__main__":
    main()
