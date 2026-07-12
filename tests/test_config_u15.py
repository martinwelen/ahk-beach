# -*- coding: utf-8 -*-
import config


def test_u15_constants_point_at_external_repo():
    assert config.U15_SLUG == "u15"
    assert config.U15_PAGES_BASE == "https://martinwelen.github.io/alingsas-ahus-beach-2026"
    assert config.U15_DIST == "dist-u15"
