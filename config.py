# config.py
# -*- coding: utf-8 -*-
"""Konstanter för ahk-beach. Byt TOURNAMENT_ID nästa år → allt funkar igen."""

TOURNAMENT_ID = "70944382"
CLUB_ID = 73383031                       # NameClub({id:73383031}) = Alingsås HK
CLUB_NAME = "Alingsås HK"

# cupmanager-värd för turneringen. Eventspecifik subdomän – byt om arrangören
# byter (då räcker inte att bara byta TOURNAMENT_ID).
API_HOST = "ahusbeachhandboll.cupmanager.net"

PAGES_HOST = "martinwelen.github.io"
PAGES_PATH = "/ahk-beach"
PAGES_BASE = f"https://{PAGES_HOST}{PAGES_PATH}"

UTC_OFFSET_HOURS = 2                      # Åhus i juli = CEST = UTC+2

CLUB_BLUE = "#1f5fbf"                     # klubbens standardfärg (ensamt lag)

# Färgord (slugifierat) → hex. Används när ALLA lag i en grupp har färgsuffix.
COLOR_MAP = {
    "bla": "#1f5fbf",
    "vit": "#c9c2b4",
    "svart": "#23303a",
    "orange": "#e8730c",
    "gul": "#f2bd0c",
    "rod": "#d22f27",
    "gron": "#2f9e44",
    "rosa": "#e864a4",
}

# Distinkta färger för fallback (siffer-/blandade suffix).
PALETTE = ["#1f5fbf", "#e8730c", "#2f9e44", "#d22f27", "#9c36b5", "#f2bd0c"]
