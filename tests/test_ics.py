# -*- coding: utf-8 -*-
import build_ics


def test_vevent_has_stable_uid_and_times():
    m = {"slug": "u14-p-bla", "mots": "Lugi HF", "grupp": "Grupp 2",
         "start_ms": 1783585800000, "bana": 7, "hemma": "Alingsås HK Blå",
         "borta": "Lugi HF", "hb": "Hemma", "tid": "10:30"}
    lines = build_ics.vevent(m, label="U14", duration_min=11, seq=1, dtstamp="20260101T000000Z")
    text = "\n".join(lines)
    assert "BEGIN:VEVENT" in text and "END:VEVENT" in text
    assert "UID:u14-p-bla-vs-lugi-hf-grupp-2@" in text
    assert "DTSTART:20260709T083000Z" in text     # 10:30 CEST = 08:30 UTC
    assert "DTEND:20260709T084100Z" in text        # +11 min


def test_fold_wraps_long_lines():
    long = "X" * 200
    out = build_ics.fold(long)
    assert all(len(l.encode("utf-8")) <= 75 for l in out.split("\r\n "))
