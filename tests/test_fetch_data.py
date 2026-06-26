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
