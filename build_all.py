# build_all.py
# -*- coding: utf-8 -*-
"""Kör hela kedjan lokalt/i CI: data → standings → appar → ics → hubb."""

import sys
import fetch_data
import fetch_standings
import build_apps
import build_ics
import build_hub


def main():
    fetch_data.main()
    fetch_standings.main()
    build_apps.main()
    build_ics.main()
    build_hub.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
