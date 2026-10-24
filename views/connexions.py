"""Page 8 — Connexions : Pronote et It's Learning (bientôt disponible).

Cette page affiche seulement l'état des connecteurs. Elle n'appelle aucun service.
"""
import streamlit as st

from connectors import available_connectors
from core import ui

ui.page_title("Connexions 🔌", "Bientôt : récupérer tes devoirs et tes contrôles automatiquement.")

st.info("Ces connexions arrivent dans une prochaine version. Pour l'instant, rien n'est connecté "
        "et aucune donnée ne sort de ton ordinateur.", icon="🚧")

for connector in available_connectors():
    status = connector.status()
    st.markdown(
        f'<div class="nr-card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.4rem">'
        f'<h3 style="margin:0">{ui.esc(connector.icon)} {ui.esc(connector.name)}</h3>'
        f'<div>{ui.badge(status.value.capitalize(), "orange")}{ui.badge("Bientôt disponible", "blue")}</div></div>'
        f'<p class="nr-muted" style="margin:.5rem 0 0">{ui.esc(connector.description)}</p></div>',
        unsafe_allow_html=True,
    )
    with st.expander(f"Ce qui est prévu pour {connector.name}"):
        st.markdown(connector.roadmap)

st.caption("🔒 Les identifiants ne seront jamais enregistrés en clair : saisie à chaque session "
           "ou stockage chiffré dans le trousseau du système.")
