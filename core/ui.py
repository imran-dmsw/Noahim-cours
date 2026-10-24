"""Thème visuel et petits composants HTML réutilisés par toutes les pages."""
from __future__ import annotations

import html
import re
from datetime import date

import streamlit as st

BG = "#f5f8fc"
SURFACE = "#ffffff"
BORDER = "#e3eaf2"
ACCENT = "#1a82d4"
ACCENT_DARK = "#0f5fa8"
MINT = "#1fbf7a"        # barres et graphiques
MINT_TEXT = "#0f8a56"   # texte vert lisible sur fond clair
ORANGE = "#ff9f43"
ORANGE_TEXT = "#b95f0b"
TEXT = "#0f1f33"
MUTED = "#5b6b80"
TRACK = "#edf2f8"       # fond des barres de progression

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
    """Thème clair : police Inter (via .streamlit/config.toml), cartes, badges, mobile."""
    st.markdown(
        f"""
<style>
h1, h2, h3, h4 {{ letter-spacing: -0.02em; color: {TEXT}; overflow-wrap: normal; word-break: normal; }}
h2 {{ font-size: clamp(1.25rem, 2.2vw, 1.55rem) !important; }}
h3 {{ font-size: clamp(1.05rem, 1.8vw, 1.2rem) !important; }}
.stApp {{ background: {BG}; }}
.block-container {{ padding-top: 2rem; max-width: 1180px; }}

/* En-tête de page */
.nr-head h1 {{ font-size: clamp(1.6rem, 3.2vw, 2.1rem) !important; margin: 0; padding: 0; line-height: 1.15; }}
.nr-head p {{ color: {MUTED}; font-size: 1rem; margin: .25rem 0 0; }}

/* Bannière d'accueil */
.nr-hero {{ position: relative; overflow: hidden; border-radius: 22px; padding: 1.8rem 1.9rem 1.6rem;
  color: #fff; background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT_DARK} 100%);
  box-shadow: 0 12px 32px rgba(26,130,212,.25); }}
.nr-hero::after {{ content: ""; position: absolute; right: -60px; top: -80px; width: 260px; height: 260px;
  border-radius: 50%; background: rgba(255,255,255,.10); }}
.nr-hero::before {{ content: ""; position: absolute; right: 90px; bottom: -110px; width: 200px; height: 200px;
  border-radius: 50%; background: rgba(31,191,122,.25); }}
.nr-hero h1 {{ color: #fff !important; font-size: clamp(1.8rem, 4vw, 2.5rem) !important; margin: 0; padding: 0;
  line-height: 1.1; position: relative; z-index: 1; }}
.nr-hero p {{ color: rgba(255,255,255,.85); font-size: 1.02rem; margin: .3rem 0 0; position: relative; z-index: 1; }}
.nr-quote {{ display: inline-block; margin-top: 1rem; padding: .55rem .9rem; border-radius: 12px; position: relative; z-index: 1;
  background: rgba(255,255,255,.16); color: #fff; font-weight: 500; backdrop-filter: blur(4px); }}

/* Cartes */
.nr-card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px; padding: 1rem 1.15rem;
  margin-bottom: .8rem; box-shadow: 0 1px 2px rgba(15,31,51,.04), 0 6px 18px rgba(15,31,51,.04); }}
.nr-card h3, .nr-card h4 {{ margin: 0 0 .4rem 0; padding: 0; }}
.nr-metric-label {{ color: {MUTED}; font-size: .74rem; text-transform: uppercase; letter-spacing: .05em; font-weight: 600; }}
.nr-metric-value {{ font-weight: 800; font-size: clamp(1.4rem, 2.4vw, 1.9rem); color: {TEXT};
  line-height: 1.2; white-space: nowrap; letter-spacing: -0.02em; margin: .15rem 0; }}
.nr-metric-sub {{ color: {MUTED}; font-size: .85rem; }}
.nr-pct {{ font-weight: 800; font-size: 1.1rem; white-space: nowrap; margin-left: .5rem; color: {TEXT}; }}
.nr-accent {{ border-top: 3px solid {ACCENT}; }}
.nr-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; margin: 1rem 0 1.2rem; }}
@media (min-width: 1100px) {{ .nr-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }} }}

/* Barres de progression */
.nr-bar {{ height: 9px; background: {TRACK}; border-radius: 99px; overflow: hidden; margin: .45rem 0 .3rem; }}
.nr-bar > span {{ display: block; height: 100%; border-radius: 99px; }}

/* Badges */
.nr-badge {{ display: inline-block; padding: .18rem .6rem; border-radius: 99px; font-size: .76rem;
  font-weight: 600; margin: 0 .3rem .2rem 0; background: {TRACK}; color: {TEXT}; }}
.nr-badge.mint {{ background: rgba(31,191,122,.12); color: {MINT_TEXT}; }}
.nr-badge.orange {{ background: rgba(255,159,67,.15); color: {ORANGE_TEXT}; }}
.nr-badge.blue {{ background: rgba(26,130,212,.10); color: {ACCENT_DARK}; }}
.nr-muted {{ color: {MUTED}; }}

/* Planning */
.nr-day {{ font-weight: 700; font-size: .9rem; margin-bottom: .35rem; color: {TEXT}; }}
.nr-day.today {{ color: {ACCENT}; }}
.nr-chip {{ background: {SURFACE}; border: 1px solid {BORDER}; border-left: 3px solid {ACCENT}; border-radius: 8px;
  padding: .35rem .5rem; margin-bottom: .35rem; font-size: .8rem; line-height: 1.25; overflow-wrap: anywhere; }}
.nr-chip.done {{ opacity: .5; text-decoration: line-through; }}
.nr-chip.exam {{ border-left-color: {ORANGE}; color: {ORANGE_TEXT}; font-weight: 600; background: rgba(255,159,67,.08); }}

/* Questions flash */
details.nr-flash {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 12px; padding: .5rem .8rem; margin: .3rem 0 .8rem; }}
details.nr-flash summary {{ cursor: pointer; color: {ACCENT}; font-weight: 600; }}

/* Boutons et blocs Streamlit */
div.stButton > button, div.stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {{ font-weight: 600; }}
[data-testid="stExpander"] details {{ background: {SURFACE}; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ background: {SURFACE}; }}

/* Mobile */
@media (max-width: 640px) {{
  .block-container {{ padding: 1.1rem .8rem 3rem; }}
  .nr-hero {{ padding: 1.3rem 1.2rem 1.2rem; border-radius: 18px; }}
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
    """Bannière bleue de la page d'accueil."""
    block = f'<div class="nr-hero"><h1>{esc(title)}</h1>'
    if subtitle:
        block += f"<p>{esc(subtitle)}</p>"
    if quote:
        block += f'<div class="nr-quote">💬 {esc(quote)}</div>'
    st.markdown(block + "</div>", unsafe_allow_html=True)


def page_title(title: str, subtitle: str = "") -> None:
    """En-tête sobre des autres pages."""
    block = f'<div class="nr-head"><h1>{esc(title)}</h1>'
    if subtitle:
        block += f"<p>{esc(subtitle)}</p>"
    st.markdown(block + "</div>", unsafe_allow_html=True)
    st.write("")


def metric_card(label: str, value: str, sub: str = "", color: str = ACCENT) -> None:
    st.markdown(
        f'<div class="nr-card nr-accent" style="border-top-color:{color}"><div class="nr-metric-label">{esc(label)}</div>'
        f'<div class="nr-metric-value">{esc(value)}</div>'
        f'<div class="nr-metric-sub">{esc(sub)}</div></div>',
        unsafe_allow_html=True,
    )


def metric_grid(items: list[tuple[str, str, str, str]]) -> None:
    """Cartes de chiffres clés (label, valeur, sous-titre, couleur) qui passent à la ligne selon la largeur."""
    cards = "".join(
        f'<div class="nr-card nr-accent" style="border-top-color:{color};margin:0">'
        f'<div class="nr-metric-label">{esc(label)}</div><div class="nr-metric-value">{esc(value)}</div>'
        f'<div class="nr-metric-sub">{esc(sub)}</div></div>'
        for label, value, sub, color in items
    )
    st.markdown(f'<div class="nr-grid">{cards}</div>', unsafe_allow_html=True)


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
