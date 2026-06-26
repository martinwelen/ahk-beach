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
