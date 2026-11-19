"""List candidate standard codes for the 21 nodes of the P7 guideline-derived graph.

Public, no-key sources only: EBI OLS4 search API (NCIT, HP, MONDO, EFO) and the NLM Clinical Table
Search Service for LOINC. SNOMED CT and UMLS are not queried (licence required).
Writes the raw hits to a CSV so the final choice in p7_kg_export.py can be checked.
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request

OUT = sys.argv[1]
Q = {
    "HighBP": "hypertension", "HighChol": "hypercholesterolemia", "CholCheck": "cholesterol measurement",
    "BMI": "body mass index", "Smoker": "smoking history", "Stroke": "stroke", "HeartDiseaseorAttack": "coronary heart disease",
    "PhysActivity": "physical activity", "Fruits": "fruit consumption", "Veggies": "vegetable consumption",
    "HvyAlcoholConsump": "heavy drinking", "AnyHealthcare": "health insurance coverage", "NoDocbcCost": "cost barrier to care",
    "GenHlth": "self-rated health", "MentHlth": "mentally unhealthy days", "PhysHlth": "physically unhealthy days",
    "DiffWalk": "difficulty walking", "Sex": "sex", "Age": "age", "Education": "educational attainment", "Income": "income",
}
LOINC_Q = {
    "HighBP": "hypertension", "HighChol": "cholesterol", "CholCheck": "cholesterol serum", "BMI": "body mass index",
    "Smoker": "smoked at least 100 cigarettes", "Stroke": "stroke", "HeartDiseaseorAttack": "coronary heart disease",
    "PhysActivity": "physical activity", "Fruits": "fruit", "Veggies": "vegetables", "HvyAlcoholConsump": "alcoholic drinks",
    "AnyHealthcare": "health insurance", "NoDocbcCost": "could not see doctor because of cost", "GenHlth": "general health",
    "MentHlth": "mental health not good", "PhysHlth": "physical health not good", "DiffWalk": "difficulty walking",
    "Sex": "sex", "Age": "age", "Education": "highest level of education", "Income": "income",
}
UA = {"User-Agent": "research-script/1.0"}


def get(url):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # retry transient network errors
            err = e
            time.sleep(2)
    raise err


rows = []
for node, q in Q.items():
    for onto in ["ncit", "hp", "mondo", "efo"]:
        u = ("https://www.ebi.ac.uk/ols4/api/search?" + urllib.parse.urlencode(
            {"q": q, "ontology": onto, "rows": 4, "fieldList": "iri,label,obo_id,ontology_name,is_defining_ontology"}))
        for d in get(u)["response"]["docs"]:
            rows.append({"node": node, "source": "OLS4:" + onto, "query": q, "code": d.get("obo_id", ""),
                         "label": d.get("label", ""), "iri": d.get("iri", ""), "defining": d.get("is_defining_ontology", "")})
    u = ("https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search?" + urllib.parse.urlencode(
        {"terms": LOINC_Q[node], "df": "LOINC_NUM,LONG_COMMON_NAME", "maxList": 6}))
    for code, name in get(u)[3]:
        rows.append({"node": node, "source": "NLM:loinc", "query": LOINC_Q[node], "code": code, "label": name,
                     "iri": f"https://loinc.org/{code}", "defining": ""})
    print(node, flush=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
