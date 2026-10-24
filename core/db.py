"""Accès à la base SQLite locale.

Toutes les données de Noahim (matières, chapitres, examens, séances, XP...)
vivent dans un seul fichier `data/noahim.db`. Rien ne part sur Internet.

Les migrations sont volontairement simples : une liste de scripts SQL
numérotés, appliqués dans l'ordre grâce à `PRAGMA user_version`.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
# Chemin modifiable (les tests utilisent une base temporaire).
DB_PATH = Path(os.getenv("NOAHIM_DB_PATH", DATA_DIR / "noahim.db"))

STATUSES = ["a_voir", "en_cours", "maitrise"]
STATUS_LABELS = {"a_voir": "À voir", "en_cours": "En cours", "maitrise": "Maîtrisé"}
STATUS_EMOJIS = {"a_voir": "⚪", "en_cours": "🟠", "maitrise": "🟢"}

# ---------------------------------------------------------------------------
# Migrations : on ajoute toujours à la fin, on ne modifie jamais une ancienne.
# ---------------------------------------------------------------------------
MIGRATIONS: list[str] = [
    # 1 — schéma initial
    """
    CREATE TABLE subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        emoji TEXT NOT NULL DEFAULT '📘',
        color TEXT NOT NULL DEFAULT '#1a82d4',
        position INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'a_voir',
        confidence INTEGER NOT NULL DEFAULT 1 CHECK (confidence BETWEEN 1 AND 5),
        notes TEXT NOT NULL DEFAULT '',
        pasted_content TEXT NOT NULL DEFAULT '',
        position INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT
    );
    CREATE TABLE chapter_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        added_at TEXT NOT NULL
    );
    CREATE TABLE exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        exam_date TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE exam_chapters (
        exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
        chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        PRIMARY KEY (exam_id, chapter_id)
    );
    CREATE TABLE revision_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
        chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        session_date TEXT NOT NULL,
        minutes INTEGER NOT NULL DEFAULT 45,
        done INTEGER NOT NULL DEFAULT 0,
        done_at TEXT
    );
    CREATE TABLE focus_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        minutes INTEGER NOT NULL,
        chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL
    );
    CREATE TABLE quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        taken_at TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL
    );
    CREATE TABLE weak_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        question TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        resolved INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE fiches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
        content_md TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'manuel',
        created_at TEXT NOT NULL
    );
    CREATE TABLE progress_snapshots (
        snap_date TEXT NOT NULL,
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        score REAL NOT NULL,
        PRIMARY KEY (snap_date, subject_id)
    );
    CREATE TABLE activity (day TEXT PRIMARY KEY);
    CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE INDEX idx_chapters_subject ON chapters(subject_id);
    CREATE INDEX idx_sessions_date ON revision_sessions(session_date);
    """,
]

# ---------------------------------------------------------------------------
# Données de départ (programme de Première, modifiable dans l'app)
# ---------------------------------------------------------------------------
SEED: list[tuple[str, str, str, list[str]]] = [
    ("Maths", "📐", "#1a82d4", [
        "Suites numériques", "Dérivation", "Variations et courbes",
        "Fonction exponentielle", "Trigonométrie", "Produit scalaire",
        "Probabilités conditionnelles et indépendance", "Variables aléatoires",
        "Second degré", "Géométrie repérée",
    ]),
    ("Physique-Chimie", "⚗️", "#ff9f43", [
        "Constitution et transformations de la matière",
        "Réactions d'oxydo-réduction", "Mouvement et interactions",
        "Énergie : conversions et transferts", "Ondes et signaux",
    ]),
    ("SVT", "🌱", "#3ddc97", [
        "Transmission, variation et expression du patrimoine génétique",
        "Évolution", "Écosystèmes et services écosystémiques",
        "Climats du passé et changement climatique", "Corps humain et santé",
    ]),
]

# Couleurs attribuées aux matières ajoutées par Noahim.
EXTRA_COLORS = ["#b388ff", "#ff6b9d", "#ffd166", "#4dd0e1", "#a3e635"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Ouvre une connexion, valide à la fin, annule en cas d'erreur."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Crée la base si besoin, applique les migrations et injecte les données de départ."""
    with connect() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for number, script in enumerate(MIGRATIONS, start=1):
            if number > version:
                conn.executescript(script)
                conn.execute(f"PRAGMA user_version = {number}")
        if conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 0:
            _seed(conn)


def _seed(conn: sqlite3.Connection) -> None:
    for s_pos, (name, emoji, color, chapters) in enumerate(SEED):
        cur = conn.execute(
            "INSERT INTO subjects (name, emoji, color, position) VALUES (?, ?, ?, ?)",
            (name, emoji, color, s_pos),
        )
        conn.executemany(
            "INSERT INTO chapters (subject_id, name, position, updated_at) VALUES (?, ?, ?, ?)",
            [(cur.lastrowid, ch, i, _now()) for i, ch in enumerate(chapters)],
        )


# ---------------------------------------------------------------------------
# Matières
# ---------------------------------------------------------------------------
def list_subjects() -> list[dict]:
    with connect() as conn:
        return _rows(conn, "SELECT * FROM subjects ORDER BY position, id")


def add_subject(name: str, emoji: str = "📘") -> int:
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        color = EXTRA_COLORS[count % len(EXTRA_COLORS)]
        cur = conn.execute(
            "INSERT INTO subjects (name, emoji, color, position) VALUES (?, ?, ?, ?)",
            (name.strip(), emoji or "📘", color, count),
        )
        return cur.lastrowid


def rename_subject(subject_id: int, name: str, emoji: Optional[str] = None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE subjects SET name = ?, emoji = COALESCE(?, emoji) WHERE id = ?",
            (name.strip(), emoji, subject_id),
        )


def delete_subject(subject_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))


# ---------------------------------------------------------------------------
# Chapitres
# ---------------------------------------------------------------------------
_CHAPTER_SELECT = """
    SELECT c.*, s.name AS subject_name, s.emoji AS subject_emoji, s.color AS subject_color
    FROM chapters c JOIN subjects s ON s.id = c.subject_id
"""


def list_chapters(subject_id: Optional[int] = None) -> list[dict]:
    with connect() as conn:
        if subject_id is None:
            return _rows(conn, _CHAPTER_SELECT + " ORDER BY s.position, s.id, c.position, c.id")
        return _rows(
            conn, _CHAPTER_SELECT + " WHERE c.subject_id = ? ORDER BY c.position, c.id",
            (subject_id,),
        )


def get_chapter(chapter_id: int) -> Optional[dict]:
    with connect() as conn:
        rows = _rows(conn, _CHAPTER_SELECT + " WHERE c.id = ?", (chapter_id,))
        return rows[0] if rows else None


def add_chapter(subject_id: int, name: str) -> int:
    with connect() as conn:
        pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM chapters WHERE subject_id = ?",
            (subject_id,),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO chapters (subject_id, name, position, updated_at) VALUES (?, ?, ?, ?)",
            (subject_id, name.strip(), pos, _now()),
        )
        return cur.lastrowid


def rename_chapter(chapter_id: int, name: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE chapters SET name = ? WHERE id = ?", (name.strip(), chapter_id))


def delete_chapter(chapter_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))


def update_chapter(chapter_id: int, **fields) -> None:
    """Met à jour status / confidence / notes / pasted_content d'un chapitre."""
    allowed = {"status", "confidence", "notes", "pasted_content"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    if "status" in updates and updates["status"] not in STATUSES:
        raise ValueError(f"Statut inconnu : {updates['status']}")
    sets = ", ".join(f"{k} = ?" for k in updates)
    with connect() as conn:
        conn.execute(
            f"UPDATE chapters SET {sets}, updated_at = ? WHERE id = ?",
            (*updates.values(), _now(), chapter_id),
        )


# ---------------------------------------------------------------------------
# Fichiers de cours importés
# ---------------------------------------------------------------------------
def add_chapter_file(chapter_id: int, filename: str, stored_path: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO chapter_files (chapter_id, filename, stored_path, added_at) VALUES (?, ?, ?, ?)",
            (chapter_id, filename, stored_path, _now()),
        )
        return cur.lastrowid


def list_chapter_files(chapter_id: int) -> list[dict]:
    with connect() as conn:
        return _rows(conn, "SELECT * FROM chapter_files WHERE chapter_id = ? ORDER BY id", (chapter_id,))


def delete_chapter_file(file_id: int) -> Optional[str]:
    """Supprime l'entrée et renvoie le chemin du fichier à effacer du disque."""
    with connect() as conn:
        row = conn.execute("SELECT stored_path FROM chapter_files WHERE id = ?", (file_id,)).fetchone()
        conn.execute("DELETE FROM chapter_files WHERE id = ?", (file_id,))
        return row["stored_path"] if row else None


# ---------------------------------------------------------------------------
# Examens et séances de révision
# ---------------------------------------------------------------------------
def add_exam(subject_id: int, title: str, exam_date: date, chapter_ids: list[int]) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO exams (subject_id, title, exam_date, created_at) VALUES (?, ?, ?, ?)",
            (subject_id, title.strip(), exam_date.isoformat(), _now()),
        )
        conn.executemany(
            "INSERT INTO exam_chapters (exam_id, chapter_id) VALUES (?, ?)",
            [(cur.lastrowid, cid) for cid in chapter_ids],
        )
        return cur.lastrowid


def list_exams(upcoming_only: bool = False, today: Optional[date] = None) -> list[dict]:
    today = today or date.today()
    sql = """
        SELECT e.*, s.name AS subject_name, s.emoji AS subject_emoji, s.color AS subject_color,
               (SELECT COUNT(*) FROM revision_sessions r WHERE r.exam_id = e.id) AS n_sessions,
               (SELECT COUNT(*) FROM revision_sessions r WHERE r.exam_id = e.id AND r.done = 1) AS n_done
        FROM exams e JOIN subjects s ON s.id = e.subject_id
    """
    params: tuple = ()
    if upcoming_only:
        sql += " WHERE e.exam_date >= ?"
        params = (today.isoformat(),)
    sql += " ORDER BY e.exam_date"
    with connect() as conn:
        return _rows(conn, sql, params)


def exam_chapters(exam_id: int) -> list[dict]:
    with connect() as conn:
        return _rows(
            conn,
            _CHAPTER_SELECT + " JOIN exam_chapters ec ON ec.chapter_id = c.id WHERE ec.exam_id = ? ORDER BY c.position",
            (exam_id,),
        )


def delete_exam(exam_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))


def replace_pending_sessions(exam_id: int, sessions: list[tuple[date, int, int]]) -> None:
    """Remplace les séances non faites d'un examen par un nouveau plan.

    `sessions` : liste de (jour, chapter_id, minutes). Les séances déjà
    validées sont conservées pour ne pas perdre l'historique de Noahim.
    """
    with connect() as conn:
        conn.execute("DELETE FROM revision_sessions WHERE exam_id = ? AND done = 0", (exam_id,))
        conn.executemany(
            "INSERT INTO revision_sessions (exam_id, chapter_id, session_date, minutes) VALUES (?, ?, ?, ?)",
            [(exam_id, cid, d.isoformat(), m) for d, cid, m in sessions],
        )


def list_sessions(start: Optional[date] = None, end: Optional[date] = None,
                  only_pending: bool = False) -> list[dict]:
    """Séances de révision entre deux dates incluses."""
    sql = """
        SELECT r.*, c.name AS chapter_name, s.name AS subject_name, s.emoji AS subject_emoji,
               s.color AS subject_color, e.title AS exam_title, e.exam_date
        FROM revision_sessions r
        JOIN chapters c ON c.id = r.chapter_id
        JOIN subjects s ON s.id = c.subject_id
        JOIN exams e ON e.id = r.exam_id
        WHERE 1 = 1
    """
    params: list = []
    if start:
        sql += " AND r.session_date >= ?"
        params.append(start.isoformat())
    if end:
        sql += " AND r.session_date <= ?"
        params.append(end.isoformat())
    if only_pending:
        sql += " AND r.done = 0"
    sql += " ORDER BY r.session_date, s.position, r.id"
    with connect() as conn:
        return _rows(conn, sql, tuple(params))


def set_session_done(session_id: int, done: bool) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE revision_sessions SET done = ?, done_at = ? WHERE id = ?",
            (1 if done else 0, _now() if done else None, session_id),
        )


# ---------------------------------------------------------------------------
# Mode focus
# ---------------------------------------------------------------------------
def add_focus_session(minutes: int, chapter_id: Optional[int] = None) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO focus_sessions (started_at, minutes, chapter_id) VALUES (?, ?, ?)",
            (_now(), minutes, chapter_id),
        )
        return cur.lastrowid


def list_focus_sessions(limit: int = 200) -> list[dict]:
    with connect() as conn:
        return _rows(
            conn,
            """SELECT f.*, c.name AS chapter_name FROM focus_sessions f
               LEFT JOIN chapters c ON c.id = f.chapter_id
               ORDER BY f.started_at DESC LIMIT ?""",
            (limit,),
        )


# ---------------------------------------------------------------------------
# Quiz et points à retravailler
# ---------------------------------------------------------------------------
def add_quiz_result(chapter_id: int, score: int, total: int) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO quiz_results (chapter_id, taken_at, score, total) VALUES (?, ?, ?, ?)",
            (chapter_id, _now(), score, total),
        )


def list_quiz_results(chapter_id: Optional[int] = None) -> list[dict]:
    with connect() as conn:
        if chapter_id is None:
            return _rows(conn, "SELECT * FROM quiz_results ORDER BY taken_at")
        return _rows(conn, "SELECT * FROM quiz_results WHERE chapter_id = ? ORDER BY taken_at", (chapter_id,))


def add_weak_point(chapter_id: int, question: str, detail: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO weak_points (chapter_id, question, detail, created_at) VALUES (?, ?, ?, ?)",
            (chapter_id, question, detail, _now()),
        )


def list_weak_points(include_resolved: bool = False) -> list[dict]:
    sql = """SELECT w.*, c.name AS chapter_name, s.name AS subject_name, s.emoji AS subject_emoji
             FROM weak_points w JOIN chapters c ON c.id = w.chapter_id
             JOIN subjects s ON s.id = c.subject_id"""
    if not include_resolved:
        sql += " WHERE w.resolved = 0"
    sql += " ORDER BY w.created_at DESC"
    with connect() as conn:
        return _rows(conn, sql)


def resolve_weak_point(weak_id: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE weak_points SET resolved = 1 WHERE id = ?", (weak_id,))


# ---------------------------------------------------------------------------
# Fiches de révision
# ---------------------------------------------------------------------------
def save_fiche(chapter_id: int, content_md: str, source: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO fiches (chapter_id, content_md, source, created_at) VALUES (?, ?, ?, ?)",
            (chapter_id, content_md, source, _now()),
        )
        return cur.lastrowid


def list_fiches(chapter_id: int) -> list[dict]:
    with connect() as conn:
        return _rows(conn, "SELECT * FROM fiches WHERE chapter_id = ? ORDER BY created_at DESC, id DESC", (chapter_id,))


def delete_fiche(fiche_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM fiches WHERE id = ?", (fiche_id,))


# ---------------------------------------------------------------------------
# Historique de progression, activité, réglages
# ---------------------------------------------------------------------------
def upsert_snapshot(day: date, subject_id: int, score: float) -> None:
    with connect() as conn:
        conn.execute(
            """INSERT INTO progress_snapshots (snap_date, subject_id, score) VALUES (?, ?, ?)
               ON CONFLICT(snap_date, subject_id) DO UPDATE SET score = excluded.score""",
            (day.isoformat(), subject_id, score),
        )


def list_snapshots() -> list[dict]:
    with connect() as conn:
        return _rows(
            conn,
            """SELECT p.snap_date, p.score, s.name AS subject_name, s.color AS subject_color
               FROM progress_snapshots p JOIN subjects s ON s.id = p.subject_id
               ORDER BY p.snap_date, s.position""",
        )


def mark_active(day: Optional[date] = None) -> None:
    """Note qu'il y a eu du travail ce jour-là (sert à la série de jours)."""
    with connect() as conn:
        conn.execute("INSERT OR IGNORE INTO activity (day) VALUES (?)", ((day or date.today()).isoformat(),))


def list_active_days() -> list[date]:
    with connect() as conn:
        return [date.fromisoformat(r["day"]) for r in conn.execute("SELECT day FROM activity ORDER BY day")]


def get_setting(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def xp_counters() -> dict:
    """Compteurs bruts qui servent au calcul de l'XP (voir core/stats.py)."""
    with connect() as conn:
        one = lambda sql: conn.execute(sql).fetchone()[0] or 0  # noqa: E731
        return {
            "focus": one("SELECT COUNT(*) FROM focus_sessions"),
            "sessions_done": one("SELECT COUNT(*) FROM revision_sessions WHERE done = 1"),
            "quiz_points": one("SELECT SUM(score) FROM quiz_results"),
            "mastered": one("SELECT COUNT(*) FROM chapters WHERE status = 'maitrise'"),
            "fiches": one("SELECT COUNT(DISTINCT chapter_id) FROM fiches"),
        }
