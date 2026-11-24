"""Small helpers shared by all scripts."""
import ast
import json
import os
import re
import shutil
import tempfile
import textwrap
import warnings


def get_device():
    """Use the Mac GPU (MPS) or NVIDIA GPU if present, otherwise the CPU."""
    import torch
    if torch.cuda.is_available():
        return torch.device("cuda")
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _plain(value):
    """Turn {"content": "<s>", ...} special-token entries into plain strings."""
    if isinstance(value, dict) and "content" in value:
        return value["content"]
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def load_tokenizer(name):
    """Load a tokenizer, working around a clash between CodeT5's tokenizer files and
    transformers 5, which fails with "TypeError: Input must be a List[Union[str, AddedToken]]"
    because the files store special tokens as dictionaries. We convert them to plain text."""
    from transformers import AutoTokenizer
    try:
        return AutoTokenizer.from_pretrained(name)
    except TypeError:
        pass
    if os.path.isdir(name):
        source = name
    else:
        from huggingface_hub import snapshot_download
        source = snapshot_download(name, allow_patterns=["*.json", "*.txt", "*.model"])
    fixed = os.path.join(tempfile.mkdtemp(), "tokenizer")
    shutil.copytree(source, fixed)
    for filename in ("special_tokens_map.json", "tokenizer_config.json"):
        path = os.path.join(fixed, filename)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            data = {k: (v if k == "added_tokens_decoder" else _plain(v)) for k, v in data.items()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
    return AutoTokenizer.from_pretrained(fixed)


def strip_docstring(code):
    """Remove a function's docstring so the model cannot just copy it.

    Returns the cleaned code, or None if the code cannot be parsed
    (for example old Python 2 code) or the docstring sits on the def line.
    Code with no function or no docstring is returned unchanged.
    """
    code = textwrap.dedent(code).strip("\n")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # old code often has odd escape characters
            tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return None
    func = next((n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if func is None or not func.body:
        return code
    first = func.body[0]
    is_doc = (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
              and isinstance(first.value.value, str))
    if not is_doc:
        return code
    header_end = func.body[0].lineno - 1
    if first.lineno <= func.lineno or header_end < 1:
        return None
    lines = code.splitlines()
    del lines[first.lineno - 1:first.end_lineno]
    return "\n".join(lines)


def first_sentence(doc):
    """Take the first sentence of the first paragraph of a docstring."""
    para = re.split(r"\n\s*\n", doc.strip())[0]
    para = re.sub(r"\s+", " ", para).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", para)
    sent = m.group(1) if m else para
    if len(sent.split()) < 4:  # too short, probably split at "e.g." or similar
        sent = " ".join(para.split()[:30])
    return sent


def valid_description(s):
    """Keep only short, clean, English-looking descriptions."""
    if not s:
        return False
    words = s.split()
    if not 3 <= len(words) <= 40:
        return False
    if sum(ch.isascii() for ch in s) / len(s) < 0.95:
        return False
    if s.startswith((":", "@", "#", "..", ">>>", "TODO", "FIXME", "Deprecated")):
        return False
    if "http" in s or ">>>" in s:
        return False
    return True


def normalize_code(code):
    """Collapse whitespace so the same code always gives the same key."""
    return re.sub(r"\s+", " ", code).strip()


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
