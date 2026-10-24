"""Connecteurs vers les services de l'établissement (seconde phase, non branchés)."""
from connectors.base import Connector, ConnectorStatus
from connectors.itslearning import ItsLearningConnector
from connectors.pronote import PronoteConnector


def available_connectors() -> list[Connector]:
    """Liste affichée sur la page Connexions. Aucun appel réseau ici."""
    return [PronoteConnector(), ItsLearningConnector()]


__all__ = ["Connector", "ConnectorStatus", "available_connectors"]
