"""Thème visuel et petits composants HTML réutilisés par toutes les pages."""
from __future__ import annotations

import html
import re
from datetime import date

import streamlit as st

BG = "#0d1b2a"
SURFACE = "#13263a"
ACCENT = "#1a82d4"
MINT = "#3ddc97"
ORANGE = "#ff9f43"
TEXT = "#e8f1f8"
MUTED = "#8aa4bd"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

QUOTES = [
    "Un chapitre à la fois. C'est comme ça qu'on finit le programme.",
    "45 minutes bien faites valent mieux que 3 heures à moitié.",
    "Le Noahim de juin te remerciera pour ce que tu fais aujourd'hui.",
    "Pas besoin d'être motivé pour commencer. Commence, la motivation suit.",
    "Tu ne rates pas un exo : tu découvres ce qu'il te reste à apprendre.",
    "La régularité bat le talent quand le talent ne bosse pas.",
    "Petit effort chaque jour > gros rush la veille.",
    "Se tromper en révisant, c'est le meilleur moment pour se tromper.",
    "Ferme TikTok 25 minutes. Il sera encore là après, promis.",
    "Ce qui est dur aujourd'hui sera facile dans deux semaines.",
    "Explique-le à voix haute : si tu peux l'expliquer, tu l'as compris.",
    "Une pause, c'est pas de la triche. C'est de la stratégie.",
    "Les dérivées ne vont pas se réviser toutes seules (malheureusement).",
    "Chaque séance validée, c'est un point de plus le jour J.",
    "T'as pas besoin d'être parfait, juste d'être un peu meilleur qu'hier.",
    "Ton cerveau range ce que t'as appris pendant que tu dors. Dors bien.",
    "Commence par le plus dur, le reste paraîtra simple.",
    "Le stress, ça se transforme en préparation. Go.",
    "Un brouillon rempli vaut mieux qu'une feuille blanche.",
    "Tu progresses même quand tu ne le vois pas encore.",
]


def inject_css() -> None:
    """Polices Google (Syne + Inter), cartes, badges et ajustements mobile."""
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Syne:wght@700;800&display=swap');
html, body, .stApp, p, li, label, input, textarea, button, td, th,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {{
  font-family: 'Inter', system-ui, sans-serif;
}}
h1, h2, h3, h4, .nr-title {{
  font-family: 'Syne', 'Inter', sans-serif !important;
  font-weight: 800 !important; letter-spacing: -0.01em;
}}
h2 {{ font-size: clamp(1.3rem, 2.4vw, 1.7rem) !important; }}
h3 {{ font-size: clamp(1.1rem, 2vw, 1.35rem) !important; }}
h1, h2, h3, h4 {{ overflow-wrap: normal; word-break: normal; hyphens: none; }}
.stApp {{ background: radial-gradient(1200px 600px at 100% -10%, rgba(26,130,212,.18), transparent 60%), {BG}; }}
[data-testid="stSidebar"] {{ background: #0a1622; border-right: 1px solid rgba(255,255,255,.05); }}
.block-container {{ padding-top: 2.2rem; max-width: 1200px; }}

.nr-hero h1 {{ font-size: clamp(1.8rem, 4vw, 2.6rem) !important; margin: 0 0 .2rem 0; line-height: 1.1; padding: 0; }}
.nr-hero p {{ color: {MUTED}; font-size: 1.05rem; margin: 0; }}
.nr-quote {{ margin-top: .9rem; padding: .8rem 1rem; border-left: 3px solid {ACCENT};
  background: rgba(26,130,212,.08); border-radius: 0 12px 12px 0; color: {TEXT}; font-style: italic; }}

.nr-card {{ background: {SURFACE}; border: 1px solid rgba(255,255,255,.06); border-radius: 18px;
  padding: 1rem 1.2rem; margin-bottom: .8rem; }}
.nr-card h3, .nr-card h4 {{ margin: 0 0 .4rem 0; }}
.nr-metric-label {{ color: {MUTED}; font-size: .72rem; text-transform: uppercase; letter-spacing: .04em; font-weight: 600; }}
.nr-metric-value {{ font-family: 'Syne', sans-serif; font-weight: 800; font-size: clamp(1.3rem, 2.4vw, 2rem);
  color: {TEXT}; line-height: 1.2; white-space: nowrap; }}
.nr-pct {{ font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1.15rem; white-space: nowrap; margin-left: .5rem; }}
.nr-metric-sub {{ color: {MUTED}; font-size: .85rem; }}

.nr-bar {{ height: 10px; background: rgba(255,255,255,.08); border-radius: 99px; overflow: hidden; margin: .35rem 0 .2rem; }}
.nr-bar > span {{ display: block; height: 100%; border-radius: 99px; }}

.nr-badge {{ display: inline-block; padding: .15rem .6rem; border-radius: 99px; font-size: .78rem;
  font-weight: 600; margin-right: .3rem; background: rgba(255,255,255,.08); color: {TEXT}; }}
.nr-badge.mint {{ background: rgba(61,220,151,.15); color: {MINT}; }}
.nr-badge.orange {{ background: rgba(255,159,67,.15); color: {ORANGE}; }}
.nr-badge.blue {{ background: rgba(26,130,212,.18); color: #6cb8f5; }}
.nr-muted {{ color: {MUTED}; }}

.nr-day {{ font-family: 'Syne', sans-serif; font-weight: 800; font-size: .95rem; margin-bottom: .3rem; }}
.nr-day.today {{ color: {MINT}; }}

.nr-chip {{ background: rgba(255,255,255,.05); border-left: 3px solid {ACCENT}; border-radius: 8px;
  padding: .35rem .5rem; margin-bottom: .35rem; font-size: .8rem; line-height: 1.25; overflow-wrap: anywhere; }}
.nr-chip.done {{ opacity: .55; text-decoration: line-through; }}
.nr-chip.exam {{ border-left-color: {ORANGE}; color: {ORANGE}; font-weight: 600; }}
details.nr-flash {{ background: rgba(255,255,255,.04); border-radius: 12px; padding: .5rem .8rem; margin: .3rem 0 .8rem; }}
details.nr-flash summary {{ cursor: pointer; color: #6cb8f5; font-weight: 600; }}

div.stButton > button, div.stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {{
  border-radius: 12px; font-weight: 600;
}}
[data-testid="stExpander"] {{ border-radius: 14px; border: 1px solid rgba(255,255,255,.07); background: rgba(19,38,58,.6); }}

/* Mobile : on resserre et on réduit les titres */
@media (max-width: 640px) {{
  .block-container {{ padding: 1.2rem .8rem 3rem; }}
  .nr-hero h1 {{ font-size: 1.9rem; }}
  .nr-metric-value {{ font-size: 1.6rem; }}
  .nr-card {{ padding: .85rem .95rem; border-radius: 14px; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def esc(text) -> str:
    return html.escape(str(text))


def french_date(d: date, with_weekday: bool = True) -> str:
    base = f"{d.day} {MOIS[d.month - 1]}"
    return f"{JOURS[d.weekday()]} {base}" if with_weekday else base


def quote_of_the_day(d: date) -> str:
    return QUOTES[d.toordinal() % len(QUOTES)]


def hero(title: str, subtitle: str = "", quote: str = "") -> None:
    block = f'<div class="nr-hero"><h1>{esc(title)}</h1>'
    if subtitle:
        block += f"<p>{esc(subtitle)}</p>"
    if quote:
        block += f'<div class="nr-quote">« {esc(quote)} »</div>'
    st.markdown(block + "</div>", unsafe_allow_html=True)


def page_title(title: str, subtitle: str = "") -> None:
    hero(title, subtitle)
    st.write("")


def metric_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="nr-card"><div class="nr-metric-label">{esc(label)}</div>'
        f'<div class="nr-metric-value">{esc(value)}</div>'
        f'<div class="nr-metric-sub">{esc(sub)}</div></div>',
        unsafe_allow_html=True,
    )


def bar_html(pct: float, color: str = ACCENT) -> str:
    pct = max(0.0, min(100.0, float(pct)))
    return (f'<div class="nr-bar"><span style="width:{pct:.1f}%;'
            f'background:linear-gradient(90deg,{color},{MINT})"></span></div>')


def progress_card(title: str, pct: float, color: str = ACCENT, sub: str = "") -> None:
    st.markdown(
        f'<div class="nr-card"><div style="display:flex;justify-content:space-between;align-items:baseline">'
        f'<strong>{esc(title)}</strong><span class="nr-pct">{pct:.0f}&nbsp;%</span></div>'
        f'{bar_html(pct, color)}<div class="nr-metric-sub">{esc(sub)}</div></div>',
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "") -> str:
    return f'<span class="nr-badge {kind}">{esc(text)}</span>'


def motivation(subject: str, pct: float) -> str:
    """Petite phrase décontractée selon l'avancement d'une matière."""
    if pct >= 85:
        return f"{subject} à {pct:.0f} %, t'es quasi au top 🏆"
    if pct >= 60:
        return f"T'as déjà fait {pct:.0f} % de {subject}, continue 🔥"
    if pct >= 30:
        return f"{subject} à {pct:.0f} % : la moitié du chemin approche 💪"
    if pct > 0:
        return f"{subject} démarre ({pct:.0f} %), chaque chapitre compte 🚀"
    return f"{subject} t'attend, lance un premier chapitre 👀"


def render_fiche(markdown: str) -> None:
    """Affiche une fiche : les lignes « R : ... » deviennent des réponses masquées."""
    out = []
    for line in markdown.splitlines():
        m = re.match(r"^\s*-?\s*R\s*:\s*(.*)$", line)
        if m:
            out.append(f'<details class="nr-flash"><summary>Voir la réponse</summary>{esc(m.group(1))}</details>')
        elif re.match(r"^\s*-?\s*Q\d*\s*:", line):
            out.append(f"**{line.strip()}**")
        else:
            out.append(line)
    st.markdown("\n".join(out), unsafe_allow_html=True)


def flash(message: str, icon: str = "✅") -> None:
    """Message affiché après le prochain rechargement (st.toast + st.rerun)."""
    st.session_state["_flash"] = (message, icon)


def show_flash() -> None:
    if "_flash" in st.session_state:
        message, icon = st.session_state.pop("_flash")
        st.toast(message, icon=icon)
