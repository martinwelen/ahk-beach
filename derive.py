# derive.py
# -*- coding: utf-8 -*-
"""Rena härledningsfunktioner: slug, kategoritolkning, färgregel. Ingen I/O."""

import re

_SV = str.maketrans({"å": "a", "ä": "a", "ö": "o", "é": "e",
                     "Å": "a", "Ä": "a", "Ö": "o", "É": "e"})


def slugify(s):
    s = (s or "").translate(_SV).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
