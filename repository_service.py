"""Safe repository extraction, structural indexing, symbol search, and context retrieval."""
import os
import shutil
import tempfile
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from config import LANGUAGE_EXTENSIONS, SUPPORTED_LANGUAGES
from languages import detect_language, parse_code_structure

MAX_FILES_LIMIT = 500
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB


def is_safe_zip_path(target_dir: str, path: str) -> bool:
    """Verify that an archive member does not traverse outside target_dir."""
    if path.startswith("/") or path.startswith("\\") or (len(path) > 1 and path[1] == ":"):
        return False
    if ".." in path.split("/") or ".." in path.split("\\"):
        return False
    abs_target = os.path.abspath(target_dir)
    abs_dest = os.path.abspath(os.path.join(target_dir, path))
    return abs_dest.startswith(abs_target + os.sep) or abs_dest == abs_target


def safe_extract_zip(zip_file_or_bytes: Any, dest_dir: Optional[str] = None) -> Tuple[bool, str, str]:
    """Safely extract a ZIP repository, rejecting path traversals and decompression bombs."""
    target_dir = dest_dir or tempfile.mkdtemp(prefix="repo_")

    try:
        with zipfile.ZipFile(zip_file_or_bytes, "r") as zf:
            infolist = zf.infolist()
            if len(infolist) > MAX_FILES_LIMIT:
                return False, f"ZIP contains too many files ({len(infolist)} > {MAX_FILES_LIMIT} limit).", target_dir

            total_size = sum(f.file_size for f in infolist)
            if total_size > MAX_UNCOMPRESSED_BYTES:
                return False, f"Decompressed size exceeds limit ({total_size / 1024 / 1024:.1f} MB > 50 MB).", target_dir

            for member in infolist:
                if not is_safe_zip_path(target_dir, member.filename):
                    return False, f"Illegal path traversal detected in ZIP: {member.filename}", target_dir

            # Safe extraction
            for member in infolist:
                zf.extract(member, target_dir)

            return True, f"Successfully extracted {len(infolist)} files.", target_dir
    except zipfile.BadZipFile:
        return False, "Uploaded file is not a valid or readable ZIP archive.", target_dir
    except Exception as e:
        return False, f"Error extracting ZIP archive: {str(e)}", target_dir


class RepositoryIndex:
    """Indexes source files, classes, functions, calls, and imports across a repository."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.files: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.dependencies: Dict[str, List[str]] = {}
        self.call_graph: List[Dict[str, str]] = []
        self.language_distribution: Dict[str, int] = {lang: 0 for lang in SUPPORTED_LANGUAGES}
        self.total_loc: int = 0

    def build(self) -> None:
        """Scan directory and index all supported source files."""
        ignored_dirs = {
            ".git", "__pycache__", ".venv", "node_modules", "target", "build",
            "dist", ".idea", ".vscode", ".pytest_cache"
        }

        all_extensions = {ext for exts in LANGUAGE_EXTENSIONS.values() for ext in exts}

        for root, dirs, filenames in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in all_extensions:
                    continue

                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, self.root_dir)

                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue

                lang = detect_language(content, filename=fname)
                self.language_distribution[lang] = self.language_distribution.get(lang, 0) + 1

                lines = content.splitlines()
                loc = len([l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))])
                self.total_loc += loc

                struct = parse_code_structure(content, lang)

                file_record = {
                    "rel_path": rel_path,
                    "filename": fname,
                    "language": lang,
                    "loc": loc,
                    "content": content,
                    "struct": struct
                }
                self.files.append(file_record)

                # Index functions with snippet context
                for fn in struct.get("functions", []):
                    start_l = fn.get("line", 1)
                    end_l = fn.get("end_line", min(len(lines), start_l + 25))
                    snippet = "\n".join(lines[max(0, start_l - 1):end_l])

                    self.functions.append({
                        "name": fn["name"],
                        "file": rel_path,
                        "line": start_l,
                        "end_line": end_l,
                        "params": fn.get("params", []),
                        "language": lang,
                        "snippet": snippet
                    })

                # Index classes
                for cls in struct.get("classes", []):
                    self.classes.append({
                        "name": cls["name"],
                        "file": rel_path,
                        "line": cls.get("line", 1),
                        "language": lang
                    })

                # Extract imports/dependencies
                imports_found = []
                for line in lines:
                    line_s = line.strip()
                    if line_s.startswith(("import ", "from ", "#include", "package ")):
                        imports_found.append(line_s)
                if imports_found:
                    self.dependencies[rel_path] = imports_found[:15]

    def search_symbols(self, query: str) -> Dict[str, List[Any]]:
        """Search functions, classes, and files matching query substring."""
        q = query.lower().strip()
        if not q:
            return {"functions": self.functions[:20], "classes": self.classes[:20], "files": self.files[:20]}

        matched_fns = [f for f in self.functions if q in f["name"].lower() or q in f["file"].lower()]
        matched_classes = [c for c in self.classes if q in c["name"].lower() or q in c["file"].lower()]
        matched_files = [f for f in self.files if q in f["rel_path"].lower()]

        return {
            "functions": matched_fns,
            "classes": matched_classes,
            "files": matched_files
        }

    def retrieve_context_for_query(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Retrieve most relevant function and file snippets for a natural language question."""
        terms = [t for t in query.lower().split() if len(t) > 2]
        scored_items = []

        for fn in self.functions:
            score = 0
            fn_name_lower = fn["name"].lower()
            file_lower = fn["file"].lower()
            snippet_lower = fn["snippet"].lower()

            for term in terms:
                if term in fn_name_lower:
                    score += 5
                if term in file_lower:
                    score += 3
                if term in snippet_lower:
                    score += 1

            if score > 0:
                scored_items.append((score, fn))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored_items[:top_k]]

        # If no specific functions matched, return first few file headers
        if not results and self.files:
            for f in self.files[:2]:
                results.append({
                    "name": f["filename"],
                    "file": f["rel_path"],
                    "line": 1,
                    "language": f["language"],
                    "snippet": "\n".join(f["content"].splitlines()[:25])
                })

        return results
