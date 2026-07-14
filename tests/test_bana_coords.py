# -*- coding: utf-8 -*-
import bana_coords as bc


def test_all_19_courts_present():
    assert set(bc.BANA_PX) == set(range(1, 20))


def test_fractions_in_range_and_correct():
    fr = bc.bana_fractions()
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in fr.values())
    assert fr[9] == [round(789 / 842, 4), round(92 / 1191, 4)]
    assert len(fr) == 19


def test_klubbtalt_fraction():
    fr = bc.klubbtalt_fraction()
    assert fr == [round(428 / 842, 4), round(776 / 1191, 4)]
