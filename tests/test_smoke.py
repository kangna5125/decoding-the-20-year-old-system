"""Runs the real prepare/train/explain/evaluate code on a tiny random model (no downloads)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import datasets

import evaluate
import prepare_data
import train
from common import read_jsonl, write_jsonl
from explainer import CodeExplainer
from tiny import build_tiny

RAW = '''def {name}(a, b):
    """{doc} Extra detail that should be dropped.

    :param a: first
    """
    total = a + b
    if total > {n}:
        total = {n}
    return total
'''


def fake_csn(n):
    rows = []
    for i in range(n):
        rows.append({"func_code_string": RAW.format(name=f"add_limit_{i}", n=i + 10,
                                                    doc=f"Add two numbers and cap the result at {i + 10}."),
                     "func_documentation_string": f"Add two numbers and cap the result at {i + 10}.\n\n:param a: first",
                     "repository_name": f"user/repo{i % 3}", "func_name": f"add_limit_{i}",
                     "func_code_url": f"https://github.com/user/repo/blob/x/f.py#L{i}"})
    rows.append({"func_code_string": "print 'python 2'", "func_documentation_string": "Broken old code sample here.",
                 "repository_name": "user/repo0", "func_name": "bad", "func_code_url": "u"})
    return datasets.Dataset.from_list(rows)


def test_prepare_data_cleans_and_splits(tmp_path, monkeypatch):
    monkeypatch.setattr(datasets, "load_dataset", lambda *a, **k: fake_csn(30))
    out = tmp_path / "data"
    prepare_data.main(["--train_size", "20", "--val_size", "4", "--test_size", "4", "--out", str(out)])
    train_rows = read_jsonl(out / "train.jsonl")
    assert len(train_rows) == 20 and len(read_jsonl(out / "val.jsonl")) == 4
    for r in train_rows:
        assert "Extra detail" not in r["code"] and "Add two numbers" not in r["code"]
        assert r["description"].startswith("Add two numbers")


def test_full_pipeline_on_tiny_model(tmp_path, monkeypatch):
    monkeypatch.setattr(datasets, "load_dataset", lambda *a, **k: fake_csn(40))
    data = tmp_path / "data"
    prepare_data.main(["--train_size", "24", "--val_size", "6", "--test_size", "6", "--out", str(data)])
    texts = [r["code"] + " " + r["description"] for r in read_jsonl(data / "train.jsonl")]
    base, out = tmp_path / "base", tmp_path / "model"
    build_tiny(str(base), texts)

    train.main(["--base_model", str(base), "--data_dir", str(data), "--out", str(out),
                "--epochs", "2", "--batch_size", "4", "--log_every", "2"])
    info = json.load(open(out / "training_log.json"))
    assert info["best_val_loss"] > 0 and (out / "config.json").exists()

    ex = CodeExplainer(str(out), db_path=str(tmp_path / "c.db"))
    code = "def f(x, y):\n    z = x + y\n    return z * 2\n"
    first = ex.explain(code)
    assert first["source"] == "model" and 0 <= first["confidence"] <= 1
    assert first["level"] in ("High", "Medium", "Low")

    ex.save_correction(code, first["explanation"], "Adds two numbers and doubles the sum.", "tester")
    again = ex.explain(code)
    assert again["source"] == "verified" and again["explanation"] == "Adds two numbers and doubles the sum."
    assert ex.explain("def f(x, y):\n    z = x + y\n    return z * 2  \n")["source"] == "verified"

    evaluate.main(["--model_dir", str(out), "--data_dir", str(data), "--n", "6", "--out", str(tmp_path / "res")])
    res = json.load(open(tmp_path / "res" / "eval_results.json"))
    assert res["examples"] == 6 and "bleu" in res and "baseline_name_only_rougeL" in res
    assert (tmp_path / "res" / "samples.md").exists()


def test_prepare_data_from_local_parquet_files(tmp_path):
    folder = tmp_path / "dl"
    folder.mkdir()
    fake_csn(30).to_parquet(str(folder / "test-00000-of-00001.parquet"))
    fake_csn(30).to_parquet(str(folder / "validation-00000-of-00001.parquet"))
    out = tmp_path / "data"
    prepare_data.main(["--local_dir", str(folder), "--train_size", "10", "--val_size", "3",
                       "--test_size", "4", "--out", str(out)])
    train_rows, val_rows = read_jsonl(out / "train.jsonl"), read_jsonl(out / "val.jsonl")
    assert len(train_rows) == 10 and len(val_rows) == 3 and len(read_jsonl(out / "test.jsonl")) == 4
    assert not {r["repo"] for r in train_rows} & {r["repo"] for r in val_rows}  # no repo leakage
