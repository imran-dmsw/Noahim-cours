"""Import d'un dossier de cours (ex. ~/Documents/cours Noahim) dans l'appli.

Structure attendue : un dossier par matière, puis des sous-dossiers de chapitres.
    cours Noahim/
        Maths (spé)/Le Second degré/DS/sujet.pdf
        SVT (spé)/Thème 1 - .../Partie 1 - Transmission.../cours.pptx
        Classe 1ère 5 (espace commun)/HISTOIRE/...   <- « espace commun » : chaque
                                                       sous-dossier est une matière

Règles :
- matière : rapprochée d'une matière existante (« Maths (spé) » -> « Maths »),
  sinon créée ;
- chapitre : le sous-dossier le plus profond qui correspond à un chapitre
  existant, sinon le premier sous-dossier (créé au besoin), sinon
  « Documents généraux » pour les fichiers posés à la racine de la matière ;
- les liens .webloc sont ajoutés au « contenu du cours » du chapitre ;
- relancer l'import ne crée pas de doublon (même nom de fichier = ignoré).

`plan_import` est une fonction pure (testable) ; `apply_import` écrit en base.
"""
from __future__ import annotations

import plistlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from core import db, files

DEFAULT_CHAPTER = "Documents généraux"
LINKS_HEADER = "Liens importés :"
SHARED_MARKER = "espace commun"
# Noms plus jolis pour les matières écrites en capitales dans It's Learning.
PRETTY_SUBJECTS = {"histoire": "Histoire", "geographie": "Géographie", "emc": "EMC"}
SKIPPED_NAMES = {"À lire.txt", "A lire.txt", ".DS_Store"}


@dataclass
class PlannedItem:
    kind: str                 # "fichier", "lien" ou "ignoré"
    source: Path
    subject: str
    chapter: str
    new_subject: bool = False
    new_chapter: bool = False
    url: str = ""
    reason: str = ""


def _norm(text: str) -> str:
    """Forme simplifiée pour comparer des noms : sans accents, préfixes ni ponctuation."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"^\s*(theme|chapitre|partie|axis|unit|tema)\s*\d+\s*[:\-–.]*\s*", "", text)
    text = re.sub(r"^\s*(le|la|les|l'|un|une|des)\s+|^l'", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _same(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if min(len(a), len(b)) >= 6 and (a in b or b in a):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.85


def _subject_label(folder: str) -> str:
    base = re.sub(r"\s*\(.*?\)\s*", " ", folder).strip()
    return PRETTY_SUBJECTS.get(_norm(base), base)


def _webloc_url(path: Path) -> str:
    try:
        return plistlib.loads(path.read_bytes()).get("URL", "")
    except Exception:
        return ""


def plan_import(root: Path, subjects: list[dict], chapters: list[dict]) -> list[PlannedItem]:
    """Calcule où chaque fichier du dossier `root` sera rangé, sans rien écrire."""
    known_subjects = {s["name"]: s["id"] for s in subjects}
    chapters_by_subject: dict[str, list[str]] = {}
    for c in chapters:
        name = next((s["name"] for s in subjects if s["id"] == c["subject_id"]), None)
        if name:
            chapters_by_subject.setdefault(name, []).append(c["name"])
    created_subjects: set[str] = set()
    created_chapters: set[tuple[str, str]] = set()
    plan: list[PlannedItem] = []

    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).parts
        if path.name in SKIPPED_NAMES or path.name.startswith(".") or len(rel) < 2:
            continue
        folders = list(rel[:-1])
        if SHARED_MARKER in folders[0].lower() and len(folders) > 1:
            folders = folders[1:]  # l'espace commun regroupe plusieurs matières
        label = _subject_label(folders[0])
        subject = next((s for s in list(known_subjects) + sorted(created_subjects) if _same(s, label)), None)
        new_subject = subject is None
        if new_subject:
            subject = label
            created_subjects.add(subject)

        existing = chapters_by_subject.get(subject, []) + [c for s, c in created_chapters if s == subject]
        chapter = None
        for folder in reversed(folders[1:]):  # du plus précis au plus général
            chapter = next((c for c in existing if _same(c, folder)), None)
            if chapter:
                break
        if chapter is None:
            chapter = re.sub(r"\s{2,}", " ", folders[1]).strip() if len(folders) > 1 else DEFAULT_CHAPTER
            chapter = next((c for c in existing if c == chapter), chapter)
        new_chapter = chapter not in existing
        if new_chapter:
            created_chapters.add((subject, chapter))

        item = PlannedItem("fichier", path, subject, chapter, new_subject, new_chapter)
        ext = path.suffix.lower().lstrip(".")
        if ext == "webloc":
            item.kind, item.url = "lien", _webloc_url(path)
            if not item.url:
                item.kind, item.reason = "ignoré", "lien illisible"
        elif ext not in files.ALLOWED_EXTENSIONS:
            item.kind, item.reason = "ignoré", f"format .{ext} non pris en charge"
        elif path.stat().st_size > files.MAX_UPLOAD_MB * 1024 * 1024:
            item.kind, item.reason = "ignoré", f"plus de {files.MAX_UPLOAD_MB} Mo"
        plan.append(item)
    return plan


def _already_imported(chapter_id: int, source: Path) -> bool:
    """Même nom et même taille qu'un fichier déjà rattaché au chapitre (deux devoirs
    peuvent joindre des fichiers homonymes au contenu différent)."""
    size = source.stat().st_size
    for f in db.list_chapter_files(chapter_id):
        stored = db.ROOT_DIR / f["stored_path"]
        if f["filename"] == source.name and stored.exists() and stored.stat().st_size == size:
            return True
    return False


def apply_import(plan: list[PlannedItem], progress=None) -> dict:
    """Applique le plan : crée matières et chapitres, copie les fichiers, ajoute les liens."""
    subject_ids = {s["name"]: s["id"] for s in db.list_subjects()}
    chapter_ids = {(c["subject_name"], c["name"]): c["id"] for c in db.list_chapters()}
    report = {"fichiers": 0, "liens": 0, "déjà là": 0, "ignorés": 0,
              "matières créées": 0, "chapitres créés": 0, "erreurs": []}
    links_by_chapter: dict[int, list[str]] = {}

    for i, item in enumerate(plan):
        if progress:
            progress(i + 1, len(plan), item.source.name)
        if item.kind == "ignoré":
            report["ignorés"] += 1
            continue
        if item.subject not in subject_ids:
            subject_ids[item.subject] = db.add_subject(item.subject, "📘")
            report["matières créées"] += 1
        key = (item.subject, item.chapter)
        if key not in chapter_ids:
            chapter_ids[key] = db.add_chapter(subject_ids[item.subject], item.chapter)
            report["chapitres créés"] += 1
        chapter_id = chapter_ids[key]

        if item.kind == "lien":
            links_by_chapter.setdefault(chapter_id, []).append(f"- {item.source.stem} : {item.url}")
            continue
        if _already_imported(chapter_id, item.source):
            report["déjà là"] += 1
            continue
        try:
            files.save_upload(chapter_id, item.source.name, item.source.read_bytes())
            report["fichiers"] += 1
        except Exception as exc:
            report["erreurs"].append(f"{item.source.name} : {exc}")

    # Les liens rejoignent le « contenu du cours » du chapitre, sans doublon.
    for chapter_id, lines in links_by_chapter.items():
        chapter = db.get_chapter(chapter_id)
        content = chapter["pasted_content"]
        new = [line for line in lines if line.split(" : ", 1)[-1] not in content]
        if not new:
            report["déjà là"] += len(lines)
            continue
        if LINKS_HEADER not in content:
            content = (content.rstrip() + "\n\n" if content.strip() else "") + LINKS_HEADER
        db.update_chapter(chapter_id, pasted_content=content + "\n" + "\n".join(new))
        report["liens"] += len(new)
        report["déjà là"] += len(lines) - len(new)
    return report


def summary(plan: list[PlannedItem]) -> list[dict]:
    """Une ligne par chapitre pour l'aperçu avant import."""
    rows: dict[tuple[str, str], dict] = {}
    for item in plan:
        row = rows.setdefault((item.subject, item.chapter), {
            "Matière": item.subject + (" (nouvelle)" if item.new_subject else ""),
            "Chapitre": item.chapter + (" (nouveau)" if item.new_chapter else ""),
            "Fichiers": 0, "Liens": 0, "Ignorés": 0,
        })
        row[{"fichier": "Fichiers", "lien": "Liens", "ignoré": "Ignorés"}[item.kind]] += 1
    return list(rows.values())


def default_folder() -> Optional[Path]:
    """Dossier proposé par défaut s'il existe sur cet ordinateur."""
    candidate = Path.home() / "Documents" / "cours Noahim"
    return candidate if candidate.is_dir() else None
