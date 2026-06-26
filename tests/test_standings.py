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
