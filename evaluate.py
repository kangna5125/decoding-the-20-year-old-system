"""Step 3: test the model on the held-out CodeSearchNet test examples."""
import argparse
import json
import os
import re

import numpy as np

from common import read_jsonl
from explainer import HIGH, MEDIUM, CodeExplainer, confidence_level


def name_baseline(func_name):
    """A trivial baseline: turn the function name into words (get_user_name -> 'Get user name')."""
    name = func_name.split(".")[-1].strip("_")
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ")
    return " ".join(name.split()).capitalize()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", default="models/codet5-small-csn")
    ap.add_argument("--data_dir", default="data")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", default="results")
    a = ap.parse_args(argv)

    import sacrebleu
    from rouge_score import rouge_scorer

    rows = read_jsonl(os.path.join(a.data_dir, "test.jsonl"))[:a.n]
    ex = CodeExplainer(a.model_dir, db_path=None)
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    preds, confs = [], []
    for i, r in enumerate(rows, 1):
        text, conf, _ = ex.generate(r["code"])
        preds.append(text)
        confs.append(conf)
        if i % 50 == 0:
            print(f"generated {i}/{len(rows)}")
    refs = [r["description"] for r in rows]
    base = [name_baseline(r["func_name"]) for r in rows]

    rl = np.array([scorer.score(ref, p)["rougeL"].fmeasure for ref, p in zip(refs, preds)])
    rl_base = np.array([scorer.score(ref, b)["rougeL"].fmeasure for ref, b in zip(refs, base)])
    confs = np.array(confs)
    corr = float(np.corrcoef(confs, rl)[0, 1]) if confs.std() > 0 and rl.std() > 0 else None

    bleu_model = round(sacrebleu.corpus_bleu(preds, [refs]).score, 2)
    bleu_base = round(sacrebleu.corpus_bleu(base, [refs]).score, 2)

    buckets = {}
    for lvl in ["High", "Medium", "Low"]:
        mask = np.array([confidence_level(c) == lvl for c in confs])
        buckets[lvl] = {
            "count": int(mask.sum()),
            "percentage": round(float(mask.sum() / len(rows) * 100), 1),
            "avg_rougeL": round(float(rl[mask].mean()), 4) if mask.any() else None,
            "avg_confidence": round(float(confs[mask].mean()), 4) if mask.any() else None,
        }

    res = {"examples": len(rows),
           "bleu": bleu_model,
           "baseline_name_only_bleu": bleu_base,
           "rougeL": round(float(rl.mean()), 4),
           "baseline_name_only_rougeL": round(float(rl_base.mean()), 4),
           "avg_confidence": round(float(confs.mean()), 4),
           "confidence_vs_rougeL_correlation": None if corr is None else round(corr, 3),
           "confidence_levels": {"High >=": HIGH, "Medium >=": MEDIUM, **buckets},
           "suggested_cutoffs_from_thirds": [round(float(x), 3) for x in np.quantile(confs, [1 / 3, 2 / 3])]}

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "eval_results.json"), "w") as f:
        json.dump(res, f, indent=2)
    with open(os.path.join(a.out, "samples.md"), "w", encoding="utf-8") as f:
        for r, p, c in list(zip(rows, preds, confs))[:15]:
            snippet = "\n".join(r["code"].splitlines()[:8])
            f.write(f"### {r['func_name']}\n```python\n{snippet}\n```\n"
                    f"- Real description: {r['description']}\n- Model: {p}\n"
                    f"- Confidence: {c:.0%}\n- Source: {r['url']}\n\n")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
