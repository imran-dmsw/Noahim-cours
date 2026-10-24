"""Squelette du connecteur Pronote (NON BRANCHÉ).

Pronote n'a pas d'API officielle publique. La piste prévue est la
bibliothèque communautaire `pronotepy` (https://github.com/bain3/pronotepy),
non officielle : elle peut casser à chaque mise à jour de Pronote.

Sécurité des identifiants (données d'un mineur) :
- jamais de mot de passe en clair dans la base, le code ou un fichier ;
- option 1 : saisie à chaque session, gardé uniquement en mémoire ;
- option 2 : stockage dans le trousseau du système via `keyring`
  (Trousseau macOS, Gestionnaire d'identification Windows), ou chiffrement
  avec `cryptography.fernet` et une clé dérivée d'un code choisi par Noahim ;
- pronotepy permet aussi la connexion par QR code / jeton : à privilégier
  pour ne jamais manipuler le mot de passe ENT.

Esquisse d'implémentation (à valider plus tard) :

    import pronotepy
    from pronotepy.ent import ...  # selon l'ENT de l'établissement
    client = pronotepy.Client(url, username=..., password=..., ent=...)
    client.homework(date.today())          # devoirs
    client.current_period.evaluations      # évaluations
"""
from __future__ import annotations

from typing import Optional

from connectors.base import Connector, ConnectorStatus, Course, Exam, Homework


class PronoteConnector(Connector):
    name = "Pronote"
    icon = "🏫"
    description = ("Devoirs, contrôles et emploi du temps depuis Pronote, via la bibliothèque "
                   "non officielle pronotepy (Pronote ne propose pas d'API officielle).")
    roadmap = (
        "- Connexion avec l'URL Pronote de l'établissement (+ ENT si besoin) ou par QR code\n"
        "- Import du **travail à faire** dans le planning du jour\n"
        "- Import des **contrôles** dans « Examens » (avec plan de révision automatique)\n"
        "- Identifiants jamais stockés en clair : saisie à chaque session ou trousseau chiffré"
    )

    def __init__(self, url: Optional[str] = None, username: Optional[str] = None, ent: Optional[str] = None):
        # Le mot de passe n'est volontairement PAS un attribut : il sera passé
        # directement à authenticate() puis oublié.
        self.url = url
        self.username = username
        self.ent = ent
        self._client = None

    def status(self) -> ConnectorStatus:
        return ConnectorStatus.NOT_CONFIGURED if not (self.url and self.username) else ConnectorStatus.READY

    def authenticate(self, password: Optional[str] = None) -> bool:  # type: ignore[override]
        raise NotImplementedError("Connecteur Pronote prévu pour une prochaine version.")

    def fetch_courses(self) -> list[Course]:
        raise NotImplementedError("Connecteur Pronote prévu pour une prochaine version.")

    def fetch_homework(self) -> list[Homework]:
        raise NotImplementedError("Connecteur Pronote prévu pour une prochaine version.")

    def fetch_exams(self) -> list[Exam]:
        raise NotImplementedError("Connecteur Pronote prévu pour une prochaine version.")
