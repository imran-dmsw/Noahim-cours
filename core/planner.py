"""Calcul automatique du plan de révision.

Tout est dans une fonction pure (`plan_revisions`) : elle ne lit ni la base
ni l'horloge, on lui passe tout en paramètre. Elle est donc facile à tester.

Principe :
1. Chaque chapitre demande un nombre de séances de 45 min selon la
   confiance de Noahim (confiance 1 → 4 séances, confiance 5 → 1 séance).
2. Le début des révisions est calculé à rebours depuis l'examen :
   assez de jours pour caser toutes les séances (2 par jour max), plus
   un jour de marge. Plus il y a de chapitres faibles, plus on commence tôt.
3. Les chapitres les plus faibles commencent au début de la période,
   les chapitres déjà solides plus tard (révision « de rappel »).
4. Les séances d'un même chapitre sont étalées dans le temps
   (répétition espacée) et jamais deux fois le même jour si possible.
5. Aucune séance le jour de l'examen : c'est le jour J, on se repose.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

SESSION_MINUTES = 45
MAX_SESSIONS_PER_DAY = 2
# Si la date est trop proche, on accepte de charger un peu plus les journées.
HARD_MAX_SESSIONS_PER_DAY = 4
SESSIONS_BY_CONFIDENCE = {1: 4, 2: 3, 3: 2, 4: 1, 5: 1}


@dataclass(frozen=True)
class ChapterInput:
    chapter_id: int
    confidence: int  # 1 (pas du tout sûr) à 5 (au top)


@dataclass(frozen=True)
class PlannedSession:
    day: date
    chapter_id: int
    minutes: int = SESSION_MINUTES


def sessions_needed(confidence: int) -> int:
    """Nombre de séances de 45 min conseillées pour un niveau de confiance."""
    return SESSIONS_BY_CONFIDENCE[min(5, max(1, int(confidence)))]


def revision_start(exam_date: date, chapters: list[ChapterInput], today: date,
                   max_per_day: int = MAX_SESSIONS_PER_DAY) -> date:
    """Premier jour de révision conseillé (jamais avant aujourd'hui)."""
    total = sum(sessions_needed(c.confidence) for c in chapters)
    days_needed = math.ceil(total / max_per_day) + 1  # +1 jour de marge
    return max(today, exam_date - timedelta(days=days_needed))


def plan_revisions(exam_date: date, chapters: list[ChapterInput], today: date,
                   session_minutes: int = SESSION_MINUTES,
                   max_per_day: int = MAX_SESSIONS_PER_DAY) -> list[PlannedSession]:
    """Construit la liste des séances, triée par date.

    Renvoie une liste vide si l'examen est aujourd'hui ou déjà passé,
    ou s'il n'y a aucun chapitre.
    """
    if not chapters or exam_date <= today:
        return []

    start = revision_start(exam_date, chapters, today, max_per_day)
    window = [start + timedelta(days=i) for i in range((exam_date - start).days)]
    total = sum(sessions_needed(c.confidence) for c in chapters)

    # Pas assez de jours ? On augmente la charge quotidienne (dans une limite raisonnable).
    per_day = max(max_per_day, math.ceil(total / len(window)))
    per_day = min(per_day, HARD_MAX_SESSIONS_PER_DAY)
    capacity = {d: per_day for d in window}
    placed: dict[date, set[int]] = {d: set() for d in window}
    plan: list[PlannedSession] = []

    # Les plus faibles d'abord : ils choisissent leurs jours en premier.
    ordered = sorted(chapters, key=lambda c: (c.confidence, c.chapter_id))
    last = len(window) - 1
    for ch in ordered:
        n = sessions_needed(ch.confidence)
        # Confiance 1 → départ au jour 0 ; confiance 5 → départ vers la moitié de la période.
        first = round(last * (min(5, max(1, ch.confidence)) - 1) / 8)
        if n == 1:
            targets = [first + (last - first) // 2]
        else:
            targets = [first + round(k * (last - first) / (n - 1)) for k in range(n)]
        for target in targets:
            day = _closest_free_day(window, target, capacity, placed, ch.chapter_id)
            if day is None:  # plus aucune place : on arrête pour ce chapitre
                break
            capacity[day] -= 1
            placed[day].add(ch.chapter_id)
            plan.append(PlannedSession(day=day, chapter_id=ch.chapter_id, minutes=session_minutes))

    return sorted(plan, key=lambda s: (s.day, s.chapter_id))


def _closest_free_day(window: list[date], target: int, capacity: dict[date, int],
                      placed: dict[date, set[int]], chapter_id: int):
    """Jour libre le plus proche de `target`, en évitant de doubler un chapitre."""
    order = sorted(range(len(window)), key=lambda i: (abs(i - target), i < target))
    # 1er passage : un jour libre sans ce chapitre ; 2e passage : n'importe quel jour libre.
    for allow_same_chapter in (False, True):
        for i in order:
            d = window[i]
            if capacity[d] > 0 and (allow_same_chapter or chapter_id not in placed[d]):
                return d
    return None
