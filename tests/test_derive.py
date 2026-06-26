# tests/test_derive.py
# -*- coding: utf-8 -*-
import derive


def test_slugify_lowercases_and_hyphenates():
    assert derive.slugify("Lag Blå") == "lag-bla"


def test_slugify_maps_swedish_vowels():
    assert derive.slugify("Gulö Ärt") == "gulo-art"


def test_slugify_strips_non_alnum_and_collapses():
    assert derive.slugify("AHK  2 / B") == "ahk-2-b"


def test_slugify_empty_is_empty():
    assert derive.slugify("") == ""


def test_parse_category_classic_with_color():
    p = derive.parse_category("P15 Classic (f. 2011) Blå")
    assert p == {"gender": "P", "age": 15, "rule": "Classic", "suffix": "Blå"}


def test_parse_category_mini_numeric_suffix():
    p = derive.parse_category("F11 Mini (f. 2015) 1")
    assert p == {"gender": "F", "age": 11, "rule": "Mini", "suffix": "1"}


def test_parse_category_no_suffix():
    p = derive.parse_category("P10 Mini (f. 2016)")
    assert p == {"gender": "P", "age": 10, "rule": "Mini", "suffix": ""}


def test_parse_category_multiword_suffix():
    p = derive.parse_category("P8 Mini (f. 2018) Lag Blå")
    assert p == {"gender": "P", "age": 8, "rule": "Mini", "suffix": "Lag Blå"}


def test_parse_category_unknown_rule_falls_back():
    p = derive.parse_category("P14 Beachhandboll (f. 2012) 2")
    assert p["gender"] == "P" and p["age"] == 14 and p["suffix"] == "2"
    assert p["rule"] == "Beachhandboll"
