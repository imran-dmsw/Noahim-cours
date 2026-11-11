"""Stockage local des cours importés (PDF, Word, PowerPoint, texte, images) dans data/cours/."""
from __future__ import annotations

import html
import logging
import os
import re
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

from core import db

COURS_DIR = Path(os.getenv("NOAHIM_COURS_DIR", db.DATA_DIR / "cours"))
TEXT_EXTENSIONS = {"txt", "md"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx"} | TEXT_EXTENSIONS | IMAGE_EXTENSIONS
MAX_UPLOAD_MB = 50

# pypdf signale bruyamment les petits défauts des PDF scolaires : on ne garde que les erreurs.
logging.getLogger("pypdf").setLevel(logging.ERROR)


def _safe_name(filename: str) -> str:
    """Nom de fichier sans accents ni caractères bizarres."""
    stem, _, ext = filename.rpartition(".")
    stem = unicodedata.normalize("NFKD", stem or filename).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-")[:60] or "cours"
    return f"{stem}.{ext.lower()}" if ext else stem


def save_upload(chapter_id: int, filename: str, data: bytes) -> Path:
    """Enregistre le fichier sur le disque et le rattache au chapitre."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formats acceptés : PDF, Word, PowerPoint, TXT, MD ou image.")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Fichier trop lourd (max {MAX_UPLOAD_MB} Mo).")
    folder = COURS_DIR / f"chapitre-{chapter_id}"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = folder / f"{stamp}_{_safe_name(filename)}"
    path.write_bytes(data)
    # Chemin relatif au projet quand c'est possible (le dossier reste déplaçable).
    stored = path.relative_to(db.ROOT_DIR) if path.is_relative_to(db.ROOT_DIR) else path
    db.add_chapter_file(chapter_id, filename, str(stored))
    return path


def delete_file(file_id: int) -> None:
    stored = db.delete_chapter_file(file_id)
    if stored:
        (db.ROOT_DIR / stored).unlink(missing_ok=True)


def extract_text(stored_path: str) -> str:
    """Texte brut d'un fichier importé (vide si illisible, ex. PDF scanné)."""
    path = db.ROOT_DIR / stored_path  # un chemin absolu reste absolu
    if not path.exists():
        return ""
    ext = path.suffix.lower().lstrip(".")
    if ext == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception:
            return ""
    if ext in ("docx", "pptx"):
        return _office_text(path, ext)
    if ext not in TEXT_EXTENSIONS:
        return ""  # images, etc. : pas de texte à extraire
    raw = path.read_bytes()
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return ""


def _office_text(path: Path, ext: str) -> str:
    """Texte d'un .docx ou .pptx : ce sont des archives zip de XML, pas besoin de librairie."""
    try:
        with zipfile.ZipFile(path) as z:
            if ext == "docx":
                parts = ["word/document.xml"]
            else:  # une entrée par diapositive, dans l'ordre
                parts = sorted(
                    (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)),
                )
            chunks = []
            for name in parts:
                xml = z.read(name).decode("utf-8", "ignore")
                # Un paragraphe (<w:p>, <a:p>) = une ligne ; on garde le texte des balises <w:t>/<a:t>.
                for para in re.findall(r"<(?:w|a):p[ >].*?</(?:w|a):p>", xml, flags=re.S):
                    line = "".join(re.findall(r"<(?:w|a):t[^>]*>([^<]*)</(?:w|a):t>", para))
                    if line.strip():
                        chunks.append(html.unescape(line))
            return "\n".join(chunks).strip()
    except (zipfile.BadZipFile, KeyError, OSError):
        return ""


def chapter_material(chapter: dict) -> str:
    """Tout ce qu'on sait d'un chapitre : notes, texte collé, fichiers importés."""
    parts = []
    if chapter.get("notes", "").strip():
        parts.append(f"## Notes de Noahim\n{chapter['notes'].strip()}")
    if chapter.get("pasted_content", "").strip():
        parts.append(f"## Contenu du cours\n{chapter['pasted_content'].strip()}")
    for f in db.list_chapter_files(chapter["id"]):
        text = extract_text(f["stored_path"])
        if text:
            parts.append(f"## Fichier : {f['filename']}\n{text}")
    return "\n\n".join(parts)
