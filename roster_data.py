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
        {"namn": "Alfred Lindblad", "pos": "MV", "smek": "Affe"},
        {"namn": "Maurits Fridberg", "pos": "UT", "smek": "Marre"},
        {"namn": "Filip Holmgren", "pos": "UT"},
        {"namn": "Terje Hegge", "pos": "UT"},
        {"namn": "Theodor Kangas"},
        {"namn": "Silas Klintefelt"},
    ],
    "u15-p-orange": [
        {"namn": "Olle Laas", "pos": "MV"},
        {"namn": "Hjalmar Oscarsson", "pos": "UT", "smek": "Hjalle"},
        {"namn": "Alexander Westberg", "pos": "UT"},
        {"namn": "Theodor Herou", "pos": "UT"},
        {"namn": "Fabian Mattsson", "pos": "UT", "smek": "Fabbe"},
        {"namn": "Frank Jannerland", "pos": "UT"},
    ],
    "u15-p-vit": [
        {"namn": "Samuel Welén", "pos": "MV"},
        {"namn": "Ture Thunberg", "pos": "UT"},
        {"namn": "Sixten Herbertsson", "pos": "UT"},
        {"namn": "Filip Larsson", "pos": "UT"},
        {"namn": "Liam Bergaoui", "pos": "UT"},
        {"namn": "Love Jönsson", "pos": "UT"},
    ],
    "u15-f-bla": [],
    "u15-f-gul": [],
    "u15-f-vit": [],
}
