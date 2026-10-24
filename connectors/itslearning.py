"""Squelette du connecteur It's Learning (NON BRANCHÉ, à étudier).

It's Learning propose une API REST, mais son accès dépend de ce que
l'établissement (ou la région) autorise. Pistes, de la plus simple à la plus poussée :

1. Export manuel : télécharger les ressources (PDF) et les importer dans
   « Mes cours » — déjà possible aujourd'hui, sans connecteur.
2. Flux iCalendar du calendrier It's Learning (si activé par l'établissement)
   pour récupérer les échéances et devoirs.
3. API REST officielle (OAuth2) : nécessite une application déclarée par
   l'établissement. À demander à l'administrateur ENT.

Les mêmes règles de sécurité que pour Pronote s'appliquent : aucun
identifiant en clair, jetons OAuth stockés dans le trousseau du système.
"""
from __future__ import annotations

from connectors.base import Connector, Course, Exam, Homework


class ItsLearningConnector(Connector):
    name = "It's Learning"
    icon = "🎒"
    description = ("Ressources de cours et devoirs depuis It's Learning. Méthode à définir selon "
                   "ce que l'établissement autorise (export, calendrier ou API).")
    roadmap = (
        "- Étape 1 : vérifier avec l'établissement ce qui est autorisé (export, calendrier, API)\n"
        "- Import des **ressources** dans « Mes cours » (rattachées au bon chapitre)\n"
        "- Import des **devoirs et échéances** dans le planning\n"
        "- Jetons d'accès stockés de façon chiffrée, jamais de mot de passe en clair"
    )

    def authenticate(self) -> bool:
        raise NotImplementedError("Connecteur It's Learning prévu pour une prochaine version.")

    def fetch_courses(self) -> list[Course]:
        raise NotImplementedError("Connecteur It's Learning prévu pour une prochaine version.")

    def fetch_homework(self) -> list[Homework]:
        raise NotImplementedError("Connecteur It's Learning prévu pour une prochaine version.")

    def fetch_exams(self) -> list[Exam]:
        raise NotImplementedError("Connecteur It's Learning prévu pour une prochaine version.")
