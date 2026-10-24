"""Page 5 — Fiches de révision : générées par Claude ou écrites à la main."""
import re

import streamlit as st

from core import ai, db, files, pdf, stats, ui

ui.page_title("Fiches de révision 📝", "L'essentiel, les formules, les pièges et 5 questions flash.")

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
chapter = c2.selectbox("Chapitre", own, format_func=lambda c: c["name"])

material = files.chapter_material(chapter)
fiches = db.list_fiches(chapter["id"])

tab_view, tab_ai, tab_manual = st.tabs(["📖 Ma fiche", "✨ Générer avec l'IA", "✍️ Fiche manuelle"])

# --- Génération IA -----------------------------------------------------------------
with tab_ai:
    if not ai.is_configured():
        st.warning(
            "**Aucune clé API Claude n'est configurée**, la génération automatique est désactivée.\n\n"
            "Pour l'activer : copie `.env.example` en `.env`, colle ta clé dans `ANTHROPIC_API_KEY`, "
            "puis relance l'appli. En attendant, l'onglet **« Fiche manuelle »** te donne un modèle à remplir."
        )
    else:
        if material:
            st.caption(f"Contenu utilisé : notes + cours collé + fichiers importés (~{len(material.split())} mots).")
        else:
            st.caption("Aucun contenu importé pour ce chapitre : la fiche s'appuiera sur le programme officiel.")
        st.caption("🔒 Le contenu du chapitre est envoyé à l'API Claude uniquement quand tu cliques.")
        if st.button("✨ Générer la fiche", type="primary"):
            with st.spinner("Claude prépare ta fiche…"):
                try:
                    fiche = ai.generate_fiche(chapter["subject_name"], chapter["name"], material)
                    md = ai.fiche_to_markdown(fiche, chapter["subject_name"], chapter["name"])
                    db.save_fiche(chapter["id"], md, "ia")
                    stats.record_activity()
                    ui.flash("Fiche générée ! Va voir l'onglet « Ma fiche »", "📝")
                    st.rerun()
                except ai.AIError as e:
                    st.error(str(e))

# --- Fiche manuelle -----------------------------------------------------------------
with tab_manual:
    st.caption("Remplis le modèle. Écris tes questions flash sous la forme « Q1 : … » puis « R : … » "
               "(les réponses seront masquées à l'affichage).")
    base = fiches[0]["content_md"] if fiches else \
        ai.MANUAL_TEMPLATE.format(chapter=chapter["name"], subject=chapter["subject_name"])
    with st.form(f"manual_{chapter['id']}"):
        content = st.text_area("Contenu (Markdown)", base, height=460)
        if st.form_submit_button("💾 Enregistrer ma fiche", type="primary"):
            db.save_fiche(chapter["id"], content, "manuel")
            stats.record_activity()
            ui.flash("Fiche enregistrée")
            st.rerun()

# --- Affichage + export -------------------------------------------------------------
with tab_view:
    if not fiches:
        st.info("Pas encore de fiche pour ce chapitre. Génère-la avec l'IA ou écris-la à la main.")
    else:
        if len(fiches) > 1:
            chosen = st.selectbox(
                "Version", fiches,
                format_func=lambda f: f"{f['created_at'][:16].replace('T', ' ')} · "
                                      f"{'IA' if f['source'] == 'ia' else 'manuelle'}",
            )
        else:
            chosen = fiches[0]
        with st.container(border=True):
            ui.render_fiche(chosen["content_md"])

        slug = re.sub(r"[^a-z0-9]+", "-", chapter["name"].lower()).strip("-") or "fiche"
        d1, d2, d3 = st.columns(3)
        d1.download_button("⬇️ Markdown", chosen["content_md"], file_name=f"fiche-{slug}.md",
                           mime="text/markdown", width="stretch")
        d2.download_button("⬇️ PDF", pdf.fiche_to_pdf(chosen["content_md"]), file_name=f"fiche-{slug}.pdf",
                           mime="application/pdf", width="stretch")
        with d3.popover("🗑️ Supprimer", width="stretch"):
            if st.button("Confirmer la suppression", key=f"delfiche_{chosen['id']}"):
                db.delete_fiche(chosen["id"])
                st.rerun()
