# -*- coding: utf-8 -*-
import re

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


def test_live_poll_window_bridges_robot_persistence_lag():
    # Regression: liveState (slut-siffran) lever bara i minnet och töms vid refresh.
    # Efter reload pollas en avslutad match bara medan den ligger i tidsfönstret.
    # Robotens persisterade slutresultat kan dröja ~25-30 min (matchslut + missad
    # cykel + CI-körtid), så fönstret MÅSTE sträcka sig väl bortom det – annars blir
    # kortet blankt (varken live-"Slut" eller sparat resultat) i glappet.
    t = template.TEMPLATE
    m = re.search(r"POLL_GRACE_MS\s*=\s*(\d+)\s*\*\s*60000", t)
    assert m, "hittar inte POLL_GRACE_MS-konstanten"
    grace_min = int(m.group(1))
    assert grace_min >= 30, f"grace {grace_min} min för kort för robotlatensen (~30 min)"
    # pollWindow måste använda konstanten (inte en hårdkodad kort grace).
    assert "m.ms + DUR + POLL_GRACE_MS" in t


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
    assert 'fetch("sched.json", {cache:"no-store"})' in t
    assert "setInterval(refreshData, 60000)" in t


def test_background_refresh_bypasses_http_cache():
    # Regression: GitHub Pages serverar sched.json med Cache-Control: max-age=600.
    # refreshData MÅSTE hämta med {cache:"no-store"}, annars kan bakgrunds-
    # uppdateringen läsa en inaktuell (cachead) sched.json och RADERA ett redan
    # visat resultat tills HTTP-cachen löper ut (~10 min). En manuell reload
    # revaliderar index.html och "återfår" resultatet – exakt det observerade felet.
    assert 'fetch("sched.json", {cache:"no-store"})' in template.TEMPLATE


def test_map_markers_markup():
    t = template.TEMPLATE
    assert 'id="mk-inline"' in t               # markörcontainer i inline-kartan
    assert 'id="mapzoom-stage"' in t            # stage-wrapper runt helskärmsbilden
    assert 'id="mk-zoom"' in t                  # markörcontainer i helskärmsläget
    assert 'id="mapinfo"' in t                  # infochip under helskärmsläget
    assert "mapmarkers" in t                    # CSS-klassen finns


def test_zoom_transforms_stage_not_img():
    t = template.TEMPLATE
    assert 'stage.style.transform=' in t        # transform sätts på stage (inte img)
    assert 'img.style.transform=' not in t      # img transformeras inte direkt
    assert 'stage.style.willChange="transform"' in t  # willChange på stage


def test_map_markers_logic():
    t = template.TEMPLATE
    assert "function mapMarkers(" in t
    assert "function showMapInfo(" in t
    assert 'state(m,now)==="live"' in t
    assert "BANA_XY[" in t
    assert "mapMarkers();" in t


def test_klubbtalt_marker():
    t = template.TEMPLATE
    assert "const KLUBBTALT" in t
    assert "function showTentInfo(" in t
    assert "Klubbtält" in t
    assert "mk tent" in t
    assert "Alingsas_HK_logo.svg" in t
