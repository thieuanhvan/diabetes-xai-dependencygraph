"""Which build of this repository is running.

Printed in the header of every run so that a stale checkout announces itself
instead of quietly producing plausible numbers from old code.
"""

REPO_VERSION = "v24"
RELEASED = "2026-07-19"

# Files whose presence check_install.py verifies. A partial extraction is the
# usual cause of a missing entry.
EXPECTED = [
    "src/depgraph/audit.py",
    "src/depgraph/paths.py",
    "src/depgraph/runlog.py",
    "src/depgraph/version.py",
    "analysis/audit_rules.py",
    "analysis/compare_runs.py",
    "analysis/export_edges.py",
    "analysis/test_audit.py",
    "analysis/make_figures.py",
    "analysis/paper_numbers.py",
    "analysis/check_install.py",
    "analysis/tier_sensitivity.py",
]
