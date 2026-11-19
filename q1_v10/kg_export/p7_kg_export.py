"""Export the P7 guideline-derived knowledge graph with provenance (CSV + Turtle).

Nodes: the 21 BRFSS survey features, with role and direction (depgraph.nodes) and standard codes chosen
from public, no-key sources (EBI OLS4 for NCIt, HPO, MONDO, EFO; NLM Clinical Table Search Service for
LOINC); candidate hits are in kg_code_candidates_20261111.csv. SNOMED CT and UMLS are not assigned
(licence required). A code names the closest standard concept, not the survey item itself.
Edges: 26 ADA assertions (depgraph.edges; paraphrase only, ADA text is not reproduced) plus the agreed
edges of the two independent extractions of the Ministry of Health (Decision 5481) and WHO HEARTS-D
documents (quotation of at most twelve words, original language). Each edge carries a heuristic
evidence-support score under the linear mapping of the article.
Usage: python -I p7_kg_export.py <out_dir>
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.edges import EDGES  # noqa: E402
from depgraph.nodes import DIRECTION, TIER  # noqa: E402

OUT = Path(sys.argv[1])
X5 = Path("D:/20-study/uit/research/diabetesxai/paper7/killtest_x5/extraction")
SCORE = {"A": 0.9, "B": 0.7, "C": 0.5, "E": 0.3, "explicit": 0.6, "narrative": 0.2}

LABEL = {
    "HighBP": "High blood pressure (told by a health professional)",
    "HighChol": "High blood cholesterol (told by a health professional)",
    "CholCheck": "Cholesterol check within five years",
    "BMI": "Body mass index",
    "Smoker": "Smoked at least 100 cigarettes in lifetime",
    "Stroke": "Ever told had a stroke",
    "HeartDiseaseorAttack": "Coronary heart disease or myocardial infarction",
    "PhysActivity": "Physical activity in the past 30 days outside work",
    "Fruits": "Fruit consumption at least once per day",
    "Veggies": "Vegetable consumption at least once per day",
    "HvyAlcoholConsump": "Heavy alcohol consumption",
    "AnyHealthcare": "Any health care coverage",
    "NoDocbcCost": "Could not see a doctor in the past year because of cost",
    "GenHlth": "Self-rated general health (1 excellent to 5 poor)",
    "MentHlth": "Days of poor mental health in the past 30 days",
    "PhysHlth": "Days of poor physical health in the past 30 days",
    "DiffWalk": "Serious difficulty walking or climbing stairs",
    "Sex": "Sex",
    "Age": "Age group",
    "Education": "Education level",
    "Income": "Household income category",
}

# Chosen codes (prefix:id). Empty string = no adequate concept found in the public sources queried.
CODES = {
    "HighBP": {"ncit": "NCIT:C3117", "hpo": "HP:0000822"},
    "HighChol": {"ncit": "NCIT:C37967", "hpo": "HP:0003124", "loinc": "LOINC:58292-4"},
    "CholCheck": {"ncit": "NCIT:C105586", "efo": "EFO:0004574"},
    "BMI": {"ncit": "NCIT:C16358", "efo": "EFO:0004340", "loinc": "LOINC:39156-5"},
    "Smoker": {"ncit": "NCIT:C29719", "efo": "EFO:0006527", "loinc": "LOINC:63581-3"},
    "Stroke": {"ncit": "NCIT:C3390", "hpo": "HP:0001297", "mondo": "MONDO:0005098", "loinc": "LOINC:78925-5"},
    "HeartDiseaseorAttack": {"ncit": "NCIT:C26732", "hpo": "HP:0001658", "mondo": "MONDO:0005010"},
    "PhysActivity": {"ncit": "NCIT:C17708", "efo": "EFO:0003940"},
    "Fruits": {"ncit": "NCIT:C172465"},
    "Veggies": {"ncit": "NCIT:C172466"},
    "HvyAlcoholConsump": {"ncit": "NCIT:C126384", "efo": "EFO:0004329"},
    "AnyHealthcare": {"ncit": "NCIT:C157356", "loinc": "LOINC:63513-6"},
    "NoDocbcCost": {"loinc": "LOINC:99552-2"},
    "GenHlth": {"efo": "EFO:0004778", "loinc": "LOINC:66576-0"},
    "MentHlth": {"loinc": "LOINC:66578-6"},
    "PhysHlth": {"loinc": "LOINC:66577-8"},
    "DiffWalk": {"ncit": "NCIT:C198638", "loinc": "LOINC:69859-7"},
    "Sex": {"ncit": "NCIT:C28421", "loinc": "LOINC:46098-0"},
    "Age": {"ncit": "NCIT:C25150", "efo": "EFO:0000246", "loinc": "LOINC:30525-0"},
    "Education": {"ncit": "NCIT:C17953", "efo": "EFO:0011015", "loinc": "LOINC:82589-3"},
    "Income": {"ncit": "NCIT:C41150", "efo": "EFO:0009695", "loinc": "LOINC:108248-6"},
}

NOTE = {
    "HighBP": "No LOINC survey item for 'ever told high blood pressure' was found in the NLM LOINC search.",
    "CholCheck": "Codes name the cholesterol test; the survey item records whether a check took place within five years.",
    "HeartDiseaseorAttack": "The item merges coronary heart disease and myocardial infarction; one code is given for each.",
    "Fruits": "Codes name dietary fruit intake; the survey item is a binary daily-consumption indicator.",
    "Veggies": "Codes name dietary vegetable intake; the survey item is a binary daily-consumption indicator.",
    "HvyAlcoholConsump": "NCIt 'Heavy Drinker'; BRFSS uses sex-specific weekly thresholds.",
    "NoDocbcCost": "No NCIt, HPO, MONDO or EFO concept for a cost barrier to care was found.",
    "MentHlth": "CDC HRQOL-4 item; no ontology concept for days of poor mental health was found.",
    "PhysHlth": "CDC HRQOL-4 item; no ontology concept for days of poor physical health was found.",
}
for _f in CODES:  # SNOMED CT and UMLS need a licence and were not queried
    NOTE[_f] = (NOTE.get(_f, "") + " SNOMED CT and UMLS codes not assigned (licence required).").strip()

AUTH = {
    "ADA2026": ("American Diabetes Association, Standards of Care in Diabetes 2026",
                "https://doi.org/10.2337/dc26-SINT", "single reader (conference paper)"),
    "MoH5481": ("Ministry of Health of Vietnam, Decision 5481/QD-BYT (2020)", "", "two independent LLM-agent extractions; agreed edges only"),
    "WHO_HEARTSD": ("World Health Organization, HEARTS-D (2020), WHO/UCN/NCD/20.1", "", "two independent LLM-agent extractions; agreed edges only"),
}
ADA_SEC_DOI = {"S5": "https://doi.org/10.2337/dc26-S005", "S8": "https://doi.org/10.2337/dc26-S008",
               "S10": "https://doi.org/10.2337/dc26-S010"}


def ada_edges():
    rows = []
    for e in EDGES:
        strength = "narrative" if e.grade in ("-", "narrative") else "graded"
        grade = "" if strength == "narrative" else e.grade
        sec = e.source.split(",")[1].strip()
        rows.append({"subject": e.src, "predicate": "recognisedRouteTo", "object": e.dst, "authority": "ADA2026",
                     "location": e.source, "document_link": ADA_SEC_DOI.get(sec, ""), "strength": strength,
                     "grade": grade, "support_score": SCORE[grade or "narrative"], "quotation": "",
                     "paraphrase": e.gloss, "quotation_language": "",
                     "extraction": AUTH["ADA2026"][2]})
    return rows


def agreed(prefix, auth):
    a = list(csv.DictReader(open(X5 / f"{prefix}_extractor_A.csv", encoding="utf-8")))
    b = list(csv.DictReader(open(X5 / f"{prefix}_extractor_B.csv", encoding="utf-8")))
    keys_b = {(r["src"], r["dst"]) for r in b}
    rows = []
    for r in a:
        if (r["src"], r["dst"]) not in keys_b:
            continue
        rows.append({"subject": r["src"], "predicate": "recognisedRouteTo", "object": r["dst"], "authority": auth,
                     "location": f"p. {r['page']}, {r['section']}", "document_link": AUTH[auth][1],
                     "strength": r["strength"], "grade": r["grade"], "support_score": SCORE[r["grade"] or r["strength"]],
                     "quotation": r["evidence_words"], "paraphrase": "",
                     "quotation_language": "vi" if auth == "MoH5481" else "en", "extraction": AUTH[auth][2]})
    return rows


def ttl_lit(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    edges = ada_edges() + agreed("byt5481", "MoH5481") + agreed("who_heartsd", "WHO_HEARTSD") + agreed("nice_ng28", "NICE_NG28")
    nodes = []
    for f in TIER:
        c = CODES.get(f, {})
        nodes.append({"node": f, "label": LABEL[f], "role": TIER[f], "direction": DIRECTION[f],
                      "ncit": c.get("ncit", ""), "hpo": c.get("hpo", ""), "mondo": c.get("mondo", ""),
                      "efo": c.get("efo", ""), "loinc": c.get("loinc", ""),
                      "snomed_ct": "", "umls_cui": "", "code_note": NOTE.get(f, "")})
    with open(OUT / "dependency_graph_nodes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(nodes[0]))
        w.writeheader()
        w.writerows(nodes)
    for i, e in enumerate(edges, 1):
        e["edge_id"] = f"e{i:02d}"
    cols = ["edge_id"] + [k for k in edges[0] if k != "edge_id"]
    with open(OUT / "dependency_graph_triples.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(edges)

    pre = {"ncit": "http://purl.obolibrary.org/obo/NCIT_", "hpo": "http://purl.obolibrary.org/obo/HP_",
           "mondo": "http://purl.obolibrary.org/obo/MONDO_", "efo": "http://www.ebi.ac.uk/efo/EFO_",
           "loinc": "https://loinc.org/"}
    L = ["@prefix kg: <https://github.com/thieuanhvan/diabetes-xai-dependencygraph/kg#> .",
         "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
         "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
         "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
         "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .", "",
         "# Guideline dependency graph of the diabetes recourse audit, in knowledge-graph form. An edge states that a guideline names acting on the",
         "# subject as a recognised route to changing the object. It encodes no effect size and no causal model.",
         "kg:recognisedRouteTo a rdf:Property ; rdfs:label \"recognised route to\" .", ""]
    for n in nodes:
        L.append(f"kg:{n['node']} a kg:SurveyFeature ; rdfs:label {ttl_lit(n['label'])} ;")
        L.append(f"    kg:role kg:{n['role']} ; kg:direction {ttl_lit(n['direction'])} ;")
        for k in ["ncit", "hpo", "mondo", "efo", "loinc"]:
            for code in filter(None, n[k].split(";")):
                code = code.strip()
                local = code.split(":", 1)[1]
                L.append(f"    skos:closeMatch <{pre[k]}{local}> ;")
        if n["code_note"]:
            L.append(f"    rdfs:comment {ttl_lit(n['code_note'])} ;")
        L[-1] = L[-1].rstrip(" ;") + " ."
    L.append("")
    for e in edges:
        L.append(f"kg:{e['subject']} kg:recognisedRouteTo kg:{e['object']} .")
    L.append("")
    for e in edges:
        L.append(f"kg:{e['edge_id']} a rdf:Statement ; rdf:subject kg:{e['subject']} ; "
                 f"rdf:predicate kg:recognisedRouteTo ; rdf:object kg:{e['object']} ;")
        L.append(f"    kg:authority kg:{e['authority']} ; kg:location {ttl_lit(e['location'])} ;")
        L.append(f"    kg:strength {ttl_lit(e['strength'])} ; kg:grade {ttl_lit(e['grade'])} ;")
        L.append(f"    kg:supportScore \"{e['support_score']}\"^^xsd:decimal ;")
        if e["quotation"]:
            L.append(f"    kg:quotation {ttl_lit(e['quotation'])}@{e['quotation_language']} ;")
        if e["paraphrase"]:
            L.append(f"    kg:paraphrase {ttl_lit(e['paraphrase'])}@en ;")
        if e["document_link"]:
            L.append(f"    kg:documentLink <{e['document_link']}> ;")
        L.append(f"    kg:extraction {ttl_lit(e['extraction'])} .")
    L.append("")
    for k, (name, link, _) in AUTH.items():
        L.append(f"kg:{k} rdfs:label {ttl_lit(name)} ." if not link else
                 f"kg:{k} rdfs:label {ttl_lit(name)} ; rdfs:seeAlso <{link}> .")
    (OUT / "dependency_graph.ttl").write_text("\n".join(L) + "\n", encoding="utf-8")
    coded = sum(1 for n in nodes if any(n[k] for k in ["ncit", "hpo", "mondo", "efo", "loinc"]))
    print(f"nodes {len(nodes)}, coded {coded}; edges {len(edges)} "
          f"({sum(e['authority'] == 'ADA2026' for e in edges)} ADA), pairs {len({(e['subject'], e['object']) for e in edges})}")
    for k in ["ncit", "hpo", "mondo", "efo", "loinc"]:
        print(k, sum(1 for n in nodes if n[k]))


if __name__ == "__main__":
    main()
