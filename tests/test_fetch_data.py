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
