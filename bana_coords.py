# bana_coords.py
# -*- coding: utf-8 -*-
"""Pixelpositioner (mitten av varje bana) på karta.png, manuellt uppmätta.
Görs upplösningsoberoende (andel av bildmåtten) vid inbäddning i build_apps."""

IMG_W, IMG_H = 842, 1191

BANA_PX = {
    1: (513, 507), 2: (509, 392), 3: (561, 396), 4: (557, 305), 5: (687, 234),
    6: (767, 248), 7: (700, 158), 8: (778, 172), 9: (789, 92), 10: (610, 184),
    11: (335, 560), 12: (335, 475), 13: (383, 381), 14: (276, 655), 15: (265, 555),
    16: (229, 490), 17: (203, 555), 18: (142, 555), 19: (73, 548),
}


def bana_fractions():
    """{bana: [x_frac, y_frac]} i [0,1] för %-positionering i appen."""
    return {n: [round(x / IMG_W, 4), round(y / IMG_H, 4)] for n, (x, y) in BANA_PX.items()}
