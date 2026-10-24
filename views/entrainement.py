"""Page 6 — S'entraîner : quiz QCM + exercices courts, corrigés et expliqués."""
import random

import streamlit as st

from core import ai, db, files, stats, ui

ui.page_title("S'entraîner 🎯", "Un quiz sur mesure. Tes erreurs partent dans « à retravailler ».")

chapters = db.list_chapters()
if not chapters:
    st.warning("Ajoute d'abord des chapitres dans « Mes cours ».")
    st.stop()

c1, c2 = st.columns(2)
subjects = db.list_subjects()
subject = c1.selectbox("Matière", subjects, format_func=lambda s: f"{s['emoji']} {s['name']}")
own = [c for c in chapters if c["subject_id"] == subject["id"]]
if not own:
    st.info("Cette matière n'a pas encore de chapitre.")
    st.stop()
chapter = c2.selectbox("Chapitre", own, format_func=lambda c: f"{c['name']} (confiance {c['confidence']}/5)")

state = st.session_state
quiz_key = f"quiz_{chapter['id']}"


def suggest_confidence(score: int, total: int) -> None:
    """Propose d'ajuster la confiance selon le résultat."""
    ratio = score / total if total else 0
    current = chapter["confidence"]
    target = current + 1 if ratio >= 0.8 else current - 1 if ratio < 0.4 else current
    target = max(1, min(5, target))
    if target != current:
        verb = "monter" if target > current else "baisser"
        if st.button(f"Faire {verb} ma confiance sur ce chapitre à {target}/5"):
            db.update_chapter(chapter["id"], confidence=target)
            stats.refresh_snapshot()
            ui.flash(f"Confiance mise à {target}/5")
            st.rerun()


# =============================================================================
# Mode sans clé API : questions flash des fiches
# =============================================================================
if not ai.is_configured():
    st.warning(
        "**Aucune clé API Claude n'est configurée**, la génération de quiz est désactivée. "
        "Ajoute `ANTHROPIC_API_KEY` dans le fichier `.env` pour l'activer."
    )
    fiches = db.list_fiches(chapter["id"])
    pairs = ai.flash_questions(fiches[0]["content_md"]) if fiches else []
    if not pairs:
        st.info("En attendant, écris une fiche (onglet « Fiche manuelle ») avec des questions flash : "
                "tu pourras t'interroger dessus ici.")
        st.stop()
    st.subheader("Interro flash (questions de ta fiche)")
    for i, (q, r) in enumerate(pairs):
        with st.container(border=True):
            st.markdown(f"**{q}**")
            with st.expander("Voir la réponse"):
                st.markdown(r)
            b1, b2 = st.columns(2)
            if b1.button("✅ Je savais", key=f"ok_{chapter['id']}_{i}"):
                db.add_quiz_result(chapter["id"], 1, 1)
                stats.record_activity()
                ui.flash("+2 XP")
                st.rerun()
            if b2.button("❌ Pas su", key=f"ko_{chapter['id']}_{i}"):
                db.add_quiz_result(chapter["id"], 0, 1)
                db.add_weak_point(chapter["id"], q, f"Réponse : {r}")
                stats.record_activity()
                ui.flash("Ajouté à « à retravailler »", "📌")
                st.rerun()
    st.stop()

# =============================================================================
# Mode IA
# =============================================================================
with st.form("quiz_settings"):
    s1, s2 = st.columns(2)
    n_qcm = s1.slider("Nombre de QCM", 3, 10, 5)
    n_ex = s2.slider("Exercices courts", 0, 3, 2)
    st.caption("🔒 Le contenu du chapitre est envoyé à l'API Claude uniquement quand tu cliques.")
    if st.form_submit_button("🎲 Générer un quiz", type="primary"):
        with st.spinner("Claude prépare tes questions…"):
            try:
                quiz = ai.generate_quiz(chapter["subject_name"], chapter["name"],
                                        files.chapter_material(chapter), n_qcm, n_ex)
                # Mélange les propositions pour que la bonne réponse ne soit pas toujours au même endroit.
                qcm = []
                for q in quiz.qcm:
                    order = list(range(len(q.choix)))
                    random.shuffle(order)
                    qcm.append({"question": q.question, "choix": [q.choix[i] for i in order],
                                "bonne": order.index(q.bonne_reponse), "explication": q.explication})
                state[quiz_key] = {
                    "qcm": qcm,
                    "exercices": [e.model_dump() for e in quiz.exercices],
                    "submitted": False, "self_eval": {},
                }
            except ai.AIError as e:
                st.error(str(e))

quiz = state.get(quiz_key)
if not quiz:
    st.info("Choisis un chapitre et génère ton quiz. Bonne chance 🍀")
    st.stop()

# --- Questions --------------------------------------------------------------------
with st.form(f"quiz_answers_{chapter['id']}"):
    st.subheader("QCM")
    for i, q in enumerate(quiz["qcm"]):
        st.radio(f"**{i + 1}.** {q['question']}", range(len(q["choix"])), index=None,
                 format_func=lambda k, q=q: q["choix"][k], key=f"{quiz_key}_q{i}",
                 disabled=quiz["submitted"])
    if quiz["exercices"]:
        st.subheader("Exercices")
        for j, ex in enumerate(quiz["exercices"]):
            st.markdown(f"**Exercice {j + 1}.** {ex['enonce']}")
            st.text_area("Ta réponse (brouillon)", key=f"{quiz_key}_e{j}", height=100,
                         disabled=quiz["submitted"])
    submitted = st.form_submit_button("📨 Corriger", type="primary", disabled=quiz["submitted"])

if submitted and not quiz["submitted"]:
    score = 0
    for i, q in enumerate(quiz["qcm"]):
        answer = state.get(f"{quiz_key}_q{i}")
        if answer == q["bonne"]:
            score += 1
        else:
            db.add_weak_point(chapter["id"], q["question"],
                              f"Bonne réponse : {q['choix'][q['bonne']]}. {q['explication']}")
    db.add_quiz_result(chapter["id"], score, len(quiz["qcm"]))
    stats.record_activity()
    quiz["submitted"] = True
    quiz["score"] = score
    st.rerun()

# --- Correction -------------------------------------------------------------------
if quiz["submitted"]:
    total = len(quiz["qcm"])
    score = quiz.get("score", 0)
    ratio = score / total if total else 0
    mood = "Énorme 🔥" if ratio >= 0.8 else "Pas mal 💪" if ratio >= 0.5 else "On s'accroche, ça va venir 🙌"
    ui.metric_card("Ton score", f"{score}/{total}", mood)
    suggest_confidence(score, total)

    for i, q in enumerate(quiz["qcm"]):
        answer = state.get(f"{quiz_key}_q{i}")
        ok = answer == q["bonne"]
        with st.container(border=True):
            st.markdown(f"{'✅' if ok else '❌'} **{i + 1}. {q['question']}**")
            if not ok:
                given = q["choix"][answer] if answer is not None else "pas de réponse"
                st.markdown(f"Ta réponse : ~~{given}~~")
            st.markdown(f"Bonne réponse : **{q['choix'][q['bonne']]}**")
            st.caption(q["explication"])

    for j, ex in enumerate(quiz["exercices"]):
        with st.container(border=True):
            st.markdown(f"**Exercice {j + 1} — correction**")
            st.markdown(ex["correction"])
            done = quiz["self_eval"].get(j)
            if done is None:
                b1, b2 = st.columns(2)
                if b1.button("✅ J'avais bon", key=f"{quiz_key}_ok{j}"):
                    quiz["self_eval"][j] = True
                    st.rerun()
                if b2.button("❌ J'avais faux", key=f"{quiz_key}_ko{j}"):
                    quiz["self_eval"][j] = False
                    db.add_weak_point(chapter["id"], f"Exercice : {ex['enonce'][:300]}", ex["correction"][:800])
                    st.rerun()
            else:
                st.caption("Noté 👍" if done else "Ajouté à « à retravailler » 📌")

    if st.button("🔁 Nouveau quiz"):
        state.pop(quiz_key, None)
        for k in [k for k in state if str(k).startswith(f"{quiz_key}_")]:
            del state[k]
        st.rerun()
