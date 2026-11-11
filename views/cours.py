"""Page 2 — Mes cours : matières, chapitres, statut, confiance, notes et imports."""
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from core import db, files, importer, stats, ui

ui.page_title("Mes cours 📚", "Mets à jour tes chapitres au fil des révisions : c'est ce qui nourrit tout le reste.")

subjects = db.list_subjects()
tab_labels = [f"{s['emoji']} {s['name']}" for s in subjects] + ["📥 Importer un dossier", "⚙️ Gérer les matières"]
tabs = st.tabs(tab_labels)

CONFIDENCE_HELP = "1 = je suis perdu · 3 = ça va · 5 = je pourrais l'expliquer à quelqu'un"


def _save_chapter(chapter_id: int) -> None:
    """Enregistre le formulaire d'un chapitre."""
    db.update_chapter(
        chapter_id,
        status=st.session_state[f"status_{chapter_id}"],
        confidence=st.session_state[f"conf_{chapter_id}"],
        notes=st.session_state[f"notes_{chapter_id}"],
        pasted_content=st.session_state[f"paste_{chapter_id}"],
    )
    stats.record_activity()
    stats.refresh_snapshot()


def chapter_block(ch: dict) -> None:
    files_list = db.list_chapter_files(ch["id"])
    title = (f"{db.STATUS_EMOJIS[ch['status']]} {ch['name']} · confiance {ch['confidence']}/5"
             + (f" · 📎 {len(files_list)}" if files_list else ""))
    with st.expander(title):
        with st.form(f"form_{ch['id']}", border=False):
            c1, c2 = st.columns([3, 2])
            c1.radio("Statut", db.STATUSES, index=db.STATUSES.index(ch["status"]),
                     format_func=lambda s: f"{db.STATUS_EMOJIS[s]} {db.STATUS_LABELS[s]}",
                     horizontal=True, key=f"status_{ch['id']}")
            c2.slider("Niveau de confiance", 1, 5, int(ch["confidence"]), key=f"conf_{ch['id']}",
                      help=CONFIDENCE_HELP)
            st.text_area("Mes notes", ch["notes"], key=f"notes_{ch['id']}", height=100,
                         placeholder="Ce que t'as retenu, ce qui bloque, les questions pour le prof…")
            st.text_area("Coller du contenu de cours", ch["pasted_content"], key=f"paste_{ch['id']}",
                         height=120, placeholder="Colle ici un cours, un résumé, un énoncé…")
            if st.form_submit_button("💾 Enregistrer", type="primary"):
                _save_chapter(ch["id"])
                ui.flash(f"« {ch['name']} » mis à jour")
                st.rerun()

        # --- Fichiers importés ---
        st.markdown("**Fichiers de cours**")
        for f in files_list:
            fc1, fc2, fc3 = st.columns([6, 2, 2])
            fc1.markdown(f"📄 {ui.esc(f['filename'])}", unsafe_allow_html=True)
            # Aperçu à la demande : lire tous les PDF à chaque affichage rendrait la page très lente.
            key = f"prev_{f['id']}"
            if fc2.button("Masquer" if st.session_state.get(key) else "Aperçu", key=f"prevb_{f['id']}"):
                st.session_state[key] = not st.session_state.get(key, False)
                st.rerun()
            if fc3.button("Supprimer", key=f"delf_{f['id']}"):
                files.delete_file(f["id"])
                st.rerun()
            if st.session_state.get(key):
                if Path(f["filename"]).suffix.lower().lstrip(".") in files.IMAGE_EXTENSIONS:
                    st.image(str(db.ROOT_DIR / f["stored_path"]))
                else:
                    text = files.extract_text(f["stored_path"])
                    st.text(text[:3000] + ("…" if len(text) > 3000 else "") if text
                            else "Pas de texte lisible (PDF scanné ?). Colle le contenu à la main.")
        with st.form(f"upload_{ch['id']}", clear_on_submit=True, border=False):
            uploads = st.file_uploader("Ajouter des fichiers (PDF, Word, PowerPoint, texte, image)",
                                       type=sorted(files.ALLOWED_EXTENSIONS),
                                       accept_multiple_files=True, key=f"up_{ch['id']}")
            if st.form_submit_button("📥 Importer") and uploads:
                for up in uploads:
                    try:
                        files.save_upload(ch["id"], up.name, up.getvalue())
                    except ValueError as e:
                        st.error(f"{up.name} : {e}")
                        break
                else:
                    ui.flash(f"{len(uploads)} fichier(s) importé(s)")
                    st.rerun()

        # --- Renommer / supprimer ---
        with st.popover("✏️ Renommer ou supprimer"):
            new_name = st.text_input("Nouveau nom", ch["name"], key=f"ren_{ch['id']}")
            if st.button("Renommer", key=f"renb_{ch['id']}") and new_name.strip():
                db.rename_chapter(ch["id"], new_name)
                st.rerun()
            st.divider()
            sure = st.checkbox("Je veux vraiment supprimer ce chapitre", key=f"sure_{ch['id']}")
            if st.button("🗑️ Supprimer le chapitre", key=f"delc_{ch['id']}", disabled=not sure):
                db.delete_chapter(ch["id"])
                stats.refresh_snapshot()
                st.rerun()


for subject, tab in zip(subjects, tabs[:-2]):
    with tab:
        chapters = db.list_chapters(subject["id"])
        p = next(x for x in stats.subject_progress(chapters) if x["id"] == subject["id"])
        st.markdown(
            ui.badge(f"{p['n_mastered']} maîtrisé(s)", "mint")
            + ui.badge(f"{p['n_in_progress']} en cours", "orange")
            + ui.badge(f"{p['n_chapters']} chapitres", "blue")
            + ui.bar_html(p["pct"], subject["color"]),
            unsafe_allow_html=True,
        )
        st.caption(ui.motivation(subject["name"], p["pct"]))
        for ch in chapters:
            chapter_block(ch)
        with st.form(f"add_ch_{subject['id']}", clear_on_submit=True):
            name = st.text_input("Ajouter un chapitre", placeholder="Nom du chapitre")
            if st.form_submit_button("➕ Ajouter") and name.strip():
                db.add_chapter(subject["id"], name)
                stats.refresh_snapshot()
                ui.flash(f"Chapitre « {name.strip()} » ajouté")
                st.rerun()

# --- Import d'un dossier de cours -------------------------------------------------
def _show_plan(root: Path) -> None:
    """Analyse le dossier et garde le plan en mémoire jusqu'au clic sur « Importer »."""
    plan = importer.plan_import(root, db.list_subjects(), db.list_chapters())
    st.session_state["import_plan"] = plan


with tabs[-2]:
    st.markdown(
        "Importe d'un coup un dossier de cours rangé **un dossier par matière, puis un sous-dossier "
        "par chapitre** (par exemple celui récupéré depuis It's Learning). Les fichiers sont rattachés "
        "aux chapitres existants quand le nom correspond ; sinon le chapitre est créé. "
        "Relancer l'import n'ajoute pas de doublon."
    )
    source = st.radio("Source", ["Dossier sur cet ordinateur", "Fichier .zip"], horizontal=True,
                      label_visibility="collapsed")
    if source == "Dossier sur cet ordinateur":
        default = importer.default_folder()
        folder = st.text_input("Chemin du dossier", str(default) if default else "",
                               placeholder="/Users/…/Documents/cours Noahim")
        if st.button("🔍 Analyser le dossier"):
            path = Path(folder).expanduser()
            if not path.is_dir():
                st.error("Dossier introuvable. Vérifie le chemin (sur la version en ligne, utilise un .zip).")
            else:
                st.session_state.pop("import_tmp", None)
                _show_plan(path)
    else:
        archive = st.file_uploader("Archive .zip du dossier de cours", type=["zip"])
        if archive and st.button("🔍 Analyser l'archive"):
            tmp = Path(tempfile.mkdtemp(prefix="cours-import-"))
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)  # zipfile neutralise les chemins absolus et les « .. »
            inner = [p for p in tmp.iterdir() if p.is_dir() and not p.name.startswith("__")]
            root = inner[0] if len(inner) == 1 else tmp  # zip d'un dossier ou de son contenu
            st.session_state["import_tmp"] = str(tmp)
            _show_plan(root)

    plan = st.session_state.get("import_plan")
    if plan is not None:
        kinds = [p.kind for p in plan]
        new_subjects = sorted({p.subject for p in plan if p.new_subject and p.kind != "ignoré"})
        st.markdown(
            ui.badge(f"{kinds.count('fichier')} fichiers", "blue")
            + ui.badge(f"{kinds.count('lien')} liens", "mint")
            + ui.badge(f"{kinds.count('ignoré')} ignorés", "orange"),
            unsafe_allow_html=True,
        )
        if new_subjects:
            st.caption("Nouvelles matières : " + ", ".join(new_subjects))
        st.dataframe(pd.DataFrame(importer.summary(plan)), hide_index=True, width="stretch")
        ignored = [p for p in plan if p.kind == "ignoré"]
        if ignored:
            with st.expander(f"Fichiers ignorés ({len(ignored)})"):
                for p in ignored:
                    st.caption(f"{p.source.name} — {p.reason}")
        if st.button("📥 Importer", type="primary", disabled=not any(k != "ignoré" for k in kinds)):
            bar = st.progress(0.0, text="Import en cours…")
            report = importer.apply_import(
                plan, progress=lambda i, n, name: bar.progress(i / n, text=f"{i}/{n} · {name[:60]}"))
            bar.empty()
            if st.session_state.get("import_tmp"):
                shutil.rmtree(st.session_state.pop("import_tmp"), ignore_errors=True)
            st.session_state.pop("import_plan", None)
            stats.refresh_snapshot()
            stats.record_activity()
            msg = (f"{report['fichiers']} fichiers et {report['liens']} liens importés · "
                   f"{report['chapitres créés']} chapitres et {report['matières créées']} matières créés")
            if report["déjà là"]:
                msg += f" · {report['déjà là']} déjà présents"
            ui.flash(msg, "📥")
            for err in report["erreurs"][:10]:
                st.error(err)
            if not report["erreurs"]:
                st.rerun()

# --- Gestion des matières -----------------------------------------------------
with tabs[-1]:
    st.markdown("#### Ajouter une matière")
    with st.form("add_subject", clear_on_submit=True):
        c1, c2 = st.columns([1, 5])
        emoji = c1.text_input("Emoji", "📘", max_chars=4)
        name = c2.text_input("Nom", placeholder="ex. Histoire-Géo, Anglais, Spé abandonnée…")
        if st.form_submit_button("➕ Ajouter la matière") and name.strip():
            try:
                db.add_subject(name, emoji)
                ui.flash(f"Matière « {name.strip()} » ajoutée")
                st.rerun()
            except Exception:
                st.error("Cette matière existe déjà.")

    st.markdown("#### Renommer ou supprimer")
    for s in subjects:
        with st.expander(f"{s['emoji']} {s['name']}"):
            c1, c2 = st.columns([1, 5])
            e = c1.text_input("Emoji", s["emoji"], key=f"se_{s['id']}", max_chars=4)
            n = c2.text_input("Nom", s["name"], key=f"sn_{s['id']}")
            if st.button("Enregistrer", key=f"sb_{s['id']}") and n.strip():
                try:
                    db.rename_subject(s["id"], n, e)
                    st.rerun()
                except Exception:
                    st.error("Ce nom est déjà pris.")
            sure = st.checkbox("Supprimer aussi tous ses chapitres, examens et fiches", key=f"ss_{s['id']}")
            if st.button("🗑️ Supprimer la matière", key=f"sd_{s['id']}", disabled=not sure):
                db.delete_subject(s["id"])
                st.rerun()
