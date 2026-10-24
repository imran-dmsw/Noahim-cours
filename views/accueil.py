"""Page 1 — Accueil : le résumé du jour."""
from datetime import date

import streamlit as st

from core import db, stats, ui

today = date.today()
ui.hero("Salut Noahim 👋", f"On est {ui.french_date(today)}.", ui.quote_of_the_day(today))

progress = stats.subject_progress()
global_pct = stats.global_progress(progress)
serie = stats.current_streak(today)
lvl = stats.current_level()
upcoming = db.list_exams(upcoming_only=True, today=today)
next_exam = upcoming[0] if upcoming else None

# --- Les 4 chiffres clés ----------------------------------------------------
if next_exam:
    days_left = (date.fromisoformat(next_exam["exam_date"]) - today).days
    exam_value = "Aujourd'hui !" if days_left == 0 else f"J-{days_left}"
    exam_sub = f"{next_exam['subject_emoji']} {next_exam['title']}"
else:
    exam_value, exam_sub = "—", "ajoute-le dans Examens"
ui.metric_grid([
    ("Progression", f"{global_pct:.0f} %", "tous chapitres confondus", ui.ACCENT),
    ("Série", f"🔥 {serie} j", "jours d'affilée" if serie else "lance-toi aujourd'hui", ui.ORANGE),
    ("Prochain examen", exam_value, exam_sub, "#8b5cf6"),
    ("Niveau", f"{lvl['level']}", f"{lvl['title']} · {lvl['xp']} XP", ui.MINT),
])

left, right = st.columns([3, 2], gap="large")

# --- À faire aujourd'hui ------------------------------------------------------
with left:
    st.subheader("À faire aujourd'hui")
    todo = db.list_sessions(end=today, only_pending=True)
    done_today = [s for s in db.list_sessions(start=today, end=today) if s["done"]]

    def _toggle(session_id: int, key: str) -> None:
        checked = st.session_state[key]
        db.set_session_done(session_id, checked)
        if checked:
            stats.record_activity()
            ui.flash("+15 XP, bien joué !", "💪")

    if not todo and not done_today:
        weakest = stats.weakest_chapters(1)
        st.markdown(
            '<div class="nr-card">Rien de planifié aujourd\'hui. '
            + (f"Idée : 45 min sur <strong>{ui.esc(weakest[0]['name'])}</strong> "
               f"({ui.esc(weakest[0]['subject_name'])}), c'est ton point le plus fragile."
               if weakest else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    for s in todo:
        late = date.fromisoformat(s["session_date"]) < today
        label = f"{s['subject_emoji']} **{s['chapter_name']}** · {s['minutes']} min"
        if late:
            label += " · ⏰ en retard"
        key = f"home_s_{s['id']}"
        st.checkbox(label, value=False, key=key, on_change=_toggle, args=(s["id"], key))
    for s in done_today:
        st.markdown(f"✅ ~~{s['subject_emoji']} {s['chapter_name']}~~")
    if done_today and not todo:
        st.success("Tout est fait pour aujourd'hui. Respect 🙌")

    st.write("")
    st.page_link("views/focus.py", label="Lancer un Pomodoro", icon="⏱️")
    st.page_link("views/entrainement.py", label="Faire un quiz", icon="🎯")
    st.page_link("views/examens.py", label="Voir le planning", icon="🗓️")

# --- Matières -----------------------------------------------------------------
with right:
    st.subheader("Tes matières")
    for p in progress:
        ui.progress_card(f"{p['emoji']} {p['name']}", p["pct"], p["color"], ui.motivation(p["name"], p["pct"]))
    if len(upcoming) > 1:
        st.caption("Examens suivants : " + " · ".join(
            f"{e['subject_emoji']} {e['title']} (J-{(date.fromisoformat(e['exam_date']) - today).days})"
            for e in upcoming[1:4]
        ))
