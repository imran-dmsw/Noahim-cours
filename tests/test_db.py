"""Démarrage sur base vide + calculs de progression / série / XP."""
from datetime import date, timedelta

import pytest

from core import db, stats


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    return db


def test_first_launch_seeds_programme(fresh_db):
    subjects = {s["name"] for s in db.list_subjects()}
    assert subjects == {"Maths", "Physique-Chimie", "SVT"}
    assert len(db.list_chapters()) == 20
    db.init_db()  # relancer ne doit rien dupliquer
    assert len(db.list_chapters()) == 20


def test_progress_reacts_to_chapter_updates(fresh_db):
    assert stats.global_progress() == 0
    ch = db.list_chapters()[0]
    db.update_chapter(ch["id"], status="maitrise", confidence=5)
    maths = next(p for p in stats.subject_progress() if p["name"] == "Maths")
    assert maths["pct"] == 10.0  # 1 chapitre sur 10 à 100 %
    assert stats.weakest_chapters(1)[0]["id"] != ch["id"]


def test_streak_and_levels():
    today = date(2026, 10, 24)
    days = [today - timedelta(days=i) for i in (1, 2, 3, 5)]
    assert stats.streak(days, today) == 3          # hier, avant-hier, J-3
    assert stats.streak(days + [today], today) == 4
    assert stats.level_for_xp(0)["level"] == 1
    assert stats.level_for_xp(100)["level"] == 2
    assert stats.level_for_xp(299)["level"] == 2
    assert stats.level_for_xp(300)["level"] == 3
