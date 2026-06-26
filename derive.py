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


_CAT_RE = re.compile(r"^\s*([PF])(\d+)\s+(\S+)\s*\(f\.\s*\d{4}\)\s*(.*?)\s*$")


def parse_category(category_name):
    """'P15 Classic (f. 2011) Blå' -> {gender, age, rule, suffix}.

    Suffix tolkas ur kategorinamnet (team-entitetens suffix-fält är opålitligt).
    """
    name = category_name or ""
    m = _CAT_RE.match(name)
    if m:
        return {"gender": m.group(1), "age": int(m.group(2)),
                "rule": m.group(3), "suffix": m.group(4)}
    # Fallback: minst kön + ålder ur inledningen.
    g = name[:1] if name[:1] in ("P", "F") else "?"
    am = re.search(r"[PF](\d+)", name)
    rm = re.search(r"\b(Classic|Mini|Beachhandboll)\b", name)
    return {"gender": g, "age": int(am.group(1)) if am else 0,
            "rule": rm.group(1) if rm else "?", "suffix": ""}
