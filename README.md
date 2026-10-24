# Noahim Revise 📚

Dashboard de révision pour Noahim (Première, spécialités Maths, Physique-Chimie, SVT) :
chapitres, progression, plan de révision automatique, fiches et quiz générés par Claude,
minuteur Pomodoro et un peu d'XP pour la motivation.

## Installation

Il faut Python 3.11 ou plus récent.

```bash
cd noahim-revise
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

L'appli s'ouvre sur http://localhost:8501. Au premier lancement, la base `data/noahim.db`
est créée avec le programme de Première (20 chapitres, tout est modifiable).

Pour l'ouvrir depuis un téléphone sur le même Wi-Fi : utilise l'adresse « Network URL »
affichée par Streamlit (ex. `http://192.168.1.20:8501`).

## Clé API Claude (facultatif)

Les fiches et quiz automatiques utilisent l'API Claude. Sans clé, l'appli marche quand même :
fiches manuelles avec un modèle à remplir, interro sur les questions flash.

1. Crée une clé sur https://platform.claude.com (rubrique API Keys).
2. Copie `.env.example` en `.env` et colle la clé :
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ANTHROPIC_MODEL=claude-opus-5-5
   ```
3. Relance l'appli.

Le fichier `.env` est ignoré par git : la clé n'est jamais commitée ni écrite dans le code.

## Ajouter des cours

Dans **Mes cours** :
- ouvre un chapitre, change le statut (à voir / en cours / maîtrisé) et la confiance (1 à 5) ;
- écris tes notes ou colle le texte d'un cours ;
- importe des fichiers **PDF, TXT ou MD** (stockés dans `data/cours/`) ;
- ajoute, renomme ou supprime des chapitres en bas de chaque matière, et des matières dans l'onglet « Gérer les matières ».

Plus tu remplis, meilleures sont les fiches et les quiz. Un PDF scanné (image) n'a pas de texte lisible :
colle le contenu à la main dans ce cas.

## Données personnelles

Noahim est mineur : tout reste **sur l'ordinateur**.
- La base SQLite et les cours importés sont dans `data/`, jamais commités.
- Aucun service tiers, aucun suivi, aucune statistique d'usage (désactivée dans `.streamlit/config.toml`).
- **Seule exception** : quand Noahim clique sur « Générer la fiche » ou « Générer un quiz », le contenu
  **de ce chapitre** (notes, texte collé, fichiers) est envoyé à l'API Claude d'Anthropic pour produire la réponse.
  Rien d'autre n'est envoyé, et rien ne part sans ce clic.
- Les connecteurs Pronote / It's Learning ne sont pas branchés. Quand ils le seront, les identifiants
  ne seront jamais stockés en clair (saisie à chaque session ou trousseau chiffré).

## Tests

```bash
pytest
```

Le plan de révision (`core/planner.py`) est une fonction pure testée dans `tests/test_planner.py`.

## Structure

```
app.py               point d'entrée + navigation
views/               une page par fichier (accueil, cours, progression, examens, fiches, entraînement, focus, connexions)
                     (dossier nommé views/ et non pages/ : sinon Streamlit active son ancien mode
                     multipage et casse les liens directs vers une page)
core/db.py           SQLite + migrations + données de départ
core/planner.py      calcul du plan de révision
core/ai.py           appels API Claude (fiches, quiz)
core/pdf.py          export PDF des fiches
core/files.py        stockage et lecture des cours importés
core/stats.py        progression, série de jours, XP
core/ui.py           thème et composants visuels
connectors/          interface Connector + squelettes Pronote et It's Learning
```

## Déployer plus tard

**Streamlit Community Cloud** (gratuit) :
1. Pousse le projet sur un dépôt GitHub **privé** (le `.gitignore` exclut `.env` et `data/`).
2. Sur https://share.streamlit.io, crée une app pointant sur `app.py`.
3. Dans *Settings → Secrets*, ajoute `ANTHROPIC_API_KEY = "sk-ant-..."`.
4. Restreins l'accès (*Sharing → Only specific people*).

⚠️ Sur Streamlit Cloud, le disque est effacé à chaque redémarrage : la base SQLite serait perdue.
Avant de déployer, il faudra soit une base hébergée (ex. Postgres / Supabase), soit garder l'appli en local.
Autre option simple : un petit serveur perso (Raspberry Pi, VPS) avec `streamlit run app.py`
derrière un mot de passe.
