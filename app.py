"""Noahim Revise — point d'entrée.

Lancer avec :  streamlit run app.py
"""
import streamlit as st

from core import db, stats, ui

st.set_page_config(
    page_title="Noahim Revise",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto",
)

ui.inject_css()

# Premier lancement : création de la base + programme de Première.
db.init_db()
stats.refresh_snapshot()

pages = [
    st.Page("views/accueil.py", title="Accueil", icon="🏠", default=True),
    st.Page("views/cours.py", title="Mes cours", icon="📚"),
    st.Page("views/progression.py", title="Progression", icon="📈"),
    st.Page("views/examens.py", title="Examens & planning", icon="🗓️"),
    st.Page("views/fiches.py", title="Fiches de révision", icon="📝"),
    st.Page("views/entrainement.py", title="S'entraîner", icon="🎯"),
    st.Page("views/focus.py", title="Mode focus", icon="⏱️"),
    st.Page("views/connexions.py", title="Connexions", icon="🔌"),
]
navigation = st.navigation(pages)

# Petit rappel du niveau dans la barre latérale (discret).
with st.sidebar:
    lvl = stats.current_level()
    serie = stats.current_streak()
    st.markdown(
        f'<div class="nr-card" style="margin-top:.5rem">'
        f'<div class="nr-metric-label">Niveau {lvl["level"]} · {ui.esc(lvl["title"])}</div>'
        f'{ui.bar_html(lvl["pct"])}'
        f'<div class="nr-metric-sub">{lvl["in_level"]} / {lvl["to_next"]} XP · 🔥 {serie} j</div></div>',
        unsafe_allow_html=True,
    )

ui.show_flash()
navigation.run()
