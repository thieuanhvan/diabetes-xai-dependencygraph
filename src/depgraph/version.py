"""Which build of this repository is running.

Printed in the header of every run so that a stale checkout announces itself
instead of quietly producing plausible numbers from old code.
"""
REPO_VERSION = "v25"
RELEASED = "2026-08-05"

# Files introduced after v12. check_install.py verifies these exist, which is
# the cheapest way to catch an archive that was never extracted.
EXPECTED = [
    "src/depgraph/audit.py",
    "src/depgraph/paths.py",
    "src/depgraph/runlog.py",
    "src/depgraph/version.py",
    "analysis/audit_rules.py",
    "analysis/compare_runs.py",
    "analysis/export_edges.py",
    "analysis/test_audit.py",
    "analysis/make_fig1_kg.py",
    "analysis/make_fig2_route.py",
    "analysis/export_edges_tex.py",
    "analysis/paper_numbers.py",
    "analysis/check_install.py",
    "analysis/tier_sensitivity.py",
]
