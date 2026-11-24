import io
import os
import zipfile
import pytest

from repository_service import safe_extract_zip, is_safe_zip_path, RepositoryIndex


def test_is_safe_zip_path():
    assert is_safe_zip_path("/tmp/safe", "src/main.py") is True
    assert is_safe_zip_path("/tmp/safe", "src/utils/calc.py") is True
    assert is_safe_zip_path("/tmp/safe", "../evil.py") is False
    assert is_safe_zip_path("/tmp/safe", "/etc/passwd") is False
    assert is_safe_zip_path("/tmp/safe", "\\windows\\system32") is False


def test_safe_extract_zip_valid_and_traversal(tmp_path):
    # 1. Valid ZIP
    valid_buf = io.BytesIO()
    with zipfile.ZipFile(valid_buf, "w") as zf:
        zf.writestr("module/app.py", "def run():\n    print('hello')\n")
        zf.writestr("module/utils.py", "def add(a, b):\n    return a + b\n")
    valid_buf.seek(0)

    extract_dest = str(tmp_path / "valid_extract")
    success, msg, target = safe_extract_zip(valid_buf, dest_dir=extract_dest)
    assert success is True
    assert os.path.exists(os.path.join(target, "module", "app.py"))
    assert os.path.exists(os.path.join(target, "module", "utils.py"))

    # 2. Path Traversal Zip
    evil_buf = io.BytesIO()
    with zipfile.ZipFile(evil_buf, "w") as zf:
        zf.writestr("../evil.py", "print('hacked')\n")
    evil_buf.seek(0)

    evil_dest = str(tmp_path / "evil_extract")
    success_evil, msg_evil, _ = safe_extract_zip(evil_buf, dest_dir=evil_dest)
    assert success_evil is False
    assert "Illegal path traversal" in msg_evil


def test_safe_extract_zip_file_count_and_size_limits(tmp_path):
    # Too many files
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(505):
            zf.writestr(f"file_{i}.txt", "a")
    buf.seek(0)

    dest = str(tmp_path / "limit_extract")
    success, msg, _ = safe_extract_zip(buf, dest_dir=dest)
    assert success is False
    assert "too many files" in msg.lower()


def test_repository_index(tmp_path):
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    (repo_dir / "math_lib.py").write_text("class Calculator:\n    def add(self, a, b):\n        return a + b\n")
    (repo_dir / "main.js").write_text("function startApp() {\n    console.log('App started');\n}\n")

    index = RepositoryIndex(str(repo_dir))
    index.build()

    assert len(index.files) == 2
    assert index.language_distribution.get("Python", 0) >= 1
    assert index.language_distribution.get("JavaScript", 0) >= 1

    # Symbol search returns {"functions": [...], "classes": [...], "files": [...]}
    results = index.search_symbols("add")
    assert "functions" in results
    assert len(results["functions"]) >= 1
    assert any(s["name"] == "add" for s in results["functions"])

    # Context retrieval for chatbot returns list of scored context items
    context = index.retrieve_context_for_query("How does add work in Calculator?")
    assert len(context) >= 1
    assert any("add" in item["name"] for item in context)
    assert any("math_lib.py" in item["file"] for item in context)
