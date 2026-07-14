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
