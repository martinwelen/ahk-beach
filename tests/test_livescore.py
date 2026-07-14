# -*- coding: utf-8 -*-
import template


def test_template_has_livescore_poll_module():
    t = template.TEMPLATE
    assert "MatchResult(" in t
    assert "encodeURIComponent" in t
    assert "visibilitychange" in t
    assert "homeGoals" in t and "awayGoals" in t
    assert "setInterval(pollWindow" in t


def test_render_reapplies_livescore_after_rerender():
    assert "reapplyLive()" in template.TEMPLATE


def test_match_card_has_mid_and_live_slot_and_video():
    t = template.TEMPLATE
    assert 'data-mid="${m.id||' in t            # kortet bär match-id
    assert 'class="lscore"' in t                 # plats för livescore-badge
    assert 'class="vidlink"' in t                # videolänk (bana 1-2)
    assert 'm.video' in t                        # renderas villkorat på video


def test_template_has_multihero_logic():
    t = template.TEMPLATE
    assert 'filter(m=>state(m,now)==="live")' in t
    assert "featured" in t
    assert "herolist" in t
    assert "m.ms===" in t or "m.ms ===" in t


def test_livestate_declared_before_initial_render():
    # Regression: liveState (const) måste initialiseras före första render()-anropet,
    # annars kastar reapplyLive() ett TDZ ReferenceError och hela appen dör vid load.
    t = template.TEMPLATE
    assert t.index("const liveState") < t.index("\nrender();")


def test_video_link_is_scheme_checked_and_encoded():
    t = template.TEMPLATE
    assert "function videoLink(" in t
    assert "/^https:" in t          # blockerar javascript:-URI:er
    assert "encodeURI(" in t        # neutraliserar citattecken i href


def test_card_shows_playoff_round():
    t = template.TEMPLATE
    assert 'class="rundachip"' in t
    assert 'm.runda' in t
    assert 'hm.runda' in t


def test_livescore_shows_final_score_before_robot():
    # Latensfix: klienten visar slutsiffran från MatchResult (finished) direkt,
    # men bara om robotens .score inte redan finns (undviker dubbel).
    t = template.TEMPLATE
    assert "s.finished" in t
    assert "Slut " in t
    assert 'querySelector(".score")' in t


def test_background_data_refresh():
    t = template.TEMPLATE
    assert "let MATCHES = __DATA__;" in t       # ombytbar för refresh
    assert "let STANDINGS = __STANDINGS__;" in t
    assert "function refreshData(" in t
    assert 'fetch("sched.json")' in t
    assert "setInterval(refreshData, 60000)" in t
