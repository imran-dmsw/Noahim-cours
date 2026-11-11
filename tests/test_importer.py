"""Import d'un dossier de cours : rapprochement des matières/chapitres et absence de doublons."""
import plistlib
import zipfile

import pytest

from core import db, files, importer


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(files, "COURS_DIR", tmp_path / "stockage")
    db.init_db()


@pytest.fixture()
def course_folder(tmp_path):
    root = tmp_path / "cours Noahim"
    (root / "Maths (spé)" / "Le Second degré" / "DS").mkdir(parents=True)
    (root / "Maths (spé)" / "Le Second degré" / "DS" / "sujet.pdf").write_bytes(b"%PDF-1.4 test")
    (root / "Maths (spé)" / "Progression.pdf").write_bytes(b"%PDF-1.4 test")
    chap = root / "SVT (spé)" / "Thème 1 - Le vivant" / "Partie 1 - Transmission, variation et expression du patrimoine génétique"
    chap.mkdir(parents=True)
    (chap / "cours.txt").write_text("La mitose produit deux cellules filles.")
    (chap / "Vidéo.webloc").write_bytes(plistlib.dumps({"URL": "https://www.youtube.com/watch?v=x&t=1"}))
    (chap / "film.mp4").write_bytes(b"0000")
    (root / "Classe (espace commun)" / "HISTOIRE" / "Thème 1").mkdir(parents=True)
    (root / "Classe (espace commun)" / "HISTOIRE" / "Thème 1" / "cours.docx").write_bytes(b"PK")
    (root / "À lire.txt").write_text("résumé")
    return root


def _plan(root):
    return importer.plan_import(root, db.list_subjects(), db.list_chapters())


def test_plan_matches_existing_subjects_and_chapters(fresh_db, course_folder):
    by_name = {p.source.name: p for p in _plan(course_folder)}
    assert "À lire.txt" not in by_name
    # « Maths (spé) » -> Maths ; le sous-dossier DS remonte au chapitre « Second degré »
    assert (by_name["sujet.pdf"].subject, by_name["sujet.pdf"].chapter) == ("Maths", "Second degré")
    assert not by_name["sujet.pdf"].new_chapter
    assert by_name["Progression.pdf"].chapter == importer.DEFAULT_CHAPTER
    # SVT : c'est le sous-dossier le plus profond qui correspond au chapitre existant
    assert by_name["cours.txt"].chapter == "Transmission, variation et expression du patrimoine génétique"
    assert by_name["Vidéo.webloc"].kind == "lien"
    assert by_name["film.mp4"].kind == "ignoré"
    # L'espace commun : chaque sous-dossier devient une matière
    assert by_name["cours.docx"].subject == "Histoire" and by_name["cours.docx"].new_subject


def test_apply_is_idempotent(fresh_db, course_folder):
    first = importer.apply_import(_plan(course_folder))
    assert first["fichiers"] == 4 and first["liens"] == 1 and first["ignorés"] == 1
    assert first["matières créées"] == 1  # Histoire

    second = importer.apply_import(_plan(course_folder))
    assert second["fichiers"] == 0 and second["liens"] == 0
    assert second["matières créées"] == 0 and second["chapitres créés"] == 0

    svt = next(c for c in db.list_chapters() if c["name"].startswith("Transmission"))
    assert svt["pasted_content"].count("youtube.com") == 1
    assert [f["filename"] for f in db.list_chapter_files(svt["id"])] == ["cours.txt"]


def test_office_text_extraction(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "ROOT_DIR", tmp_path)
    with zipfile.ZipFile(tmp_path / "c.docx", "w") as z:
        z.writestr("word/document.xml",
                   "<w:document><w:body><w:p><w:r><w:t>Dérivée de x²</w:t></w:r></w:p>"
                   "<w:p><w:r><w:t>f'(x) = 2x &amp; plus</w:t></w:r></w:p></w:body></w:document>")
    with zipfile.ZipFile(tmp_path / "c.pptx", "w") as z:
        z.writestr("ppt/slides/slide2.xml", "<p:sld><a:p><a:r><a:t>Diapo 2</a:t></a:r></a:p></p:sld>")
        z.writestr("ppt/slides/slide1.xml", "<p:sld><a:p><a:r><a:t>Diapo 1</a:t></a:r></a:p></p:sld>")
    assert files.extract_text("c.docx") == "Dérivée de x²\nf'(x) = 2x & plus"
    assert files.extract_text("c.pptx") == "Diapo 1\nDiapo 2"
