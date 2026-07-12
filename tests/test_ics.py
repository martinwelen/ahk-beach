# -*- coding: utf-8 -*-
import json
import build_ics as _bi
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


def test_u15_ics_filename_maps_to_legacy_name():
    assert build_ics.u15_ics_name("u15-p-bla") == "alingsas-p15-bla.ics"
    assert build_ics.u15_ics_name("u15-f-gul") == "alingsas-f15-gul.ics"
    assert build_ics.u15_ics_name("u15-p-orange") == "alingsas-p15-orange.ics"


def test_main_writes_u15_with_legacy_names(tmp_path, monkeypatch):
    data = {"meta": {"seq": 1}, "groups": {"u15": {
        "label": "U15", "profile": {"duration_min": 11},
        "teams": [{"slug": "u15-p-bla", "team_name": "Alingsås HK P15 Blå"}],
        "matches": [{"slug": "u15-p-bla", "mots": "Lugi", "grupp": "G1",
                     "start_ms": 1783585800000, "bana": 1, "hemma": "Blå",
                     "borta": "Lugi", "hb": "Hemma", "tid": "10:30"}]}}}
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(_bi, "ROOT", str(tmp_path))
    monkeypatch.setattr(_bi, "DATA_JSON", str(tmp_path / "data.json"))
    _bi.main()
    ics_dir = tmp_path / "dist-u15" / "ics"
    assert (ics_dir / "alingsas-alla.ics").exists()
    assert (ics_dir / "alingsas-p15-bla.ics").exists()
    assert not (tmp_path / "u15").exists()
