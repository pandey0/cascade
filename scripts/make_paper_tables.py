"""Generate paper tables for exp1b and exp2 from results/*.json (booktabs, headline cells only)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "tables"
METHODS = ("naive", "wilson", "bonferroni", "holm")


def _load(name: str) -> list[dict[str, object]]:
    return list(json.loads((ROOT / "results" / name).read_text(encoding="utf-8")))


def exp1b() -> str:
    lines = [
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Task / student & $\alpha$ & method & deploy & viol.\ (teacher) & viol.\ (gold) & cov.\\",
        r"\midrule",
    ]
    for task, tag in (("banking77", "B77"), ("clinc150", "CL150")):
        for variant, vname in (("distilled", "distilled"), ("goldtrained", "gold-trained")):
            for a, aval in (("010", "0.10"),):
                n = f"exp1b_{variant}_{task}_alpha{a}"
                t = _load(f"{n}_vs_teacher.json")
                g = _load(f"{n}_vs_gold.json")
                for rt, rg in zip(t, g, strict=True):
                    if rt["m"] != 400 or rt["method"] not in METHODS:
                        continue
                    lines.append(
                        f"{tag} {vname} & {aval} & {rt['method']} & {rt['deploy_rate']:.2f} & "
                        f"{rt['violation_rate_all']:.3f} & {rg['violation_rate_all']:.3f} & "
                        f"{rt['mean_coverage']:.2f}\\\\"
                    )
    return "\n".join([*lines, r"\bottomrule", r"\end{tabular}"]) + "\n"


def exp2() -> str:
    lines = [
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Shift (Banking77) & policy & audit & post risk & post cov. & blocks $>\alpha$\\",
        r"\midrule",
    ]
    rows = _load("exp2_banking77_w1000.json")
    for r in rows:
        if r["audit_rate"] != 0.10:
            continue
        shift = r["pool"].split("_")[-1]
        pol = r["policy"].replace("_", r"\_")
        lines.append(
            f"{shift} & {pol} & {r['audit_rate']:.2f} & {r['post_mean_risk']:.3f} & "
            f"{r['post_mean_coverage']:.2f} & {r['post_block_violation_rate']:.2f}\\\\"
        )
    return "\n".join([*lines, r"\bottomrule", r"\end{tabular}"]) + "\n"


if __name__ == "__main__":
    (OUT / "exp1b.tex").write_text(exp1b(), encoding="utf-8")
    (OUT / "exp2.tex").write_text(exp2(), encoding="utf-8")
    print("wrote paper/tables/exp1b.tex, exp2.tex")
