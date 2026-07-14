# -*- coding: utf-8 -*-
import template


def test_match_card_has_mid_and_live_slot_and_video():
    t = template.TEMPLATE
    assert 'data-mid="${m.id||' in t            # kortet bär match-id
    assert 'class="lscore"' in t                 # plats för livescore-badge
    assert 'class="vidlink"' in t                # videolänk (bana 1-2)
    assert 'm.video' in t                        # renderas villkorat på video
