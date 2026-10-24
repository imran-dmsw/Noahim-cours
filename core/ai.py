"""Appels à l'API Claude : fiches de révision et quiz.

- La clé est lue dans la variable d'environnement ANTHROPIC_API_KEY
  (fichier .env en local, « Secrets » sur Streamlit Cloud). Jamais en dur.
- Le modèle se règle avec ANTHROPIC_MODEL (par défaut claude-opus-5-5).
- Sans clé, `is_configured()` renvoie False et les pages proposent un mode manuel.
- Les appels ne partent QUE quand Noahim clique sur un bouton « Générer ».
"""
from __future__ import annotations

import os
import re
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from core.db import ROOT_DIR

load_dotenv(ROOT_DIR / ".env")

DEFAULT_MODEL = "claude-opus-5-5"


class AIError(Exception):
    """Erreur lisible à afficher telle quelle dans l'interface."""


# ---------------------------------------------------------------------------
# Formats de réponse attendus (sorties structurées validées par Pydantic)
# ---------------------------------------------------------------------------
class KeyItem(BaseModel):
    terme: str = Field(description="Formule, définition ou notion clé")
    explication: str = Field(description="Explication courte, une ou deux phrases")


class FlashQuestion(BaseModel):
    question: str
    reponse: str


class Fiche(BaseModel):
    essentiel: List[str] = Field(description="L'essentiel du chapitre en 10 lignes maximum")
    cles: List[KeyItem] = Field(description="Formules ou définitions clés")
    erreurs: List[str] = Field(description="Erreurs classiques à éviter")
    questions: List[FlashQuestion] = Field(description="Exactement 5 questions flash avec réponse")


class QCM(BaseModel):
    question: str
    choix: List[str] = Field(description="4 propositions")
    bonne_reponse: int = Field(description="Indice (0 à 3) de la bonne proposition")
    explication: str


class Exercice(BaseModel):
    enonce: str
    correction: str = Field(description="Correction détaillée étape par étape")


class Quiz(BaseModel):
    qcm: List[QCM]
    exercices: List[Exercice]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:  # Déploiement Streamlit Cloud : la clé peut être dans st.secrets
        import streamlit as st

        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def api_key() -> str:
    return _secret("ANTHROPIC_API_KEY")


def is_configured() -> bool:
    key = api_key()
    return bool(key) and not key.startswith("sk-ant-xxx")


def model_name() -> str:
    return _secret("ANTHROPIC_MODEL") or DEFAULT_MODEL


def _client():
    if not is_configured():
        raise AIError("Aucune clé API Claude n'est configurée (ANTHROPIC_API_KEY dans le fichier .env).")
    import anthropic

    return anthropic.Anthropic(api_key=api_key(), max_retries=2, timeout=180)


SYSTEM_PROMPT = (
    "Tu es un prof particulier bienveillant qui aide Noahim, élève de Première en France "
    "(spécialités Maths, Physique-Chimie, SVT), à réviser. Tu tutoies, tu es clair, concret "
    "et fidèle au programme officiel de Première. Tu écris en français. "
    "Pour les formules, utilise une notation texte lisible (ex. : f'(x) = 2x, u(n+1) = q × u(n)). "
    "Appuie-toi d'abord sur le contenu de cours fourni ; s'il est vide ou incomplet, "
    "complète avec le programme officiel du chapitre."
)


def _call(prompt: str, output_format, max_tokens: int = 8000):
    """Appel commun avec traduction des erreurs en messages compréhensibles."""
    import anthropic

    client = _client()
    try:
        response = client.messages.parse(
            model=model_name(),
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            output_format=output_format,
        )
    except anthropic.AuthenticationError:
        raise AIError("La clé API est refusée. Vérifie ANTHROPIC_API_KEY dans le fichier .env.")
    except anthropic.PermissionDeniedError:
        raise AIError("Cette clé API n'a pas accès à ce modèle. Change ANTHROPIC_MODEL dans .env.")
    except anthropic.NotFoundError:
        raise AIError(f"Modèle introuvable : « {model_name()} ». Vérifie ANTHROPIC_MODEL dans .env.")
    except anthropic.RateLimitError:
        raise AIError("Trop de demandes d'un coup. Attends une minute et réessaie.")
    except anthropic.BadRequestError as e:
        if "credit" in str(e).lower():
            raise AIError("Plus de crédit sur le compte API Anthropic.")
        raise AIError(f"Demande refusée par l'API : {e.message}")
    except anthropic.APIConnectionError:
        raise AIError("Impossible de joindre l'API Claude. Vérifie ta connexion Internet.")
    except anthropic.APIStatusError as e:
        raise AIError(f"L'API Claude a un souci (erreur {e.status_code}). Réessaie dans un moment.")

    if response.stop_reason == "refusal":
        raise AIError("Claude n'a pas voulu traiter ce contenu. Essaie avec d'autres notes de cours.")
    if response.stop_reason == "max_tokens":
        raise AIError("La réponse était trop longue et a été coupée. Réessaie avec moins de contenu.")
    if response.parsed_output is None:
        raise AIError("Réponse inattendue de l'IA. Réessaie.")
    return response.parsed_output


def _material_block(material: str) -> str:
    material = material.strip()
    if not material:
        return "(Aucun contenu importé : base-toi sur le programme officiel de Première.)"
    return f"<cours>\n{material}\n</cours>"


# ---------------------------------------------------------------------------
# Fiches
# ---------------------------------------------------------------------------
def generate_fiche(subject: str, chapter: str, material: str) -> Fiche:
    prompt = (
        f"Matière : {subject}\nChapitre : {chapter}\n\n{_material_block(material)}\n\n"
        "Fais une fiche de révision pour ce chapitre :\n"
        "- essentiel : l'essentiel à retenir en 10 lignes maximum (une idée par ligne) ;\n"
        "- cles : les formules ou définitions clés ;\n"
        "- erreurs : les erreurs classiques des élèves de Première sur ce chapitre ;\n"
        "- questions : exactement 5 questions flash (réponse courte) avec leur réponse."
    )
    return _call(prompt, Fiche)


def fiche_to_markdown(fiche: Fiche, subject: str, chapter: str) -> str:
    """Markdown de la fiche. Les réponses flash sont sur des lignes « R : » (masquées à l'écran)."""
    lines = [f"# {chapter}", f"*{subject} — fiche de révision*", "", "## 🎯 L'essentiel"]
    lines += [f"- {l}" for l in fiche.essentiel[:10]]
    lines += ["", "## 🔑 Formules et définitions clés"]
    lines += [f"- **{k.terme}** : {k.explication}" for k in fiche.cles]
    lines += ["", "## ⚠️ Erreurs classiques"]
    lines += [f"- {e}" for e in fiche.erreurs]
    lines += ["", "## ⚡ Questions flash"]
    for i, q in enumerate(fiche.questions[:5], start=1):
        lines += [f"Q{i} : {q.question}", f"R : {q.reponse}", ""]
    return "\n".join(lines).strip() + "\n"


MANUAL_TEMPLATE = """# {chapter}
*{subject} — fiche de révision*

## 🎯 L'essentiel
-
-
-

## 🔑 Formules et définitions clés
- **Notion** : explication

## ⚠️ Erreurs classiques
-

## ⚡ Questions flash
Q1 :
R :

Q2 :
R :

Q3 :
R :

Q4 :
R :

Q5 :
R :
"""


def flash_questions(markdown: str) -> list[tuple[str, str]]:
    """Récupère les paires (question, réponse) écrites « Qn : ... / R : ... »."""
    pairs, question = [], None
    for line in markdown.splitlines():
        q = re.match(r"^\s*-?\s*Q\d*\s*:\s*(.*)$", line)
        r = re.match(r"^\s*-?\s*R\s*:\s*(.*)$", line)
        if q:
            question = q.group(1).strip()
        elif r and question:
            if question and r.group(1).strip():
                pairs.append((question, r.group(1).strip()))
            question = None
    return pairs


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------
def generate_quiz(subject: str, chapter: str, material: str, n_qcm: int = 5, n_exercices: int = 2) -> Quiz:
    prompt = (
        f"Matière : {subject}\nChapitre : {chapter}\n\n{_material_block(material)}\n\n"
        f"Crée un entraînement : {n_qcm} QCM (4 propositions, une seule bonne réponse, "
        f"indice de la bonne réponse de 0 à 3, explication de la correction) et "
        f"{n_exercices} exercice(s) court(s) de niveau Première avec correction détaillée. "
        "Varie la difficulté et vise les pièges classiques."
    )
    quiz = _call(prompt, Quiz, max_tokens=12000)
    # On ne garde que les QCM bien formés (4 choix, indice valide).
    quiz.qcm = [q for q in quiz.qcm if len(q.choix) >= 2 and 0 <= q.bonne_reponse < len(q.choix)]
    if not quiz.qcm and not quiz.exercices:
        raise AIError("Le quiz généré est vide. Réessaie.")
    return quiz
