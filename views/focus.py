"""Page 7 — Mode focus : Pomodoro, journal des séances, XP et niveaux."""
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from core import db, stats, ui

ui.page_title("Mode focus ⏱️", "Téléphone retourné, une seule chose à la fois.")

work = int(db.get_setting("pomodoro_work", "25"))
pause = int(db.get_setting("pomodoro_break", "5"))

left, right = st.columns([3, 2], gap="large")

with left:
    with st.expander("⚙️ Réglages du minuteur"):
        with st.form("pomodoro_settings", border=False):
            r1, r2 = st.columns(2)
            new_work = r1.number_input("Travail (min)", 5, 90, work, step=5)
            new_pause = r2.number_input("Pause (min)", 1, 30, pause)
            if st.form_submit_button("Enregistrer"):
                db.set_setting("pomodoro_work", new_work)
                db.set_setting("pomodoro_break", new_pause)
                st.rerun()

    # Minuteur côté navigateur : il tourne sans recharger la page (et marche sur mobile).
    components.html(
        f"""
<div id="t" style="font-family:Inter,system-ui,sans-serif;color:{ui.TEXT};text-align:center;
  background:{ui.SURFACE};border-radius:20px;padding:22px 12px;border:1px solid {ui.BORDER};box-shadow:0 6px 18px rgba(15,31,51,.05)">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;800&display=swap" rel="stylesheet">
  <div id="mode" style="font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:13px;color:{ui.MINT_TEXT}">Focus</div>
  <div id="clock" style="font-family:Inter,sans-serif;font-weight:800;letter-spacing:-0.03em;font-variant-numeric:tabular-nums;font-size:clamp(44px,17vw,72px);line-height:1.1;margin:6px 0">{work:02d}:00</div>
  <div style="height:8px;background:{ui.TRACK};border-radius:99px;overflow:hidden;margin:0 10% 16px">
    <div id="bar" style="height:100%;width:0;background:linear-gradient(90deg,{ui.ACCENT},{ui.MINT})"></div></div>
  <button id="go" style="background:{ui.ACCENT};color:white;border:0;border-radius:12px;padding:10px 22px;font-weight:600;font-size:15px;cursor:pointer">▶ Démarrer</button>
  <button id="reset" style="background:transparent;color:{ui.TEXT};border:1px solid {ui.BORDER};border-radius:12px;padding:10px 18px;font-weight:600;font-size:15px;cursor:pointer;margin-left:6px">↺</button>
  <div id="msg" style="margin-top:12px;font-size:13px;color:{ui.MUTED}">Quand le focus se termine, valide la séance juste en dessous.</div>
</div>
<script>
const WORK={work}*60, PAUSE={pause}*60;
let mode='work', left=WORK, timer=null, endAt=null;
const $=id=>document.getElementById(id);
function draw(){{
  const m=String(Math.floor(left/60)).padStart(2,'0'), s=String(left%60).padStart(2,'0');
  $('clock').textContent=m+':'+s;
  const total=mode==='work'?WORK:PAUSE;
  $('bar').style.width=(100*(total-left)/total)+'%';
  $('mode').textContent=mode==='work'?'Focus':'Pause';
  $('mode').style.color=mode==='work'?'{ui.MINT_TEXT}':'{ui.ORANGE_TEXT}';
}}
function beep(){{ try{{ const c=new (window.AudioContext||window.webkitAudioContext)();
  [0,0.35,0.7].forEach(t=>{{const o=c.createOscillator(),g=c.createGain();o.connect(g);g.connect(c.destination);
  o.frequency.value=880;g.gain.value=.15;o.start(c.currentTime+t);o.stop(c.currentTime+t+0.2);}}); }}catch(e){{}} }}
function tick(){{
  left=Math.max(0,Math.round((endAt-Date.now())/1000)); draw();
  if(left===0){{ clearInterval(timer); timer=null; beep();
    if(mode==='work'){{ mode='pause'; left=PAUSE; $('msg').textContent='🎉 Focus terminé ! Valide ta séance, puis souffle un peu.'; }}
    else {{ mode='work'; left=WORK; $('msg').textContent='Pause finie, on y retourne ?'; }}
    $('go').textContent='▶ Démarrer'; draw(); }}
}}
$('go').onclick=()=>{{
  if(timer){{ clearInterval(timer); timer=null; $('go').textContent='▶ Reprendre'; return; }}
  endAt=Date.now()+left*1000; timer=setInterval(tick,250); $('go').textContent='⏸ Pause';
}};
$('reset').onclick=()=>{{ clearInterval(timer); timer=null; mode='work'; left=WORK; $('go').textContent='▶ Démarrer'; draw(); }};
draw();
</script>
""",
        height=300,
    )

    chapters = db.list_chapters()
    options = [None] + chapters
    chosen = st.selectbox("Sur quel chapitre ? (facultatif)", options,
                          format_func=lambda c: "— Libre —" if c is None else f"{c['subject_emoji']} {c['name']}")
    if st.button(f"✅ J'ai terminé une séance de {work} min", type="primary", width="stretch"):
        db.add_focus_session(work, chosen["id"] if chosen else None)
        stats.record_activity()
        ui.flash(f"+{stats.XP_RULES['focus']} XP. Bien joué, prends ta pause !", "🎉")
        st.rerun()

with right:
    lvl = stats.current_level()
    st.markdown(
        f'<div class="nr-card"><div class="nr-metric-label">Niveau {lvl["level"]}</div>'
        f'<div class="nr-metric-value">{ui.esc(lvl["title"])}</div>{ui.bar_html(lvl["pct"])}'
        f'<div class="nr-metric-sub">{lvl["in_level"]} / {lvl["to_next"]} XP pour le niveau suivant · '
        f'total {lvl["xp"]} XP</div></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Comment gagner de l'XP ?"):
        st.markdown(
            f"- Séance focus terminée : **+{stats.XP_RULES['focus']}**\n"
            f"- Séance du planning validée : **+{stats.XP_RULES['sessions_done']}**\n"
            f"- Bonne réponse en quiz : **+{stats.XP_RULES['quiz_points']}**\n"
            f"- Chapitre maîtrisé : **+{stats.XP_RULES['mastered']}**\n"
            f"- Chapitre avec sa fiche : **+{stats.XP_RULES['fiches']}**"
        )
    ui.metric_card("Série", f"🔥 {stats.current_streak()} j", "jours de travail d'affilée")

# --- Journal ------------------------------------------------------------------------
st.subheader("Journal des séances")
log = db.list_focus_sessions()
if not log:
    st.caption("Ta première séance apparaîtra ici.")
else:
    df = pd.DataFrame(log)
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["jour"] = df["started_at"].dt.date
    today = date.today()
    last14 = pd.DataFrame({"jour": [today - timedelta(days=i) for i in range(13, -1, -1)]})
    per_day = last14.merge(df.groupby("jour")["minutes"].sum().reset_index(), on="jour", how="left").fillna(0)
    week_total = int(df[df["jour"] >= today - timedelta(days=6)]["minutes"].sum())
    st.caption(f"Cette semaine : **{week_total // 60} h {week_total % 60:02d}** de focus.")
    fig = px.bar(per_day, x="jour", y="minutes", labels={"jour": "", "minutes": "min"})
    fig.update_traces(marker_color=ui.ACCENT)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=240,
                      font=dict(family="Inter, sans-serif", color=ui.TEXT), margin=dict(l=10, r=10, t=10, b=10),
                      yaxis=dict(gridcolor=ui.TRACK))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    table = pd.DataFrame({
        "Quand": df["started_at"].dt.strftime("%d/%m %H:%M"),
        "Durée": df["minutes"].astype(str) + " min",
        "Chapitre": df["chapter_name"].fillna("Libre"),
    })
    st.dataframe(table.head(30), hide_index=True, width="stretch")
