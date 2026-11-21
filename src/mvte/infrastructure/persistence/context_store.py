"""Local SQLite persistence for glossary, translation memory, and macro narrative notes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mvte.domain.models.translation import GlossaryTerm, TranslationMemoryEntry


class SqliteContextStore:
    """Zero-config local SQLite store for MVTE context management."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS glossary_terms (
                    id TEXT PRIMARY KEY,
                    work_id TEXT NOT NULL,
                    source_term TEXT NOT NULL,
                    target_term TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'term',
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_glossary_work ON glossary_terms(work_id);

                CREATE TABLE IF NOT EXISTS translation_memory (
                    id TEXT PRIMARY KEY,
                    work_id TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    context_summary TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_tm_lookup
                    ON translation_memory(work_id, source_lang, target_lang);

                CREATE TABLE IF NOT EXISTS narrative_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    note TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_notes_work ON narrative_notes(work_id);
                """
            )

    def add_glossary_term(self, term: GlossaryTerm) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO glossary_terms
                (id, work_id, source_term, target_term, category, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (term.id, term.work_id, term.source_term, term.target_term, term.category, term.notes),
            )

    def list_glossary_terms(self, work_id: str) -> list[GlossaryTerm]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, work_id, source_term, target_term, category, notes FROM glossary_terms WHERE work_id = ?",
                (work_id,),
            ).fetchall()
        return [
            GlossaryTerm(
                id=r[0], work_id=r[1], source_term=r[2], target_term=r[3], category=r[4], notes=r[5]
            )
            for r in rows
        ]

    def add_tm_entry(self, entry: TranslationMemoryEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO translation_memory
                (id, work_id, source_lang, target_lang, source_text, target_text, context_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.work_id,
                    entry.source_lang,
                    entry.target_lang,
                    entry.source_text,
                    entry.target_text,
                    entry.context_summary,
                ),
            )

    def list_tm_entries(
        self, work_id: str, source_lang: str, target_lang: str
    ) -> list[TranslationMemoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, work_id, source_lang, target_lang, source_text, target_text, context_summary
                FROM translation_memory
                WHERE work_id = ? AND source_lang = ? AND target_lang = ?
                """,
                (work_id, source_lang, target_lang),
            ).fetchall()
        return [
            TranslationMemoryEntry(
                id=r[0],
                work_id=r[1],
                source_lang=r[2],
                target_lang=r[3],
                source_text=r[4],
                target_text=r[5],
                context_summary=r[6],
            )
            for r in rows
        ]

    def add_narrative_note(self, work_id: str, note: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO narrative_notes (work_id, note) VALUES (?, ?)",
                (work_id, note),
            )

    def list_narrative_notes(self, work_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT note FROM narrative_notes WHERE work_id = ? ORDER BY id ASC",
                (work_id,),
            ).fetchall()
        return [str(r[0]) for r in rows]
