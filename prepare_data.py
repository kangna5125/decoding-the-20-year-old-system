"""Step 1: build a small clean subset of CodeSearchNet (Python).

Each example = (code without its docstring, one-sentence description).
CodeSearchNet already splits by repository, so splits do not share repos.

Two ways to get the data:
  A) default: download from Hugging Face (code-search-net/code_search_net)
  B) --local_dir FOLDER: use parquet files you already downloaded. File names must
     contain "test", "validation" and (optionally) "train". If there is no train file,
     training examples are taken from 90% of the validation repositories and the
     other 10% are kept for validation (still no shared repositories).
"""
import argparse
import glob
import os
import random

from common import first_sentence, strip_docstring, valid_description, write_jsonl

DATASET = "code-search-net/code_search_net"
COLUMNS = ["func_code_string", "func_documentation_string",
           "repository_name", "func_name", "func_code_url"]


def clean_rows(records, n):
    rows, seen = [], set()
    for r in records:
        code = strip_docstring(r["func_code_string"])
        if code is None or len(code.splitlines()) < 3 or len(code) > 3000:
            continue
        desc = first_sentence(r["func_documentation_string"])
        if not valid_description(desc):
            continue
        if desc.lower()[:30] in code.lower():  # description leaked into the code
            continue
        if desc.lower() in seen:
            continue
        seen.add(desc.lower())
        rows.append({"code": code, "description": desc, "repo": r["repository_name"],
                     "func_name": r["func_name"], "url": r["func_code_url"]})
        if len(rows) >= n:
            break
    return rows


def hf_records(split, seed):
    from datasets import load_dataset
    ds = load_dataset(DATASET, "python", split=split)
    return ds.select_columns(COLUMNS).shuffle(seed=seed)


def local_records(folder, key, seed, limit=None):
    """Read all parquet files whose name contains `key`. If `limit` is given, only a random
    sample of that many rows is loaded into memory (the full train split is very large)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    folder = os.path.expanduser(folder)
    files = sorted(glob.glob(os.path.join(folder, f"*{key}*.parquet")))
    if not files:
        return None
    table = pa.concat_tables([pq.read_table(f, columns=COLUMNS) for f in files])
    if limit and table.num_rows > limit:
        idx = sorted(random.Random(seed).sample(range(table.num_rows), limit))
        table = table.take(idx)
    recs = table.to_pylist()
    random.Random(seed).shuffle(recs)
    return recs


def local_splits(folder, seed, sizes):
    folder = os.path.expanduser(folder)
    # about 20% of rows are dropped by cleaning, so load 8x what we need
    test = local_records(folder, "test", seed, sizes["test"] * 8)
    train = local_records(folder, "train", seed, sizes["train"] * 8)
    val = local_records(folder, "validation", seed, None if train is None else sizes["val"] * 8)
    if test is None or val is None:
        raise SystemExit(f"Need parquet files with 'test' and 'validation' in their names in {folder}")
    if train is None:
        repos = sorted({r["repository_name"] for r in val})
        random.Random(seed).shuffle(repos)
        cut = max(1, min(len(repos) - 1, int(0.9 * len(repos))))
        train_repos = set(repos[:cut])
        train = [r for r in val if r["repository_name"] in train_repos]
        val = [r for r in val if r["repository_name"] not in train_repos]
        print("No train file found: training on 90% of the validation repositories, "
              "validating on the other 10%.")
    else:
        print(f"Using real train file from {folder} ({len(train)} records loaded)")
    return {"train": train, "val": val, "test": test}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--train_size", type=int, default=5000)
    ap.add_argument("--val_size", type=int, default=500)
    ap.add_argument("--test_size", type=int, default=500)
    ap.add_argument("--out", default="data")
    ap.add_argument("--local_dir", default=None, help="folder with downloaded .parquet files")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    sizes = {"train": a.train_size, "val": a.val_size, "test": a.test_size}
    local = local_splits(a.local_dir, a.seed, sizes) if a.local_dir else None
    hf_names = {"train": "train", "val": "validation", "test": "test"}
    saved_splits = {}
    for name, n in sizes.items():
        records = local[name] if local else hf_records(hf_names[name], a.seed)
        rows = clean_rows(records, n)
        write_jsonl(os.path.join(a.out, f"{name}.jsonl"), rows)
        saved_splits[name] = rows
        print(f"{name}: saved {len(rows)} examples from {len({r['repo'] for r in rows})} repositories")

    # Verification summary
    print("\n--- Data Verification Summary ---")
    split_repos = {}
    all_github_urls = True
    for name, rows in saved_splits.items():
        split_repos[name] = {r["repo"] for r in rows}
        has_gh = all(r.get("url", "").startswith("https://github.com/") for r in rows)
        if not has_gh:
            all_github_urls = False
        print(f"Split '{name}': {len(rows)} rows, {len(split_repos[name])} distinct repos, all GitHub URLs: {has_gh}")

    overlap_train_val = len(split_repos.get("train", set()) & split_repos.get("val", set()))
    overlap_train_test = len(split_repos.get("train", set()) & split_repos.get("test", set()))
    overlap_val_test = len(split_repos.get("val", set()) & split_repos.get("test", set()))
    total_overlap = overlap_train_val + overlap_train_test + overlap_val_test

    print(f"Repo overlap: train-val: {overlap_train_val}, train-test: {overlap_train_test}, val-test: {overlap_val_test}")
    if total_overlap == 0:
        print("Confirmation: ZERO repo overlap between all splits.")
    else:
        print(f"WARNING: Repo overlap detected: {total_overlap}")
    if all_github_urls:
        print("Confirmation: All rows have valid GitHub URLs.")


if __name__ == "__main__":
    main()
