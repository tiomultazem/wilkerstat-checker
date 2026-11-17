"""
Proxy module untuk s02_repair_geotagging.
"""
import os
import sys

_curr_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_curr_dir)
_legacy_mod = os.path.join(_parent_dir, "00 - module")

if _legacy_mod not in sys.path:
    sys.path.insert(0, _legacy_mod)

from s02_repair_geotagging import *

