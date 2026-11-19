"""Sensitivity (P7 journal review, round 2): Smoker records ever having smoked 100 cigarettes, so it cannot be
lowered by the patient. Lock it (immutable) and remove it from the lever tier, then rerun the exhaustive search.
Writes tag _nosmk_exh (picked up by p7_exh_bootstrap.py)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # v10 shadow: python -I omits the script dir
import sys

import p7_cross_exhaustive as E
from p7_cross_p4pipeline import FT, FeatureSpec, Mutability
from depgraph.nodes import TIER

s = FT.FEATURE_TAXONOMY["Smoker"]
FT.FEATURE_TAXONOMY["Smoker"] = FeatureSpec("Smoker", Mutability.IMMUTABLE, s.value_range, s.semantic_label + " [locked: ever-smoked]")
TIER["Smoker"] = "immutable"
if "--tag" not in sys.argv:
    sys.argv += ["--tag", "_nosmk_exh"]
E.main()
