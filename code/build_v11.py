"""Canonical renderer for the reader-first v11 D04 synthetic dashboard.

Run this LAST, after generating inputs and building feedback_loop_metrics.json.
Earlier builders are retained for historical investigations only.
"""
from pathlib import Path
import json
from html import escape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "v11_template.html"
INDEX = ROOT / "docs" / "index.html"
RESULT = ROOT / "results" / "feedback_loop_metrics.json"
MARKER = "__D04_DATA__"
TABLE_MARKER = "<!-- __D04_METHOD_COMPARISON__ -->"

def build(write=True):
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(MARKER) != 1 or template.count(TABLE_MARKER) != 1:
        raise ValueError("Expected one canonical v11 data marker")
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    comparison=json.loads((ROOT/"results"/"baseline_comparison.json").read_text(encoding="utf-8"))
    names=comparison["method_order"]
    titles=["Scenario","Day","Claims-only point","Gross-loss point","Strong conventional","Evidence-aware"]
    rows=[]
    for scenario in comparison["scenarios"]:
        for cp in scenario["checkpoints"]:
            fields=[scenario["label"],str(cp["day"])]+[cp["decisions"][name].upper() for name in names]
            rows.append("<tr>"+"".join("<td>"+escape(str(f))+"</td>" for f in fields)+"</tr>")
    table='<table class="d04-comparison"><thead><tr>'+"".join("<th>"+escape(t)+"</th>" for t in titles)+"</tr></thead><tbody>"+"".join(rows)+"</tbody></table>"
    rendered = template.replace(TABLE_MARKER,table).replace(MARKER, payload)
    if write:
        INDEX.write_text(rendered, encoding="utf-8")
    print("Rendered canonical D04 v11 docs/index.html")
    return rendered

if __name__ == "__main__":
    build()
