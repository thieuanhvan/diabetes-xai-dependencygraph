# P7 journal roadmap

Written 2026-07-20, at the point the FAIR submission (v21) was finalised.

Everything below exists because of a concession made to meet the FAIR deadline.
Each concession is recorded in the conference paper itself, so a journal reviewer
will find them whether or not we act. The list is therefore not a wish list; it
is the set of open holes, in the order they should be closed.

Target venue: Artificial Intelligence in Medicine (Q1, NAFOSTED hang II).
Not IJMI (editorial conflict with P4). Not an imaging venue: P7 is
knowledge-graph over tabular survey data, with no images anywhere.

Timeline: FAIR notification 2026-09-15 -> repo goes public -> write in
October and November -> submit after 2026-11-15, so the reward filing lands in
the first 2027 round and stays separate from P4 in the second 2026 round.

---

## 1. Route-aware enforcement

**The hole.** Section VI-A of the conference paper says, in as many words, that
the enforcement experiment needs only the role tier and consults no edge, and
that we claim no generation gain. That sentence is honest and it is also the
single largest opening a reviewer has.

**What to build.** Enforcement that uses the edge set: an indicator `v` may move
if and only if the counterfactual also moves some lever `u` with `(u -> v)` in
`E`. This is a constraint between two features, which is exactly what a flat
role table cannot express, so it converts "the axis needs an edge" from an
auditing claim into a generation claim.

**Experiment.** Three configurations, not two:

1. direction-only (the audited paper's own constraint layer)
2. role-only hard exclusion (what the FAIR paper tests)
3. route-aware conditional enforcement (new)

If 3 preserves validity while still permitting legitimate indicator movement,
that is a new empirical result rather than a reinterpretation of an old one.

**Implementation note.** DiCE has no interface for cross-feature constraints.
Two routes: post-hoc filtering plus regeneration until the constraint holds, or
a custom loss term. The first is simpler and probably sufficient; measure how
many regeneration rounds it costs, because that cost is itself a result.

## 2. Remove the dependence on eight ungraded edges

**The hole.** `lever_in_neighbours("GenHlth", grades="ABC")` returns the empty
set. Every lever-to-indicator route in `K_G` rests on section narrative rather
than on a numbered recommendation. Restricting the graph to graded edges makes
all 323 indicator-touching counterfactuals unsupported, which means the audit is
carried entirely by the weakest evidence in the graph. Section VII discloses
this; disclosure is not a fix.

**What to do.** Look for graded evidence for lever-to-indicator routes outside
ADA sections 5, 8 and 10: USPSTF, NICE, WHO, and meta-analyses on physical
activity and self-rated health, on weight change and physically unhealthy days.
If a graded subgraph can carry the audit on its own, the provenance objection
disappears entirely.

**This is reading, not computing.** It needs no pipeline run and no data, so it
is the one item that can start before the FAIR notification while the MAPR
poster, the thesis resubmission and the FAIR deadline are in the way.

## 3. Rigour a journal will require and a workshop did not

| Conference paper | Journal needs |
| --- | --- |
| edge set built by one author, no agreement statistic | two independent annotators, Cohen's kappa reported |
| no clinical review of tiers or edges | one clinician reviews both |
| BRFSS 2021 only | BRFSS 2015, 2021, 2023 (already harmonised in the sister repos) |
| DiCE random backend only | random, kdtree, genetic |
| XGBoost only | plus logistic regression and random forest |
| validity only | proximity, sparsity, diversity, plausibility, and a proxy for intervention burden |
| five seeds | bootstrap over the cohort, or many more seeds |
| dice-ml version drift found late | pin the version, and report the spread across versions (1,520 -> 1,500 was measured) |

The first two rows are what separates a conference paper from a Q1 paper. The
rest is breadth, and breadth is cheap once the pipeline is parameterised.

## 4. Optional: a direct comparison with ICR

Run against Improvement-Focused Causal Recourse on semi-synthetic structural
causal models, where an SCM *is* identifiable, and show that `K_G` reaches
verdicts close to ICR's without needing one. This answers "why not just use ICR"
definitively and reframes the paper from reporting a failure to proposing a
justified approximation.

Most expensive item on the list, and it can come out badly. Decide only after
item 1 is done.

---

## Do not do

- **Do not restructure the tier scheme** into behavioural lever / modifiable
  clinical state / clinician-mediated target just to satisfy a reviewer.
  Section VII already carries the monotonicity argument: moving BMI out of the
  lever tier can only remove routes, so it raises the unsupported count rather
  than lowering it. Restructuring means rerunning everything for no gain.
- **Do not target an imaging venue.** The supervisor's newer interest is
  knowledge graphs with medical imaging; P7 has no images.

## Administrative

- Items 1 and 3 together are far past any reasonable "30% new content"
  threshold for a conference extension, so that is not a constraint.
- FAIR publishes through IEEE. Read the IEEE policy on extending a conference
  paper to an Elsevier journal, and cite the conference version explicitly.
- **Not yet checked:** the current AIM policy on conference extensions. Read the
  Guide for Authors before writing.
- The repository goes public on 2026-09-15, the notification date. The journal
  version should cite the public repository rather than a generic "reproduction
  package".

## What the conference version already settled

Worth not relitigating:

- the audit rule lives in one place, `src/depgraph/audit.py`, with both the edge rule
  and the role rule implemented so the difference can be reported
- every figure comes from one environment, dice-ml 0.12, verified identical
  between `run_audit_dump.py` and `run_seed_sweep.py` by `compare_runs.py`
- `analysis/paper_numbers.py` prints every figure the manuscript quotes, so
  renumbering after any rerun is one command
- the complete 26-edge table is generated from the edge module, so the paper and
  the code cannot drift apart
