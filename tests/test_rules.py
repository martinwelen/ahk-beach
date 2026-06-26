# tests/test_rules.py
# -*- coding: utf-8 -*-
import rules


def test_classic_profile():
    p = rules.rule_profile("Classic")
    assert p == {"duration_min": 11, "has_results": True,
                 "has_tables": True, "has_playoffs": True}


def test_mini_profile_schedule_only():
    p = rules.rule_profile("Mini")
    assert p == {"duration_min": 11, "has_results": False,
                 "has_tables": False, "has_playoffs": False}


def test_unknown_rule_defaults_to_full_for_future_formats():
    # Internationellt/okänt: behåll data så den finns när renderaren byggs (Plan 2).
    p = rules.rule_profile("Beachhandboll")
    assert p["has_results"] is True and p["has_tables"] is True
    assert p["duration_min"] == 11
