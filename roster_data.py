# roster_data.py
# -*- coding: utf-8 -*-
"""Spelartrupper per Alingsås-lag (statisk källa; cupmanager saknar spelardata).

Nycklar = ahk-beach team-slugs: u{ålder}-{kön}-{färg}. Per spelare: namn (krav),
valfritt nr (tröjnummer), pos ("MV"/"UT"), smek (smeknamn). Lag utan publicerad
trupp: tom lista. Trupp-fliken göms automatiskt tills minst ett lag har spelare.
"""

rosters = {
    "u15-p-bla": [
        {"namn": "Oskar Viklund", "pos": "UT"},
        {"namn": "Alfred Lindblad", "nr": 72, "pos": "MV", "smek": "Affe"},
        {"namn": "Maurits Fridberg", "nr": 67, "pos": "UT", "smek": "Marre"},
        {"namn": "Filip Holmgren", "pos": "UT"},
        {"namn": "Terje Hegge", "nr": 17, "pos": "UT"},
        {"namn": "Theodor Kangas", "nr": 91, "pos": "MV"},
        {"namn": "Silas Klintefelt", "nr": 38, "pos": "UT"},
    ],
    "u15-p-orange": [
        {"namn": "Olle Laas", "nr": 35, "pos": "MV"},
        {"namn": "Hjalmar Oscarsson", "nr": 28, "pos": "UT", "smek": "Hjalle"},
        {"namn": "Alexander Westberg", "nr": 27, "pos": "UT"},
        {"namn": "Theodor Herou", "nr": 56, "pos": "UT"},
        {"namn": "Fabian Mattsson", "nr": 13, "pos": "UT", "smek": "Fabbe"},
        {"namn": "Frank Jannerland", "nr": 1, "pos": "MV"},
    ],
    "u15-p-vit": [
        {"namn": "Samuel Welén", "nr": 11, "pos": "MV"},
        {"namn": "Ture Thunberg", "nr": 9, "pos": "UT"},
        {"namn": "Sixten Herbertsson", "nr": 31, "pos": "UT"},
        {"namn": "Filip Larsson", "nr": 95, "pos": "MV"},
        {"namn": "Liam Bergaoui", "nr": 8, "pos": "UT"},
        {"namn": "Love Jönsson", "nr": 3, "pos": "UT"},
    ],
    "u15-f-bla": [],
    "u15-f-gul": [],
    "u15-f-vit": [],
}
