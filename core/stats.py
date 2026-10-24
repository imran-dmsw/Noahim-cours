"""Indicateurs calculés : progression, série de jours, XP et niveaux.

Les fonctions « pures » (chapter_score, streak, level_for_xp...) ne touchent
pas à la base ; les autres assemblent les données venant de core/db.py.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Optional

from core import db

# Poids du statut dans le score d'un chapitre (le reste vient de la confiance).
STATUS_WEIGHT = {"a_voir": 0.0, "en_cours": 0.5, "maitrise": 1.0}

# XP : gamification légère, juste pour le plaisir de voir la barre monter.
XP_RULES = {
    "focus": 20,          # une séance Pomodoro terminée
    "sessions_done": 15,  # une séance du plan de révision validée
    "quiz_points": 2,     # une bonne réponse en quiz
    "mastered": 30,       # un chapitre passé en « maîtrisé »
    "fiches": 10,         # un chapitre qui a sa fiche
}
LEVEL_TITLES = ["Échauffement", "Apprenti", "Motivé", "Régulier", "Solide",
                "Costaud", "Expert", "Machine", "Légende"]


def chapter_score(status: str, confidence: int) -> float:
    """Score de 0 à 1 : 60 % le statut, 40 % la confiance."""
    conf = (min(5, max(1, int(confidence))) - 1) / 4
    return round(0.6 * STATUS_WEIGHT.get(status, 0.0) + 0.4 * conf, 4)


def subject_progress(chapters: Optional[list[dict]] = None) -> list[dict]:
    """Progression par matière (en %), dans l'ordre des matières."""
    chapters = chapters if chapters is not None else db.list_chapters()
    result = []
    for s in db.list_subjects():
        own = [c for c in chapters if c["subject_id"] == s["id"]]
        pct = 100 * sum(chapter_score(c["status"], c["confidence"]) for c in own) / len(own) if own else 0.0
        result.append({
            **s,
            "pct": round(pct, 1),
            "n_chapters": len(own),
            "n_mastered": sum(1 for c in own if c["status"] == "maitrise"),
            "n_in_progress": sum(1 for c in own if c["status"] == "en_cours"),
        })
    return result


def global_progress(progress: Optional[list[dict]] = None) -> float:
    """Moyenne pondérée par le nombre de chapitres."""
    progress = progress if progress is not None else subject_progress()
    total = sum(p["n_chapters"] for p in progress)
    if not total:
        return 0.0
    return round(sum(p["pct"] * p["n_chapters"] for p in progress) / total, 1)


def weakest_chapters(limit: int = 5) -> list[dict]:
    """Chapitres à retravailler en priorité : score faible + erreurs de quiz."""
    weak_counts: dict[int, int] = {}
    for w in db.list_weak_points():
        weak_counts[w["chapter_id"]] = weak_counts.get(w["chapter_id"], 0) + 1
    scored = []
    for c in db.list_chapters():
        score = chapter_score(c["status"], c["confidence"])
        errors = weak_counts.get(c["id"], 0)
        priority = score - 0.05 * min(errors, 6)  # chaque erreur fait remonter le chapitre
        scored.append({**c, "score": score, "errors": errors, "priority": priority})
    return sorted(scored, key=lambda c: (c["priority"], c["confidence"]))[:limit]


def refresh_snapshot(today: Optional[date] = None) -> None:
    """Enregistre la progression du jour (sert au graphique d'évolution)."""
    today = today or date.today()
    for p in subject_progress():
        db.upsert_snapshot(today, p["id"], p["pct"])


def streak(active_days: Iterable[date], today: date) -> int:
    """Nombre de jours consécutifs de travail.

    La série reste valable si Noahim n'a pas encore bossé aujourd'hui
    mais a bossé hier (on lui laisse la journée pour la prolonger).
    """
    days = set(active_days)
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def xp_from_counters(counters: dict) -> int:
    return sum(XP_RULES[k] * int(counters.get(k, 0)) for k in XP_RULES)


def level_for_xp(xp: int) -> dict:
    """Niveau n atteint à 50·n·(n−1) XP : 0, 100, 300, 600, 1000..."""
    level = 1
    while 50 * (level + 1) * level <= xp:
        level += 1
    floor = 50 * level * (level - 1)
    ceil = 50 * (level + 1) * level
    return {
        "level": level,
        "title": LEVEL_TITLES[min(level - 1, len(LEVEL_TITLES) - 1)],
        "xp": xp,
        "in_level": xp - floor,
        "to_next": ceil - floor,
        "pct": round(100 * (xp - floor) / (ceil - floor), 1),
    }


def current_level() -> dict:
    return level_for_xp(xp_from_counters(db.xp_counters()))


def current_streak(today: Optional[date] = None) -> int:
    return streak(db.list_active_days(), today or date.today())


def record_activity() -> None:
    """À appeler après toute action de travail (séance, quiz, fiche...)."""
    db.mark_active()
