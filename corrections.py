"""Reviewer corrections: saved in a small SQLite file and reused for the same (or very similar) code."""
import difflib
import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, List, Optional

from common import normalize_code

SCHEMA = """CREATE TABLE IF NOT EXISTS corrections (
    code_hash TEXT PRIMARY KEY,
    code TEXT,
    original TEXT,
    corrected TEXT,
    reviewer TEXT,
    created_at TEXT,
    status TEXT DEFAULT 'Approved',
    source TEXT DEFAULT 'Human Reviewer',
    rule_type TEXT DEFAULT 'Explanation Correction',
    updated_at TEXT DEFAULT ''
)"""


def _hash(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("utf-8")).hexdigest()


class CorrectionStore:
    def __init__(self, path: str = "corrections.db"):
        self.path = path
        with closing(sqlite3.connect(self.path)) as db:
            db.execute(SCHEMA)
            # Ensure migrations for existing DB tables
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            existing_cols = {row["name"] for row in cursor.execute("PRAGMA table_info(corrections)")}
            if "status" not in existing_cols:
                db.execute("ALTER TABLE corrections ADD COLUMN status TEXT DEFAULT 'Approved'")
            if "source" not in existing_cols:
                db.execute("ALTER TABLE corrections ADD COLUMN source TEXT DEFAULT 'Human Reviewer'")
            if "rule_type" not in existing_cols:
                db.execute("ALTER TABLE corrections ADD COLUMN rule_type TEXT DEFAULT 'Explanation Correction'")
            if "updated_at" not in existing_cols:
                db.execute("ALTER TABLE corrections ADD COLUMN updated_at TEXT DEFAULT ''")
            db.commit()

    def _rows(self, query: str, args: tuple = ()) -> List[Dict[str, Any]]:
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute(query, args)]

    def save(
        self,
        code: str,
        original: str,
        corrected: str,
        reviewer: str = "",
        status: str = "Approved",
        source: str = "Human Reviewer",
        rule_type: str = "Explanation Correction"
    ) -> None:
        corrected = (corrected or "").strip()
        if not corrected:
            raise ValueError("The corrected explanation cannot be empty.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with closing(sqlite3.connect(self.path)) as db:
            db.execute(
                """INSERT INTO corrections (code_hash, code, original, corrected, reviewer, created_at, status, source, rule_type, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(code_hash) DO UPDATE SET
                       code = excluded.code,
                       original = excluded.original,
                       corrected = excluded.corrected,
                       reviewer = excluded.reviewer,
                       status = excluded.status,
                       source = excluded.source,
                       rule_type = excluded.rule_type,
                       updated_at = excluded.created_at""",
                (_hash(code), normalize_code(code), original or "", corrected,
                 reviewer.strip(), now_str, status, source, rule_type, now_str)
            )
            db.commit()

    def find(self, code: str, min_similarity: float = 0.9) -> Optional[Dict[str, Any]]:
        """Exact match first, then closest saved code if >= 90% similar. Only considers Approved items."""
        exact = self._rows("SELECT * FROM corrections WHERE code_hash=? AND status='Approved'", (_hash(code),))
        if exact:
            return {**exact[0], "similarity": 1.0}
        norm, best = normalize_code(code), None
        for r in self._rows("SELECT * FROM corrections WHERE status='Approved'"):
            sm = difflib.SequenceMatcher(None, norm, r["code"], autojunk=False)
            if sm.real_quick_ratio() < min_similarity or sm.quick_ratio() < min_similarity:
                continue
            ratio = sm.ratio()
            if ratio >= min_similarity and (best is None or ratio > best["similarity"]):
                best = {**r, "similarity": ratio}
        return best

    def all(self) -> List[Dict[str, Any]]:
        return self._rows("SELECT * FROM corrections ORDER BY created_at DESC")

    def count(self) -> int:
        return self._rows("SELECT COUNT(*) AS n FROM corrections")[0]["n"]

    def update_status(self, code_hash: str, new_status: str, reviewer: str = "") -> None:
        """Update review status (e.g. Approved, Rejected, Pending Review)."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with closing(sqlite3.connect(self.path)) as db:
            if reviewer.strip():
                db.execute(
                    "UPDATE corrections SET status=?, reviewer=?, updated_at=? WHERE code_hash=?",
                    (new_status, reviewer.strip(), now_str, code_hash)
                )
            else:
                db.execute(
                    "UPDATE corrections SET status=?, updated_at=? WHERE code_hash=?",
                    (new_status, now_str, code_hash)
                )
            db.commit()

    def edit_correction(
        self,
        code_hash: str,
        new_corrected: str,
        new_status: str = "Approved",
        reviewer: str = ""
    ) -> None:
        """Edit the text and status of a verified correction."""
        new_corrected = (new_corrected or "").strip()
        if not new_corrected:
            raise ValueError("Corrected text cannot be empty.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with closing(sqlite3.connect(self.path)) as db:
            if reviewer.strip():
                db.execute(
                    "UPDATE corrections SET corrected=?, status=?, reviewer=?, updated_at=? WHERE code_hash=?",
                    (new_corrected, new_status, reviewer.strip(), now_str, code_hash)
                )
            else:
                db.execute(
                    "UPDATE corrections SET corrected=?, status=?, updated_at=? WHERE code_hash=?",
                    (new_corrected, new_status, now_str, code_hash)
                )
            db.commit()

    def delete(self, code_hash: str) -> None:
        """Permanently delete a correction record."""
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("DELETE FROM corrections WHERE code_hash=?", (code_hash,))
            db.commit()

    def search(
        self,
        query: str = "",
        status_filter: Optional[str] = None,
        rule_type_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter saved corrections by search query, review status, and category."""
        q = (query or "").lower().strip()
        rows = self.all()
        filtered = []
        for r in rows:
            if status_filter and status_filter != "All" and r.get("status") != status_filter:
                continue
            if rule_type_filter and rule_type_filter != "All" and r.get("rule_type") != rule_type_filter:
                continue
            if q:
                searchable = (
                    f"{r.get('code', '')} {r.get('original', '')} {r.get('corrected', '')} "
                    f"{r.get('reviewer', '')} {r.get('source', '')} {r.get('rule_type', '')}"
                ).lower()
                if q not in searchable:
                    continue
            filtered.append(r)
        return filtered
