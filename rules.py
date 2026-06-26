# rules.py
# -*- coding: utf-8 -*-
"""Format-profil per regeltyp. Driver vad datalagret tar med och (i Plan 2) hur
det renderas. Mini = schema bara (inga tabeller/slutspel). Internationellt
behandlas som 'full' tills set/shootout-renderaren byggs (Plan 2)."""

_PROFILES = {
    "Classic": {"duration_min": 11, "has_results": True,
                "has_tables": True, "has_playoffs": True},
    "Mini":    {"duration_min": 11, "has_results": False,
                "has_tables": False, "has_playoffs": False},
}

_DEFAULT = {"duration_min": 11, "has_results": True,
            "has_tables": True, "has_playoffs": True}


def rule_profile(rule):
    return dict(_PROFILES.get(rule, _DEFAULT))
