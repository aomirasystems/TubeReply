import os
import json
import tempfile
import streamlit as st
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from groq import Groq

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
MAX_VIDEOS = 5
LIMITE_CREDITOS = 50

BASE_PROMPT = """Eres el community manager de un canal de YouTube.
Responde comentarios de fans siguiendo estas reglas base:
- Máximo 2-3 oraciones, respuestas cortas y directas
- Nunca inventes datos incorrectos
- Devuelve SOLO el texto de la respuesta, sin explicaciones adicionales

El creador del canal ha dado estas instrucciones sobre su estilo:
{contexto}"""

st.set_page_config(page_title="TubeReply", page_icon="▶️", layout="centered")

st.markdown("""
<style>
/* ── Base ── */
.stApp { background-color: #08011a; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; }

/* ── Header ── */
.tubereply-header {
    display: flex; align-items: center; gap: 12px;
    padding: 1.2rem 1.5rem;
    background: linear-gradient(135deg, #1a0a3e 0%, #0d0520 100%);
    border-radius: 14px;
    border: 1px solid #7c3aed44;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 24px #7c3aed22;
}
.tubereply-header h1 { margin: 0; font-size: 1.6rem; color: #e2d9f3; }
.tubereply-header p  { margin: 0; font-size: 0.8rem; color: #9575cd; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #12052a;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #9575cd;
    font-weight: 600;
    padding: 6px 20px;
}
.stTabs [aria-selected="true"] {
    background: #3b0764 !important;
    color: #e2d9f3 !important;
}

/* ── Métricas ── */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a0a3e, #12052a);
    border: 1px solid #4c1d9533;
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 2px 12px #00000033;
}
div[data-testid="metric-container"] label { color: #9575cd; font-size: 0.75rem; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e2d9f3; font-size: 1.6rem; font-weight: 700;
}

/* ── Cards ── */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: linear-gradient(135deg, #140630 0%, #0f0226 100%) !important;
    border: 1px solid #4c1d9544 !important;
    border-radius: 14px !important;
    padding: 1rem 1.2rem !important;
    box-shadow: 0 2px 16px #00000044;
    transition: border-color 0.2s;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover > div {
    border-color: #7c3aed88 !important;
}

/* ── Autor tag ── */
.author-tag {
    display: inline-block;
    background: #3b076422;
    border: 1px solid #7c3aed55;
    border-radius: 20px;
    padding: 2px 12px;
    color: #c4b5fd;
    font-weight: 700;
    font-size: 0.9rem;
}
.author-tag.replied {
    background: #064e3b22;
    border-color: #10b98155;
    color: #6ee7b7;
}

/* ── Texto comentario ── */
.comment-text {
    background: #0a011f;
    border-left: 3px solid #7c3aed66;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    color: #c4b5fd99;
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 8px 0;
}

/* ── TextArea ── */
.stTextArea textarea {
    background: #0f0226 !important;
    color: #e2d9f3 !important;
    border: 1px solid #7c3aed55 !important;
    border-radius: 10px !important;
    font-size: 0.9rem;
    resize: vertical;
}
.stTextArea textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 2px #7c3aed33 !important;
}

/* ── Botones ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    border: none !important;
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px #7c3aed44 !important;
}
.stButton > button[kind="secondary"] {
    background: #1a0a3e !important;
    border: 1px solid #4c1d9555 !important;
    color: #9575cd !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #7c3aed !important;
    color: #e2d9f3 !important;
}

/* ── Respuesta enviada ── */
.reply-sent {
    background: #064e3b22;
    border: 1px solid #10b98133;
    border-radius: 10px;
    padding: 10px 14px;
    color: #6ee7b7;
    font-size: 0.88rem;
    line-height: 1.5;
    margin: 6px 0;
}

/* ── Divider ── */
hr { border-color: #4c1d9522 !important; }

/* ── Warnings/errors ── */
.stAlert { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


def get_secret(key, fallback_env=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(fallback_env or key, '')


ESTILO_FILE = 'mi_estilo.txt'

def load_estilo():
    if 'estilo' in st.session_state:
        return st.session_state['estilo']
    try:
        val = st.secrets.get('CANAL_ESTILO', '')
        if val:
            return val
    except Exception:
        pass
    if os.path.exists(ESTILO_FILE):
        with open(ESTILO_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ''

def save_estilo(text):
    st.session_state['estilo'] = text
    try:
        with open(ESTILO_FILE, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass

def build_prompt():
    estilo = load_estilo()
    if not estilo:
        estilo = "Sé amigable, cercano y entusiasta. Responde siempre en español."
    return BASE_PROMPT.format(contexto=estilo)

def textarea_height(text):
    lines = max(3, len(text) // 58 + text.count('\n') + 1)
    return min(300, lines * 24 + 24)


@st.cache_resource
def get_groq_client():
    key = get_secret('GROQ_API_KEY')
    if not key or key.strip() == '':
        st.error("⚠️ Falta la Groq API key.")
        st.stop()
    return Groq(api_key=key)


@st.cache_resource
def get_yt_service():
    try:
        token_data = st.secrets['YOUTUBE_TOKEN']
        if isinstance(token_data, dict):
            token_str = json.dumps(dict(token_data))
        else:
            token_str = token_data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(token_str)
            token_path = f.name
    except Exception:
        token_path = 'token.json'

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('youtube', 'v3', credentials=creds)


def get_channel_id(yt):
    return yt.channels().list(part='id', mine=True).execute()['items'][0]['id']

def get_recent_videos(yt, channel_id):
    res = yt.search().list(
        part='id', channelId=channel_id,
        type='video', order='date', maxResults=MAX_VIDEOS
    ).execute()
    return [item['id']['videoId'] for item in res.get('items', [])]

def get_unanswered(yt, video_id, channel_id):
    result = []
    res = yt.commentThreads().list(
        part='snippet,replies', videoId=video_id, maxResults=50
    ).execute()
    for thread in res.get('items', []):
        top = thread['snippet']['topLevelComment']
        s = top['snippet']
        if s.get('authorChannelId', {}).get('value', '') == channel_id:
            continue
        already_replied = any(
            r['snippet']['authorChannelId']['value'] == channel_id
            for r in thread.get('replies', {}).get('comments', [])
        )
        if not already_replied:
            result.append({
                'comment_id': top['id'],
                'author': s['authorDisplayName'],
                'text': s['textDisplay'],
                'video_id': video_id,
            })
    return result


MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
MODEL_LIMITS = {'llama-3.3-70b-versatile': 100_000, 'llama-3.1-8b-instant': 500_000}

def next_reset_utc():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    horas = int((reset - now).total_seconds() // 3600)
    minutos = int((reset - now).total_seconds() % 3600 // 60)
    return reset.strftime('%H:%M UTC'), horas, minutos

def generate_reply(text):
    if 'model_index' not in st.session_state:
        st.session_state.model_index = 0
    if 'tokens_used' not in st.session_state:
        st.session_state.tokens_used = {m: 0 for m in MODELS}

    for _ in range(len(MODELS)):
        idx = st.session_state.model_index
        model = MODELS[idx]
        try:
            res = get_groq_client().chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': build_prompt()},
                    {'role': 'user', 'content': f'Comentario: {text}'}
                ],
                max_tokens=120
            )
            st.session_state.tokens_used[model] = st.session_state.tokens_used.get(model, 0) + res.usage.total_tokens
            return res.choices[0].message.content.strip()
        except Exception as e:
            if '429' in str(e):
                st.session_state.tokens_used[model] = MODEL_LIMITS[model]
                if idx + 1 < len(MODELS):
                    st.session_state.model_index = idx + 1
                    st.toast(f"⚠️ Límite de {model} alcanzado, cambiando a {MODELS[idx+1]}")
                else:
                    hora, horas, minutos = next_reset_utc()
                    raise RuntimeError(
                        f"🚫 Se han acabado los créditos de todos los modelos.\n\n"
                        f"⏳ Se reinician a las **{hora}** (en {horas}h {minutos}m).\n\n"
                        f"💳 O compra más en [console.groq.com/settings/billing](https://console.groq.com/settings/billing)"
                    )
            else:
                raise

def post_reply(comment_id, text):
    get_yt_service().comments().insert(
        part='snippet',
        body={'snippet': {'parentId': comment_id, 'textOriginal': text}}
    ).execute()


# ── UI ─────────────────────────────────────────────────────
if 'iniciado' not in st.session_state:
    st.session_state.iniciado = False

if not st.session_state.iniciado:
    st.markdown("""
    <style>
    div[data-testid="stMainBlockContainer"] { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:90vh; }
    .welcome-wrap { display:flex; flex-direction:column; align-items:center; text-align:center; gap:20px; padding:2rem; }
    div[data-testid="stButton"] button[kind="primary"] {
        font-size:1.6rem !important;
        padding:1.1rem 3.5rem !important;
        border-radius:16px !important;
        letter-spacing:0.12em !important;
        box-shadow: 0 6px 32px #7c3aed55 !important;
        min-width:260px;
    }
    </style>
    <div class="welcome-wrap">
        <div style="font-size:5rem;">▶️</div>
        <h1 style="font-size:3rem; color:#e2d9f3; margin:0; font-weight:800;">TubeReply</h1>
        <p style="font-size:1.25rem; color:#9575cd; margin:0;">
            ¿Listo para responder comentarios y ahorrar tiempo?
        </p>
    </div>
    """, unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        if st.button("🚀  INICIAR", type="primary", use_container_width=True):
            st.session_state.iniciado = True
            st.rerun()
    st.stop()

st.markdown("""
<div class="tubereply-header">
  <div>
    <h1>▶️ TubeReply</h1>
    <p>Responde comentarios de tu canal con IA · Groq + YouTube</p>
  </div>
</div>
""", unsafe_allow_html=True)

token_ok = os.path.exists('token.json') or ('YOUTUBE_TOKEN' in (st.secrets if hasattr(st, 'secrets') else {}))
if not token_ok:
    st.error("Canal de YouTube no conectado. Ejecuta `iniciar.bat` primero.")
    st.stop()

tab_bot, tab_estilo = st.tabs(["💬 Comentarios", "✏️ Mi estilo"])

# ── TAB: MI ESTILO ─────────────────────────────────────────
with tab_estilo:
    st.markdown("### Cómo quieres que responda la IA")
    st.caption("Tu tono, frases típicas, cosas a mencionar o evitar. Cuanto más detallado, mejor.")

    nuevo_estilo = st.text_area(
        label="Instrucciones",
        value=load_estilo(),
        height=280,
        placeholder="""Ejemplos:
- Habla siempre en español con entusiasmo por los dinosaurios
- Usa frases como "¡Qué buena pregunta!" o "¡Exacto!"
- Menciona el canal: "En PaleoRealms tenemos un video sobre eso"
- Si preguntan por más contenido, invítalos a suscribirse
- No uses más de 1 emoji por respuesta
- Evita respuestas genéricas, sé específico sobre paleontología""",
        label_visibility="collapsed"
    )

    if st.button("💾 Guardar estilo", type="primary", use_container_width=True):
        save_estilo(nuevo_estilo)
        st.success("✅ Guardado para esta sesión.")
        st.info("Para que sea permanente añade en Streamlit Cloud → Settings → Secrets:\n```\nCANAL_ESTILO = '''tu texto aquí'''\n```")

    if load_estilo():
        with st.expander("Ver prompt completo que recibe la IA"):
            st.code(build_prompt(), language=None)

# ── TAB: COMENTARIOS ───────────────────────────────────────
with tab_bot:
    for key, default in [('comments', []), ('replies', {}), ('done', set()), ('closed', set()), ('published_ids', set()), ('published', 0), ('creditos_usados', 0), ('batch_size', 10), ('modo', 'Asistido')]:
        if key not in st.session_state:
            st.session_state[key] = default

    if not load_estilo():
        st.warning("💡 Ve a **Mi estilo** y escribe cómo quieres que responda la IA.")

    col1, col2 = st.columns([3, 1])
    with col1:
        fetch = st.button("🔍 Buscar comentarios nuevos", type="primary", use_container_width=True)
    with col2:
        if st.button("🧹 Limpiar", use_container_width=True):
            for k in ['comments', 'replies', 'done', 'closed', 'published_ids']:
                st.session_state[k] = [] if k == 'comments' else {} if k == 'replies' else set()
            st.session_state.published = 0
            st.rerun()

    if fetch:
        with st.spinner("Conectando con YouTube..."):
            try:
                yt = get_yt_service()
                channel_id = get_channel_id(yt)
                all_comments = []
                for vid in get_recent_videos(yt, channel_id):
                    all_comments.extend(get_unanswered(yt, vid, channel_id))
                st.session_state.comments = all_comments
                st.session_state.done = set()
                st.session_state.closed = set()
                st.session_state.replies = {}
                st.session_state.published_ids = set()
                st.session_state.published = 0
            except Exception as e:
                st.error(f"Error al conectar con YouTube: {e}")

    all_visible = [c for c in st.session_state.comments if c['comment_id'] not in st.session_state.done and c['comment_id'] not in st.session_state.closed]
    all_pending = [c for c in all_visible if c['comment_id'] not in st.session_state.published_ids]
    creditos_restantes = max(0, LIMITE_CREDITOS - st.session_state.creditos_usados)

    if st.session_state.comments:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💬 Pendientes", len(all_pending))
        m2.metric("✅ Publicados", st.session_state.published)
        m3.metric("⏭ Saltados", len(st.session_state.done))
        m4.metric("🎟️ Créditos", f"{creditos_restantes}/{LIMITE_CREDITOS}")
        st.divider()

    # ── Modo y batch ───────────────────────────────────────
    if st.session_state.comments:
        st.markdown("**¿Cómo quieres responder comentarios?**")
        modo = st.radio(
            "modo", ["🤖 Automático", "🧑 Asistido", "⚡ Bulk"],
            index=["🤖 Automático", "🧑 Asistido", "⚡ Bulk"].index(
                next((m for m in ["🤖 Automático", "🧑 Asistido", "⚡ Bulk"] if st.session_state.modo in m), "🧑 Asistido")
            ),
            horizontal=True, label_visibility="collapsed"
        )
        st.session_state.modo = modo

        if modo != "🤖 Automático":
            st.markdown("**Comentarios a mostrar:**")
            batch_size = st.radio(
                "batch", [1, 10, 30, 50, 100],
                index=[1, 10, 30, 50, 100].index(st.session_state.batch_size),
                horizontal=True, label_visibility="collapsed"
            )
            st.session_state.batch_size = batch_size
        st.divider()

    visible = all_visible if st.session_state.modo == "🤖 Automático" else all_visible[:st.session_state.batch_size]
    pending = [c for c in visible if c['comment_id'] not in st.session_state.published_ids]

    def run_batch(comentarios, generar=True, publicar=True):
        sin_generar = [c for c in comentarios if c['comment_id'] not in st.session_state.replies]
        if generar and sin_generar:
            prog = st.progress(0, text="Generando respuestas...")
            for i, c in enumerate(sin_generar):
                try:
                    st.session_state.replies[c['comment_id']] = generate_reply(c['text'])
                    st.session_state.creditos_usados += 1
                except Exception:
                    pass
                prog.progress((i + 1) / len(sin_generar), text=f"Generando {i+1}/{len(sin_generar)}...")
            prog.empty()
        if publicar:
            listos = [c for c in comentarios if c['comment_id'] in st.session_state.replies and c['comment_id'] not in st.session_state.published_ids]
            prog = st.progress(0, text="Publicando...")
            for i, c in enumerate(listos):
                try:
                    post_reply(c['comment_id'], st.session_state.replies[c['comment_id']])
                    st.session_state.published_ids.add(c['comment_id'])
                    st.session_state.published += 1
                except Exception:
                    pass
                prog.progress((i + 1) / len(listos), text=f"Publicando {i+1}/{len(listos)}...")
            prog.empty()

    # ── MODO AUTOMÁTICO ────────────────────────────────────
    if st.session_state.modo == "🤖 Automático":
        if not st.session_state.comments:
            st.info("👆 Pulsa **Buscar comentarios nuevos** para empezar.")
        elif not pending:
            st.success("🎉 ¡Todos los comentarios han sido respondidos!")
        else:
            st.info(f"Se generarán y publicarán **{len(pending)} respuestas** automáticamente sin revisión.")
            if creditos_restantes >= len(pending):
                if st.button(f"🚀 Responder {len(pending)} comentarios automáticamente", type="primary", use_container_width=True):
                    run_batch(pending, generar=True, publicar=True)
                    st.rerun()
            else:
                st.warning(f"🚫 Créditos insuficientes. Tienes {creditos_restantes} y necesitas {len(pending)}.")

    # ── MODO BULK ──────────────────────────────────────────
    elif st.session_state.modo == "⚡ Bulk":
        if not st.session_state.comments:
            st.info("👆 Pulsa **Buscar comentarios nuevos** para empezar.")
        elif not visible:
            st.success("🎉 ¡Todos los comentarios han sido revisados!")
        else:
            sin_generar = [c for c in pending if c['comment_id'] not in st.session_state.replies]
            listos = [c for c in pending if c['comment_id'] in st.session_state.replies]

            ba1, ba2 = st.columns(2)
            with ba1:
                label = f"⚡ Generar {len(sin_generar)} respuestas" if sin_generar else "⚡ Todas generadas"
                if st.button(label, type="primary", use_container_width=True, disabled=not sin_generar or creditos_restantes < len(sin_generar)):
                    run_batch(sin_generar, generar=True, publicar=False)
                    st.rerun()
            with ba2:
                label = f"✅ Publicar {len(listos)} respuestas" if listos else "✅ Nada que publicar"
                if st.button(label, use_container_width=True, disabled=not listos):
                    run_batch(listos, generar=False, publicar=True)
                    st.rerun()

            st.divider()
            for c in visible:
                cid = c['comment_id']
                is_published = cid in st.session_state.published_ids
                with st.container(border=True):
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        tag = f'<span class="author-tag replied">✅ {c["author"]}</span>' if is_published else f'<span class="author-tag">👤 {c["author"]}</span>'
                        st.markdown(tag, unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f'<a href="https://youtu.be/{c["video_id"]}" target="_blank" style="color:#9575cd;font-size:0.8rem;">🎬 Ver video</a>', unsafe_allow_html=True)
                    st.markdown(f'<div class="comment-text">{c["text"][:400]}</div>', unsafe_allow_html=True)
                    if is_published:
                        st.markdown(f'<div class="reply-sent">✅ <b>Respondido:</b> {st.session_state.replies.get(cid, "")}</div>', unsafe_allow_html=True)
                        if st.button("✖ Cerrar", key=f"close_{cid}", use_container_width=True):
                            st.session_state.closed.add(cid)
                            st.rerun()
                    elif cid in st.session_state.replies:
                        st.markdown(f'<div class="reply-sent" style="border-color:#7c3aed55;color:#c4b5fd;">🤖 {st.session_state.replies[cid]}</div>', unsafe_allow_html=True)
                    else:
                        st.caption("Pendiente de generar")

    # ── MODO ASISTIDO ──────────────────────────────────────
    elif st.session_state.modo == "🧑 Asistido":
        if not st.session_state.comments:
            st.info("👆 Pulsa **Buscar comentarios nuevos** para empezar.")
        elif not visible:
            st.success("🎉 ¡Todos los comentarios han sido revisados!")
        else:
            for c in visible:
                cid = c['comment_id']
                is_published = cid in st.session_state.published_ids
                with st.container(border=True):
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        tag = f'<span class="author-tag replied">✅ {c["author"]}</span>' if is_published else f'<span class="author-tag">👤 {c["author"]}</span>'
                        st.markdown(tag, unsafe_allow_html=True)
                    with col_b:
                        st.markdown(f'<a href="https://youtu.be/{c["video_id"]}" target="_blank" style="color:#9575cd;font-size:0.8rem;">🎬 Ver video</a>', unsafe_allow_html=True)
                    st.markdown(f'<div class="comment-text">{c["text"][:400]}</div>', unsafe_allow_html=True)

                    if is_published:
                        st.markdown(f'<div class="reply-sent">✅ <b>Respondido:</b> {st.session_state.replies.get(cid, "")}</div>', unsafe_allow_html=True)
                        if st.button("✖ Cerrar", key=f"close_{cid}", use_container_width=True):
                            st.session_state.closed.add(cid)
                            st.rerun()
                    elif cid not in st.session_state.replies:
                        if creditos_restantes == 0:
                            st.warning("🚫 Se acabaron los créditos.")
                            if st.button("💳 Conseguir 500 créditos por $10", key=f"buy_{cid}", use_container_width=True):
                                st.info("Sistema de pago próximamente disponible.")
                        else:
                            b_gen, b_skip = st.columns([3, 1])
                            with b_gen:
                                if st.button("🤖 Generar respuesta", key=f"gen_{cid}", type="primary", use_container_width=True):
                                    with st.spinner("Generando..."):
                                        try:
                                            st.session_state.replies[cid] = generate_reply(c['text'])
                                            st.session_state.creditos_usados += 1
                                            st.rerun()
                                        except RuntimeError as e:
                                            st.error(str(e))
                                        except Exception as e:
                                            st.error(f"Error inesperado: {e}")
                            with b_skip:
                                if st.button("⏭ Saltar", key=f"skip_{cid}", use_container_width=True):
                                    st.session_state.done.add(cid)
                                    st.rerun()
                    else:
                        reply_text = st.session_state.replies[cid]
                        reply = st.text_area(
                            "Respuesta sugerida",
                            value=reply_text,
                            key=f"ta_{cid}",
                            height=textarea_height(reply_text),
                            label_visibility="collapsed"
                        )
                        b1, b2, b3 = st.columns([3, 1, 1])
                        with b1:
                            if st.button("✅ Publicar", key=f"pub_{cid}", type="primary", use_container_width=True):
                                try:
                                    post_reply(cid, reply)
                                    st.session_state.published_ids.add(cid)
                                    st.session_state.published += 1
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"No se pudo publicar: {e}")
                        with b2:
                            if st.button("🔄", key=f"regen_{cid}", use_container_width=True, help="Regenerar respuesta"):
                                if creditos_restantes > 0:
                                    with st.spinner("Regenerando..."):
                                        try:
                                            del st.session_state.replies[cid]
                                            st.session_state.replies[cid] = generate_reply(c['text'])
                                            st.session_state.creditos_usados += 1
                                            st.rerun()
                                        except RuntimeError as e:
                                            st.error(str(e))
                                        except Exception as e:
                                            st.error(f"Error inesperado: {e}")
                                else:
                                    st.warning("Sin créditos para regenerar.")
                        with b3:
                            if st.button("⏭", key=f"skip2_{cid}", use_container_width=True, help="Saltar comentario"):
                                st.session_state.done.add(cid)
                                st.rerun()
