"""Page 4 — Examens et planning de révision automatique."""
from datetime import date, timedelta

import streamlit as st

from core import db, planner, stats, ui

ui.page_title("Examens & planning 🗓️",
              "Ajoute tes contrôles : l'appli calcule quand commencer et quoi réviser chaque jour.")

today = date.today()


def build_plan(exam_id: int, exam_date: date) -> int:
    """(Re)calcule les séances non faites d'un examen à partir des confiances actuelles."""
    chapters = db.exam_chapters(exam_id)
    plan = planner.plan_revisions(
        exam_date,
        [planner.ChapterInput(c["id"], c["confidence"]) for c in chapters],
        today=today,
    )
    db.replace_pending_sessions(exam_id, [(s.day, s.chapter_id, s.minutes) for s in plan])
    return len(plan)


# --- Ajout d'un examen ------------------------------------------------------------
with st.expander("➕ Ajouter un examen", expanded=not db.list_exams(upcoming_only=True)):
    subjects = db.list_subjects()
    subject = st.selectbox("Matière", subjects, format_func=lambda s: f"{s['emoji']} {s['name']}")
    chapters = db.list_chapters(subject["id"]) if subject else []
    with st.form("add_exam", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        title = c1.text_input("Intitulé", placeholder="ex. DS de maths, bac blanc…")
        exam_date = c2.date_input("Date", value=today + timedelta(days=14), min_value=today,
                                  format="DD/MM/YYYY")
        selected = st.multiselect("Chapitres concernés", chapters,
                                  format_func=lambda c: f"{c['name']} (confiance {c['confidence']}/5)")
        if st.form_submit_button("Créer l'examen et mon plan", type="primary"):
            if not selected:
                st.error("Choisis au moins un chapitre.")
            else:
                exam_id = db.add_exam(subject["id"], title or f"Examen de {subject['name']}", exam_date,
                                      [c["id"] for c in selected])
                n = build_plan(exam_id, exam_date)
                start = planner.revision_start(
                    exam_date, [planner.ChapterInput(c["id"], c["confidence"]) for c in selected], today)
                ui.flash(f"Plan prêt : {n} séances de 45 min, début {ui.french_date(start)}", "🗓️")
                st.rerun()

# --- Examens à venir ------------------------------------------------------------------
exams = db.list_exams(upcoming_only=True, today=today)
if exams:
    st.subheader("Examens à venir")
    cols = st.columns(min(3, len(exams)))
    for i, e in enumerate(exams):
        d = date.fromisoformat(e["exam_date"])
        days_left = (d - today).days
        with cols[i % len(cols)]:
            pct = 100 * e["n_done"] / e["n_sessions"] if e["n_sessions"] else 0
            chapter_names = ", ".join(c["name"] for c in db.exam_chapters(e["id"]))
            st.markdown(
                f'<div class="nr-card"><div class="nr-metric-label">{ui.esc(e["subject_emoji"])} '
                f'{ui.esc(e["subject_name"])}</div><h4>{ui.esc(e["title"])}</h4>'
                f'{ui.badge("Aujourd" + chr(39) + "hui" if days_left == 0 else f"J-{days_left}", "orange")}'
                f'{ui.badge(ui.french_date(d), "blue")}'
                f'{ui.bar_html(pct, e["subject_color"])}'
                f'<div class="nr-metric-sub">{e["n_done"]}/{e["n_sessions"]} séances · {ui.esc(chapter_names)}</div></div>',
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns(2)
            if b1.button("🔄 Recalculer", key=f"re_{e['id']}",
                         help="Refait le plan avec tes niveaux de confiance actuels (les séances faites sont gardées)"):
                n = build_plan(e["id"], d)
                ui.flash(f"Plan recalculé : {n} séances à venir")
                st.rerun()
            with b2.popover("🗑️ Supprimer"):
                st.write("Supprimer l'examen et son plan ?")
                if st.button("Oui, supprimer", key=f"del_{e['id']}"):
                    db.delete_exam(e["id"])
                    st.rerun()


def toggle(session_id: int, key: str) -> None:
    checked = st.session_state[key]
    db.set_session_done(session_id, checked)
    if checked:
        stats.record_activity()
        ui.flash("Séance validée : +15 XP", "💪")


def session_checkbox(s: dict, key_prefix: str, compact: bool = False) -> None:
    label = f"{s['subject_emoji']} {s['chapter_name']}" if compact else \
        f"{s['subject_emoji']} **{s['chapter_name']}** · {s['minutes']} min · _{s['exam_title']}_"
    key = f"{key_prefix}_{s['id']}"
    st.checkbox(label, value=bool(s["done"]), key=key, on_change=toggle, args=(s["id"], key))


# --- Plan de révision ----------------------------------------------------------------------
st.subheader("Mon plan de révision")
if not db.list_sessions(start=today - timedelta(days=30)):
    st.info("Pas encore de séance planifiée. Ajoute un examen pour générer ton plan.")
else:
    tab_week, tab_list = st.tabs(["📅 Semaine", "📋 Liste"])

    with tab_week:
        # 7 jours glissants à partir d'aujourd'hui (plus utile qu'une semaine lundi-dimanche).
        offset = st.session_state.setdefault("week_offset", 0)
        first_day = today + timedelta(weeks=offset)
        last_day = first_day + timedelta(days=6)
        n1, n2, n3 = st.columns([1, 4, 1])
        if n1.button("◀", width="stretch", help="7 jours plus tôt"):
            st.session_state["week_offset"] -= 1
            st.rerun()
        n2.markdown(f"<div style='text-align:center;padding-top:.4rem' class='nr-title'>"
                    f"Du {ui.french_date(first_day, False)} au {ui.french_date(last_day, False)}</div>",
                    unsafe_allow_html=True)
        if n3.button("▶", width="stretch", help="7 jours plus tard"):
            st.session_state["week_offset"] += 1
            st.rerun()
        week = db.list_sessions(start=first_day, end=last_day)
        day_cols = st.columns(7)
        for i, col in enumerate(day_cols):
            d = first_day + timedelta(days=i)
            with col:
                css = "nr-day today" if d == today else "nr-day"
                st.markdown(f"<div class='{css}'>{ui.JOURS[d.weekday()][:3].capitalize()} {d.day}</div>",
                            unsafe_allow_html=True)
                day_sessions = [s for s in week if s["session_date"] == d.isoformat()]
                exams_today = [e for e in exams if e["exam_date"] == d.isoformat()]
                chips = [f'<div class="nr-chip exam">🎯 {ui.esc(e["title"])}</div>' for e in exams_today]
                chips += [
                    f'<div class="nr-chip{" done" if s["done"] else ""}" style="border-left-color:{s["subject_color"]}">'
                    f'{"✅ " if s["done"] else ""}{ui.esc(s["chapter_name"])}</div>'
                    for s in day_sessions
                ]
                st.markdown("".join(chips) or "<span class='nr-muted'>—</span>", unsafe_allow_html=True)
        st.caption("Coche tes séances dans l'onglet « Liste » ou sur l'accueil.")

    with tab_list:
        show_past = st.toggle("Afficher aussi les séances passées")
        sessions = db.list_sessions(start=None if show_past else today)
        late = [s for s in db.list_sessions(end=today - timedelta(days=1), only_pending=True)]
        if late and not show_past:
            st.warning(f"{len(late)} séance(s) en retard. Coche-les si tu les as faites, sinon clique « Recalculer ».")
            for s in late:
                session_checkbox(s, "late")
        current = None
        for s in sessions:
            if s["session_date"] != current:
                current = s["session_date"]
                d = date.fromisoformat(current)
                st.markdown(f"<div class='nr-day{' today' if d == today else ''}'>"
                            f"{ui.french_date(d).capitalize()}</div>", unsafe_allow_html=True)
            session_checkbox(s, "l")

past = [e for e in db.list_exams() if date.fromisoformat(e["exam_date"]) < today]
if past:
    with st.expander(f"Examens passés ({len(past)})"):
        for e in reversed(past):
            st.markdown(f"{e['subject_emoji']} **{e['title']}** — {ui.french_date(date.fromisoformat(e['exam_date']))}"
                        f" · {e['n_done']}/{e['n_sessions']} séances faites")
