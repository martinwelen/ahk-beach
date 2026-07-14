# tests/test_fetch_data.py
# -*- coding: utf-8 -*-
import fetch_data
import config


def _team(tid, category_name, club_id=config.CLUB_ID):
    return {
        "__typename": "Team", "id": tid,
        "club": {"href": f"NameClub({{id:{club_id}}})"},
        "name": {"clubName": f"Alingsås HK {category_name.split(') ')[-1]}",
                 "categoryName": category_name},
    }


def test_registry_filters_to_club_only():
    store = {
        "Team({id:1})": _team(1, "P15 Classic (f. 2011) Blå"),
        "Team({id:2})": _team(2, "P15 Classic (f. 2011) Vit", club_id=999),
    }
    reg = fetch_data.build_team_registry(store)
    assert [t["id"] for t in reg] == [1]


def test_registry_derives_fields_and_age_slug():
    store = {"Team({id:1})": _team(1, "P15 Classic (f. 2011) Blå")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["gender"] == "P" and t["age"] == 15 and t["rule"] == "Classic"
    assert t["suffix"] == "Blå" and t["age_slug"] == "u15"
    assert t["slug"] == "u15-p-bla"


def test_registry_assigns_colors_per_age_group():
    store = {
        "Team({id:1})": _team(1, "P15 Classic (f. 2011) Blå"),
        "Team({id:2})": _team(2, "P15 Classic (f. 2011) Orange"),
        "Team({id:3})": _team(3, "P15 Classic (f. 2011) VIT"),
    }
    reg = {t["id"]: t for t in fetch_data.build_team_registry(store)}
    assert reg[1]["color"] == config.COLOR_MAP["bla"]
    assert reg[2]["color"] == config.COLOR_MAP["orange"]
    assert reg[3]["color"] == config.COLOR_MAP["vit"]


def test_registry_single_team_age_group_is_club_blue():
    store = {"Team({id:9})": _team(9, "P18 Classic (f. 2008) 1")}
    t = fetch_data.build_team_registry(store)[0]
    assert t["color"] == config.CLUB_BLUE


def _match(mid, start_ms, bana, home_actor, away_actor, division_name,
           home_team_id, away_team_id, result=None):
    return {
        "__typename": "Match", "id": mid, "start": start_ms,
        "arena": {"href": f"Arena({{id:{mid}}})"},
        "home": {"href": f"H({mid})"}, "away": {"href": f"A({mid})"},
        "division": {"href": f"D({mid})"}, "result": {"href": f"R({mid})"},
        "_arena": {"completeName": f"Bana {bana}"},
        "_home": {"name": {"en": home_actor}, "team": {"href": f"Team({{id:{home_team_id}}})"}},
        "_away": {"name": {"en": away_actor}, "team": {"href": f"Team({{id:{away_team_id}}})"}},
        "_division": {"name": {"sv": division_name}},
        "_result": result or {"finished": False},
    }


def _store_for_match(m):
    """Lägg refererade entiteter i storen under sina href:ar."""
    mid = m["id"]
    return {
        f"Arena({{id:{mid}}})": m["_arena"],
        f"H({mid})": m["_home"], f"A({mid})": m["_away"],
        f"D({mid})": m["_division"], f"R({mid})": m["_result"],
        f"Match({{id:{mid}}})": m,
    }


def test_normalize_match_basic_fields():
    m = _match(100, 1783585800000, 7, "Alingsås HK Blå", "Lugi HF 3",
               "Grupp 2", home_team_id=1, away_team_id=50)
    store = _store_for_match(m)
    reg_by_id = {1: {"id": 1, "slug": "u15-p-bla", "age_slug": "u15",
                     "gender": "P", "rule": "Classic", "color": "#1f5fbf"}}
    nm = fetch_data.normalize_match(m, store, reg_by_id)
    assert nm["age_slug"] == "u15"
    assert nm["slug"] == "u15-p-bla"
    assert nm["bana"] == 7
    assert nm["hemma"] == "Alingsås HK Blå"
    assert nm["borta"] == "Lugi HF 3"
    assert nm["hb"] == "Hemma"
    assert nm["mots"] == "Lugi HF 3"
    assert nm["grupp"] == "Grupp 2"
    assert nm["tid"] == "10:30"          # 1783585800000 ms = 08:30 UTC = 10:30 CEST
    assert nm["result"] is None


def test_normalize_match_away_side_and_result():
    res = {"finished": True, "homeGoals": 9, "awayGoals": 14}
    m = _match(101, 1783585800000, 3, "IFK Kristianstad 2", "Alingsås HK Blå",
               "Grupp 2", home_team_id=50, away_team_id=1, result=res)
    store = _store_for_match(m)
    reg_by_id = {1: {"id": 1, "slug": "u15-p-bla", "age_slug": "u15",
                     "gender": "P", "rule": "Classic", "color": "#1f5fbf"}}
    nm = fetch_data.normalize_match(m, store, reg_by_id)
    assert nm["hb"] == "Borta"
    assert nm["mots"] == "IFK Kristianstad 2"
    assert nm["result"] == {"hg": 9, "ag": 14}


def test_bucket_by_age_group_groups_and_sorts():
    reg = [
        {"id": 1, "slug": "u15-p-bla", "age_slug": "u15", "age": 15,
         "gender": "P", "rule": "Classic", "team_name": "Alingsås HK Blå",
         "suffix": "Blå", "color": "#1f5fbf"},
    ]
    m_late = _match(2, 1783589400000, 8, "Alingsås HK Blå", "X", "Grupp 2", 1, 50)
    m_early = _match(1, 1783585800000, 7, "Alingsås HK Blå", "Y", "Grupp 2", 1, 50)
    store = {}
    store.update(_store_for_match(m_late))
    store.update(_store_for_match(m_early))
    groups = fetch_data.bucket_by_age_group(reg, [m_early, m_late], store)
    assert "u15" in groups
    g = groups["u15"]
    assert g["age"] == 15 and g["label"] == "U15" and g["rule"] == "Classic"
    assert [t["id"] for t in g["teams"]] == [1]
    assert [mm["start_ms"] for mm in g["matches"]] == [1783585800000, 1783589400000]


def test_bucket_sorts_courts_numerically_not_lexicographically():
    reg = [{"id": 1, "slug": "u15-p-bla", "age_slug": "u15", "age": 15,
            "gender": "P", "rule": "Classic", "team_name": "Alingsås HK Blå",
            "suffix": "Blå", "color": "#1f5fbf"}]
    # Samma starttid, banorna 2 och 10 → 2 ska komma före 10 (inte "10" < "2").
    m10 = _match(1, 1783585800000, 10, "Alingsås HK Blå", "X", "Grupp 2", 1, 50)
    m2 = _match(2, 1783585800000, 2, "Alingsås HK Blå", "Y", "Grupp 2", 1, 50)
    store = {}
    store.update(_store_for_match(m10))
    store.update(_store_for_match(m2))
    groups = fetch_data.bucket_by_age_group(reg, [m10, m2], store)
    assert [mm["bana"] for mm in groups["u15"]["matches"]] == [2, 10]


def test_normalize_match_returns_none_for_non_club_match():
    m = _match(200, 1783585800000, 5, "Lugi HF", "IFK Kristianstad", "Grupp 1", 99, 88)
    store = _store_for_match(m)
    reg_by_id = {1: {"id": 1, "slug": "u15-p-bla", "age_slug": "u15",
                     "gender": "P", "rule": "Classic", "color": "#1f5fbf"}}
    assert fetch_data.normalize_match(m, store, reg_by_id) is None


import json
import os


def test_assemble_shapes_doc_with_meta_and_groups():
    groups = {"u15": {"age": 15, "label": "U15", "rule": "Classic",
                      "profile": {"duration_min": 11}, "teams": [], "matches": []}}
    doc = fetch_data.assemble(groups, generated="2026-06-26T00:00:00Z", seq=1)
    assert doc["meta"]["club_id"] == config.CLUB_ID
    assert doc["meta"]["seq"] == 1
    assert "data_hash" in doc["meta"]
    assert doc["groups"]["u15"]["label"] == "U15"


def test_data_hash_stable_regardless_of_meta():
    groups = {"u15": {"age": 15, "label": "U15", "rule": "Classic",
                      "profile": {}, "teams": [], "matches": []}}
    a = fetch_data.assemble(groups, generated="2026-01-01T00:00:00Z", seq=1)
    b = fetch_data.assemble(groups, generated="2026-09-09T00:00:00Z", seq=2)
    assert a["meta"]["data_hash"] == b["meta"]["data_hash"]


def test_write_if_changed_writes_then_skips(tmp_path):
    groups = {"u15": {"age": 15, "label": "U15", "rule": "Classic",
                      "profile": {}, "teams": [], "matches": []}}
    path = os.path.join(tmp_path, "data.json")
    wrote1 = fetch_data.write_if_changed(groups, path,
                                         generated="2026-06-26T00:00:00Z", seq=1)
    wrote2 = fetch_data.write_if_changed(groups, path,
                                         generated="2026-06-27T00:00:00Z", seq=2)
    assert wrote1 is True and wrote2 is False
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["meta"]["seq"] == 1     # andra körningen skrev inte över


def test_normalize_match_returns_none_for_untimed_match():
    m = _match(300, 1783585800000, 5, "Alingsås HK Blå", "X", "Grupp 2", 1, 50)
    m["start"] = None                        # ännu ej tidssatt (slutspels-TBD)
    store = _store_for_match(m)
    reg_by_id = {1: {"id": 1, "slug": "u15-p-bla", "age_slug": "u15",
                     "gender": "P", "rule": "Classic", "color": "#1f5fbf"}}
    assert fetch_data.normalize_match(m, store, reg_by_id) is None


def test_normalize_match_includes_cupmanager_id():
    import fetch_data, api
    e = {"id": 81848529, "home": {"href": "h"}, "away": {"href": "a"},
         "start": 1784034000000, "division": {}, "arena": {}, "result": {}}
    reg = {7: {"id": 7, "age_slug": "u15", "slug": "u15-p-bla", "gender": "P",
               "rule": "Classic", "color": "#1f5fbf", "age": 15}}
    orig = (api.ref_id, api.name_of, api.store_get)
    api.store_get = lambda s, r: {"team": {"href": "Team({id:7})"}}
    api.ref_id = lambda n: 7
    api.name_of = lambda x: "Lag"
    try:
        m = fetch_data.normalize_match(e, {}, reg)
    finally:
        api.ref_id, api.name_of, api.store_get = orig
    assert m is not None
    assert m["id"] == 81848529


def test_video_url_extracts_external_link():
    import fetch_data, api
    orig = api.call
    api.call = lambda q: {"responses": {"Video({id:1})": {"entity": {
        "__typename": "Video", "externalLink": "https://solidsport.com/x"}}}}
    try:
        assert fetch_data._video_url(123) == "https://solidsport.com/x"
        api.call = lambda q: {"responses": {}}
        assert fetch_data._video_url(123) is None
        assert fetch_data._video_url(None) is None
    finally:
        api.call = orig


def test_normalize_match_sets_video_only_for_courts_1_2():
    import fetch_data, api
    reg = {7: {"id": 7, "age_slug": "u15", "slug": "u15-p-bla", "gender": "P",
               "rule": "Classic", "color": "#1f5fbf", "age": 15}}
    orig = (api.ref_id, api.name_of, api.store_get, api.call)
    api.ref_id = lambda n: 7
    api.name_of = lambda x: "Lag"
    api.call = lambda q: {"responses": {"v": {"entity": {
        "__typename": "Video", "externalLink": "https://solidsport.com/x"}}}}
    def mk(bana):
        api.store_get = lambda s, r: {"completeName": f"Bana {bana}", "team": {"href": "t"}}
        return fetch_data.normalize_match(
            {"id": 1, "home": {"href": "h"}, "away": {"href": "a"}, "start": 1784034000000,
             "division": {}, "arena": {}, "result": {}}, {}, reg)
    try:
        assert mk(2)["video"] == "https://solidsport.com/x"   # bana 2 → video
        assert mk(15)["video"] is None                        # annan bana → ingen
    finally:
        api.ref_id, api.name_of, api.store_get, api.call = orig


def test_hash_includes_id_and_video():
    import copy
    import fetch_data
    base = {"u15": {"rule": "Classic", "teams": [{"id": 1}],
            "matches": [{"slug": "s", "start_ms": 1, "bana": 2, "hemma": "a",
                         "borta": "b", "grupp": "g", "result": None,
                         "id": 10, "video": None}]}}
    h1 = fetch_data._hash_groups(base)
    b2 = copy.deepcopy(base); b2["u15"]["matches"][0]["video"] = "https://x"
    b3 = copy.deepcopy(base); b3["u15"]["matches"][0]["id"] = 99
    assert fetch_data._hash_groups(b2) != h1   # video ändrar hashen → tvingar omskrivning
    assert fetch_data._hash_groups(b3) != h1   # id ändrar hashen


def test_runda_sv_mapping():
    import fetch_data as f
    assert f._runda_sv("Final") == "Final"
    assert f._runda_sv("1/2 Final") == "Semifinal"
    assert f._runda_sv("Semi final") == "Semifinal"      # verkligt källnamn
    assert f._runda_sv("1/4 Final") == "Kvartsfinal"
    assert f._runda_sv("Quarter final") == "Kvartsfinal"
    assert f._runda_sv("1/8 Final") == "1/8-final"
    assert f._runda_sv("1/16 Final") == "1/16-final"
    assert f._runda_sv(None) is None
    assert f._runda_sv("Bronsmatch") == "Bronsmatch"  # okänt → råtext


def test_round_name_resolves_swedish():
    import fetch_data, api
    orig = api.call
    api.call = lambda q: {"responses": {"r": {"entity": {
        "__typename": "Match$RoundName", "name": {"en": "1/2 Final"}}}}}
    try:
        assert fetch_data._round_name(5) == "Semifinal"
        api.call = lambda q: {"responses": {}}
        assert fetch_data._round_name(5) is None
    finally:
        api.call = orig


def test_normalize_sets_runda_only_for_slutspel():
    import fetch_data, api
    reg = {7: {"id": 7, "age_slug": "u12", "slug": "u12-p-bla", "gender": "P",
               "rule": "Classic", "color": "#1f5fbf", "age": 12}}
    orig = (api.ref_id, api.name_of, api.store_get, api.call)
    api.ref_id = lambda n: 7
    api.call = lambda q: {"responses": {"r": {"entity": {
        "__typename": "Match$RoundName", "name": {"en": "1/8 Final"}}}}}
    def mk(grupp):
        api.name_of = lambda x: grupp
        api.store_get = lambda s, r: {"completeName": "Bana 5", "team": {"href": "t"}}
        return fetch_data.normalize_match(
            {"id": 1, "home": {"href": "h"}, "away": {"href": "a"}, "start": 1784034000000,
             "division": {}, "arena": {}, "result": {}}, {}, reg)
    try:
        assert mk("A-Slutspel")["runda"] == "1/8-final"
        assert mk("Grupp 1")["runda"] is None
    finally:
        api.ref_id, api.name_of, api.store_get, api.call = orig


def test_hash_includes_runda():
    import copy, fetch_data
    base = {"u12": {"rule": "Classic", "teams": [{"id": 1}],
            "matches": [{"slug": "s", "start_ms": 1, "bana": 2, "hemma": "a",
                         "borta": "b", "grupp": "A-Slutspel", "result": None,
                         "id": 10, "video": None, "runda": "Semifinal"}]}}
    h1 = fetch_data._hash_groups(base)
    b2 = copy.deepcopy(base); b2["u12"]["matches"][0]["runda"] = "Final"
    assert fetch_data._hash_groups(b2) != h1
