"""Page 3 — Progression : barres, évolution dans le temps et points faibles."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import db, stats, ui

ui.page_title("Progression 📈", "Où t'en es, et ce qu'il faut reprendre en priorité.")

progress = stats.subject_progress()
global_pct = stats.global_progress(progress)

ui.progress_card("🌍 Global", global_pct, ui.ACCENT,
                 f"{sum(p['n_mastered'] for p in progress)} chapitres maîtrisés sur "
                 f"{sum(p['n_chapters'] for p in progress)}")
cols = st.columns(max(1, len(progress)))
for col, p in zip(cols, progress):
    with col:
        ui.progress_card(f"{p['emoji']} {p['name']}", p["pct"], p["color"], ui.motivation(p["name"], p["pct"]))

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=ui.TEXT),
    margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2),
    xaxis=dict(gridcolor="rgba(255,255,255,.06)"), yaxis=dict(gridcolor="rgba(255,255,255,.06)"),
)

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("Évolution")
    snaps = pd.DataFrame(db.list_snapshots())
    if snaps.empty:
        st.info("Les courbes apparaîtront dès que tu mettras à jour tes chapitres.")
    else:
        snaps["snap_date"] = pd.to_datetime(snaps["snap_date"])
        colors = {p["name"]: p["color"] for p in progress}
        fig = px.line(snaps, x="snap_date", y="score", color="subject_name", markers=True,
                      color_discrete_map=colors, labels={"snap_date": "", "score": "%", "subject_name": ""})
        fig.update_layout(**PLOT_LAYOUT, yaxis_range=[0, 100], height=340)
        fig.update_traces(line_width=3)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        if snaps["snap_date"].nunique() == 1:
            st.caption("Un seul point pour l'instant : la courbe se dessine jour après jour.")

    st.subheader("Répartition des chapitres")
    chapters = db.list_chapters()
    if chapters:
        df = pd.DataFrame(chapters)
        df["Statut"] = df["status"].map(db.STATUS_LABELS)
        counts = df.groupby(["subject_name", "Statut"]).size().reset_index(name="n")
        fig2 = go.Figure()
        for statut, color in [("Maîtrisé", ui.MINT), ("En cours", ui.ORANGE), ("À voir", "#3b556e")]:
            part = counts[counts["Statut"] == statut]
            fig2.add_bar(y=part["subject_name"], x=part["n"], name=statut, orientation="h", marker_color=color)
        fig2.update_layout(**PLOT_LAYOUT, barmode="stack", height=60 + 50 * len(progress))
        st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

with right:
    st.subheader("À retravailler en priorité")
    for c in stats.weakest_chapters(6):
        extra = f" · ❌ {c['errors']} erreur(s) en quiz" if c["errors"] else ""
        st.markdown(
            f'<div class="nr-card"><strong>{ui.esc(c["subject_emoji"])} {ui.esc(c["name"])}</strong><br>'
            f'<span class="nr-muted">{db.STATUS_EMOJIS[c["status"]]} {db.STATUS_LABELS[c["status"]]} · '
            f'confiance {c["confidence"]}/5{ui.esc(extra)}</span>{ui.bar_html(c["score"] * 100, c["subject_color"])}</div>',
            unsafe_allow_html=True,
        )

    weak = db.list_weak_points()
    st.subheader(f"Erreurs à revoir ({len(weak)})")
    if not weak:
        st.caption("Aucune pour l'instant. Les questions ratées en quiz arriveront ici.")
    for w in weak[:15]:
        with st.expander(f"{w['subject_emoji']} {w['chapter_name']} — {w['question'][:70]}"):
            st.markdown(w["question"])
            if w["detail"]:
                st.caption(w["detail"])
            if st.button("✅ C'est compris", key=f"res_{w['id']}"):
                db.resolve_weak_point(w["id"])
                st.rerun()
