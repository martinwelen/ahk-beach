# tests/test_api.py
# -*- coding: utf-8 -*-
import api


def test_ref_id_extracts_int():
    assert api.ref_id({"href": "Team({id:74384993})"}) == 74384993


def test_ref_id_nameclub():
    assert api.ref_id({"href": "NameClub({id:73383031})"}) == 73383031


def test_ref_id_missing_is_none():
    assert api.ref_id(None) is None
    assert api.ref_id({"href": "no-id-here"}) is None


def test_name_of_prefers_sv_then_en():
    assert api.name_of({"name": {"sv": "Grupp 4", "en": "Group 4"}}) == "Grupp 4"
    assert api.name_of({"name": {"en": "Grupp 4"}}) == "Grupp 4"


def test_name_of_missing_is_empty():
    assert api.name_of({}) == ""


def test_store_get_resolves_href():
    store = {"Team({id:5})": {"id": 5}}
    assert api.store_get(store, {"href": "Team({id:5})"}) == {"id": 5}
    assert api.store_get(store, {"href": "Team({id:9})"}) == {}
