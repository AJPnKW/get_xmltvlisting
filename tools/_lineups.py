#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_lineups.py

Version: 1.0.0
Purpose:
- Single source of truth for xmltvlistings.com lineup IDs and labels used by this repo.
- Prevent drift between workflow, scripts, and documentation.

Rule:
- Do not duplicate lineup IDs in workflow files, config files, or multiple scripts.
- Import from this module instead.
"""

from __future__ import annotations

PROVIDER_NAME = "xmltvlistings.com"
API_KEY_ENV = "API_XMLTVLISTING_KEY"
DEFAULT_DAYS = 7

ACTIVE_LINEUPS: tuple[dict[str, str], ...] = (
    {"id": "10270", "name": "Rogers - Toronto, ON", "label": "Rogers_Toronto_ON_CA"},
    {"id": "10269", "name": "Telus Optik TV - Vancouver, BC", "label": "Telus_Optik_Vancouver_BC_CA"},
    {"id": "10271", "name": "Xfinity - Chicago Area 1, 4 & 5, IL - Digital", "label": "Xfinity_Chicago_IL_US"},
    {"id": "10273", "name": "Verizon FIOS - New York, NY", "label": "Verizon_FIOS_NewYork_NY_US"},
    {"id": "10272", "name": "Broadcast - Los Angeles, CA", "label": "Broadcast_LosAngeles_CA_US"},
)

LINEUP_LABELS: dict[str, str] = {item["id"]: item["label"] for item in ACTIVE_LINEUPS}
LINEUP_IDS: list[str] = [item["id"] for item in ACTIVE_LINEUPS]
LINEUP_NAME_BY_ID: dict[str, str] = {item["id"]: item["name"] for item in ACTIVE_LINEUPS}
