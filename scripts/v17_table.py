#!/usr/bin/env python3
"""从 analysis_v17_glm9.json 生成 results.tex 4.7 节的九条件后端矩阵表体 + 关键数字摘要。
用法: python v17_table.py  (在 v17_glm9conds.py 之后运行)"""
import json, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

A = json.load(open(os.path.join(_ROOT, 'results', 'analysis_v17_glm9.json')))
M9 = A["backend_matrix_9"]
CONDS = ["clean_r", "revr", "rb10", "rb5", "rb25", "rb0", "rbm25", "rbm5", "rn0"]
COLS = [("qwen-mt-uni", "oracle", "gummy_vs_oracle"),
        ("qwen-mt-uni", "glm", "gummy_vs_glmref"),
        ("GLM", "oracle", "glm_vs_oracle"),
        ("GLM", "glm", "glm_vs_glmref")]

def relloss(row, col):
    c = M9["clean_r"][col]["bleu"]; e = M9["rbm5"][col]["bleu"]
    return f"{100*(c-e)/c:.0f}\\%"

print("% ---- tab:backend body (nine conditions) ----")
print("% rel.loss = clean -> -5 dB within backend x reference")
for backend, refname, col in COLS:
    cells = " & ".join(f"{M9[c][col]['bleu']:.1f}" for c in CONDS)
    label = f"{backend} & {'oracle (same engine)' if refname=='oracle' else 'GLM (cross)'}" \
        if backend == "qwen-mt-uni" else \
        f"{backend} & {'oracle (cross)' if refname=='oracle' else 'GLM (same engine)'}"
    print(f"{label} & {cells} & {relloss(M9, col)} \\\\")

print()
print("% ---- key numbers ----")
for k in ["slope_gummy_9cond_oracleref_noclean", "slope_glm_9cond_glmref_noclean",
          "slope_glm_9cond_glmref_withclean", "slope_glm_9cond_oracleref_noclean",
          "slope_glm_9cond_glmref_noclean_prev3"]:
    v = A.get(k, {})
    print(f"{k}: " + ", ".join(f"{l} slope={d['slope']} r={d['r']} n={d['n_points']}" for l, d in v.items()))

print()
print("% ---- paired deltas (gummy - glm) ----")
for c in CONDS:
    d = A["backend_deltas"][c]
    print(f"{c:8s} glmref {d['glmref']:+6.2f}  oracle {d['oracle']:+6.2f}  diag_gummy {d['diag_gummy']:+6.2f}  diag_glm {d['diag_glm']:+6.2f}")

print()
print("% ---- per-cell n and empty accounting ----")
print("n_glm by cond:", A["n_glm_by_cond"])
print("empty accounting:", A["empty_accounting"])
