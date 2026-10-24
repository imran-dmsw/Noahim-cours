"""Interface commune à tous les connecteurs (Pronote, It's Learning...).

Chaque connecteur renvoie des objets simples (Course, Homework, Exam) que
l'application pourra ensuite fusionner avec ses propres données.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ConnectorStatus(Enum):
    NOT_CONFIGURED = "non configuré"
    READY = "prêt"
    CONNECTED = "connecté"
    ERROR = "erreur"


@dataclass
class Course:
    subject: str
    title: str
    content: str = ""
    published_on: Optional[date] = None
    attachments: list[str] = field(default_factory=list)


@dataclass
class Homework:
    subject: str
    description: str
    due_date: date
    done: bool = False


@dataclass
class Exam:
    subject: str
    title: str
    exam_date: date
    chapters: list[str] = field(default_factory=list)


class Connector(ABC):
    """Contrat que chaque connecteur doit respecter."""

    name: str = "Connecteur"
    icon: str = "🔌"
    description: str = ""
    roadmap: str = ""

    def status(self) -> ConnectorStatus:
        """État affiché dans l'interface. Ne doit JAMAIS faire d'appel réseau."""
        return ConnectorStatus.NOT_CONFIGURED

    @abstractmethod
    def authenticate(self) -> bool:
        """Ouvre une session auprès du service. Renvoie True si la connexion réussit."""

    @abstractmethod
    def fetch_courses(self) -> list[Course]:
        """Récupère les cours / ressources publiés."""

    @abstractmethod
    def fetch_homework(self) -> list[Homework]:
        """Récupère le travail à faire."""

    @abstractmethod
    def fetch_exams(self) -> list[Exam]:
        """Récupère les contrôles et évaluations à venir."""
