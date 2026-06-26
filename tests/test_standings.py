# tests/test_standings.py
# -*- coding: utf-8 -*-
import fetch_standings as fs


def test_winner_side_home_away_none():
    assert fs.winner_side({"finished": True, "homeGoals": 14, "awayGoals": 11}) == "home"
    assert fs.winner_side({"finished": True, "homeGoals": 9, "awayGoals": 12}) == "away"
    assert fs.winner_side({"finished": False, "homeGoals": 0, "awayGoals": 0}) is None
    assert fs.winner_side({"finished": True, "homeGoals": 10, "awayGoals": 10}) is None


def test_table_row_normalizes_and_flags_club():
    row = {
        "name": {"sv": "Alingsås HK Blå"}, "team": {"href": "Team({id:1})"},
        "played": 3, "won": 2, "tied": 0, "lost": 1,
        "goalsWon": 40, "goalsLost": 33, "points": 4,
        "targetStage": {"href": "Stage({categoryId:1,stageId:70944379,tournamentId:2})"},
    }
    out = fs.table_row(row, club_team_ids={1}, tier_by_stage={70944379: "A-Slutspel"})
    assert out["team_id"] == 1 and out["is_alingsas"] is True
    assert out["diff"] == 7 and out["points"] == 4 and out["tier"] == "A-Slutspel"


def test_bucket_groups_by_age_slug_skips_mini():
    groups_in = [
        {"age_slug": "u15", "rule": "Classic", "name": "Grupp 2", "rows": []},
        {"age_slug": "u10", "rule": "Mini", "name": "Grupp 1", "rows": []},
    ]
    out = fs.bucket_groups(groups_in)
    assert "u15" in out and "u10" not in out      # Mini har inga tabeller


def _bm_store(mid, home_name, away_name, hid, aid, rnd, bana, result):
    return {
        f"M({mid})": {"__typename": "Match", "id": mid, "start": 1000 + mid,
                      "home": {"href": f"HO({mid})"}, "away": {"href": f"AW({mid})"},
                      "arena": {"href": f"AR({mid})"}, "round": {"href": f"RN({mid})"},
                      "result": {"href": f"RE({mid})"}},
        f"HO({mid})": {"name": {"sv": home_name}, "team": {"href": f"Team({{id:{hid}}})"}},
        f"AW({mid})": {"name": {"sv": away_name}, "team": {"href": f"Team({{id:{aid}}})"}},
        f"AR({mid})": {"fieldName": f"Bana {bana}"},
        f"RN({mid})": {"name": {"sv": rnd}},
        f"RE({mid})": result,
    }


def test_bracket_match_normalizes_and_flags_winner():
    st = _bm_store(1, "Alingsås HK Blå", "Lugi HF", 10, 20, "Semifinal", 7,
                   {"finished": True, "homeGoals": 12, "awayGoals": 9})
    m = fs.bracket_match(st["M(1)"], st, club_ids={10})
    assert m["round"] == "Semifinal" and m["bana"] == 7
    assert m["home"]["label"] == "Alingsås HK Blå" and m["home"]["is_alingsas"] is True
    assert m["home"]["goals"] == 12 and m["away"]["goals"] == 9
    assert m["winner"] == "home"


def test_group_rounds_orders_by_first_start():
    ms = [{"round": "Final", "start": 200, "id": 2},
          {"round": "Semifinal", "start": 100, "id": 1}]
    rounds = fs.group_rounds(ms)
    assert [r["name"] for r in rounds] == ["Semifinal", "Final"]
    assert "_first" not in rounds[0]


def test_discover_divisions_tags_age_slug():
    store = {
        "Match({id:1})": {"__typename": "Match",
                          "home": {"href": "HO1"}, "away": {"href": "AW1"},
                          "division": {"href": "Div({id:500})"}},
        "HO1": {"team": {"href": "Team({id:10})"}},
        "AW1": {"team": {"href": "Team({id:99})"}},
        "Div({id:500})": {"name": {"sv": "Grupp 2"},
                          "category": {"href": "Category({categoryId:70,tournamentId:2})"}},
    }
    reg_by_id = {10: {"age_slug": "u15", "rule": "Classic", "gender": "P", "age": 15}}
    out = fs.discover_divisions(store, reg_by_id)
    assert out[500] == {"age_slug": "u15", "rule": "Classic", "klass": "P15",
                        "name": "Grupp 2", "category": "70"}
