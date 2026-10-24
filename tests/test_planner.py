"""Tests du plan de révision (fonction pure, pas de base de données)."""
from collections import Counter
from datetime import date, timedelta

from core.planner import (ChapterInput, HARD_MAX_SESSIONS_PER_DAY, MAX_SESSIONS_PER_DAY,
                          plan_revisions, revision_start, sessions_needed)

TODAY = date(2026, 10, 24)


def test_sessions_stay_between_today_and_exam_eve():
    exam = TODAY + timedelta(days=20)
    chapters = [ChapterInput(1, 1), ChapterInput(2, 3), ChapterInput(3, 5)]
    plan = plan_revisions(exam, chapters, TODAY)

    assert plan, "le plan ne doit pas être vide"
    assert all(TODAY <= s.day < exam for s in plan), "rien avant aujourd'hui ni le jour J"
    assert all(s.minutes == 45 for s in plan)
    # Chaque chapitre reçoit le nombre de séances prévu pour sa confiance.
    counts = Counter(s.chapter_id for s in plan)
    assert counts == {1: sessions_needed(1), 2: sessions_needed(3), 3: sessions_needed(5)}
    # Pas plus de 2 séances par jour quand on a le temps.
    assert max(Counter(s.day for s in plan).values()) <= MAX_SESSIONS_PER_DAY


def test_weaker_chapters_start_earlier():
    exam = TODAY + timedelta(days=30)
    weak, strong = ChapterInput(10, 1), ChapterInput(20, 5)
    plan = plan_revisions(exam, [strong, weak], TODAY)
    first = {cid: min(s.day for s in plan if s.chapter_id == cid) for cid in (10, 20)}
    assert first[10] < first[20]

    # Plus de chapitres faibles => on commence les révisions plus tôt.
    weak_set = [ChapterInput(i, 1) for i in range(6)]
    strong_set = [ChapterInput(i, 5) for i in range(6)]
    assert revision_start(exam, weak_set, TODAY) < revision_start(exam, strong_set, TODAY)


def test_tight_deadline_and_edge_cases():
    # Examen demain : tout tombe aujourd'hui, avec une charge plafonnée.
    plan = plan_revisions(TODAY + timedelta(days=1), [ChapterInput(1, 1), ChapterInput(2, 2)], TODAY)
    assert plan and all(s.day == TODAY for s in plan)
    assert len(plan) <= HARD_MAX_SESSIONS_PER_DAY

    # Examen passé ou sans chapitre : pas de plan.
    assert plan_revisions(TODAY, [ChapterInput(1, 1)], TODAY) == []
    assert plan_revisions(TODAY + timedelta(days=5), [], TODAY) == []
