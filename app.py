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
.stApp { background-color: #0d0520; }
.stTextArea textarea { background: #1a0a2e; color: #eee; border: 1px solid #7fff0055; }
.stButton > button { border-radius: 8px; font-weight: bold; }
div[data-testid="metric-container"] { background: #1a0a2e; border-radius: 10px; padding: 10px; }
</style>
""", unsafe_allow_html=True)


# ── Detectar si estamos en la nube o local ────────────────
def is_cloud():
    return hasattr(st, 'secrets') and len(st.secrets) > 0


def get_secret(key, fallback_env=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(fallback_env or key, '')


# ── Estilo: local usa archivo, nube usa session_state ─────
ESTILO_FILE = 'mi_estilo.txt'

def load_estilo():
    if 'estilo' in st.session_state:
        return st.session_state['estilo']
    # Nube: leer desde secrets
    try:
        val = st.secrets.get('CANAL_ESTILO', '')
        if val:
            return val
    except Exception:
        pass
    # Local: leer desde archivo
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


# ── Clientes ──────────────────────────────────────────────
@st.cache_resource
def get_groq_client():
    key = get_secret('GROQ_API_KEY')
    if not key or key.strip() == '':
        st.error("⚠️ Falta la Groq API key.")
        st.stop()
    return Groq(api_key=key)


@st.cache_resource
def get_yt_service():
    # Nube: token guardado como secret JSON
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
        # Local: usa el archivo token.json
        token_path = 'token.json'

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('youtube', 'v3', credentials=creds)


# ── YouTube helpers ───────────────────────────────────────
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
AVG_TOKENS_PER_REPLY = 400

def next_reset_utc():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    horas = int((reset - now).total_seconds() // 3600)
    minutos = int((reset - now).total_seconds() % 3600 // 60)
    return reset.strftime('%H:%M UTC'), horas, minutos

def get_tokens_used():
    return st.session_state.get('tokens_used', {m: 0 for m in MODELS})

def replies_remaining():
    used = get_tokens_used()
    total_remaining = sum(max(0, MODEL_LIMITS[m] - used.get(m, 0)) for m in MODELS)
    return max(0, total_remaining // AVG_TOKENS_PER_REPLY)

def generate_reply(text):
    if 'model_index' not in st.session_state:
        st.session_state.model_index = 0
    if 'tokens_used' not in st.session_state:
        st.session_state.tokens_used = {m: 0 for m in MODELS}

    for attempt in range(len(MODELS)):
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


# ── UI ────────────────────────────────────────────────────
st.markdown("# ▶️ TubeReply")
st.caption("Responde comentarios de tu canal con IA · Groq + YouTube")

token_ok = os.path.exists('token.json') or ('YOUTUBE_TOKEN' in (st.secrets if hasattr(st, 'secrets') else {}))
if not token_ok:
    st.error("Canal de YouTube no conectado.")
    st.info("Ejecuta `iniciar.bat` primero para generar el token.")
    st.stop()

tab_bot, tab_estilo = st.tabs(["💬 Comentarios", "✏️ Mi estilo"])

# ── TAB: MI ESTILO ────────────────────────────────────────
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
        st.info("Para que sea permanente: copia el texto de arriba y en Streamlit Cloud ve a **Settings → Secrets** y añade:\n```\nCANAL_ESTILO = '''tu texto aquí'''\n```")

    if load_estilo():
        with st.expander("Ver prompt completo que recibe la IA"):
            st.code(build_prompt(), language=None)

# ── TAB: COMENTARIOS ──────────────────────────────────────
with tab_bot:
    LIMITE_CREDITOS = 50
    for key, default in [('comments', []), ('replies', {}), ('done', set()), ('published_ids', set()), ('published', 0), ('creditos_usados', 0)]:
        if key not in st.session_state:
            st.session_state[key] = default

    if not load_estilo():
        st.warning("💡 Ve a **Mi estilo** y escribe cómo quieres que responda la IA.")

    col1, col2 = st.columns([3, 1])
    with col1:
        fetch = st.button("🔍 Buscar comentarios nuevos", type="primary", use_container_width=True)
    with col2:
        if st.button("🧹 Limpiar", use_container_width=True):
            st.session_state.comments = []
            st.session_state.replies = {}
            st.session_state.done = set()
            st.session_state.published_ids = set()
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
                st.session_state.replies = {}
                st.session_state.published_ids = set()
                st.session_state.published = 0
            except Exception as e:
                st.error(f"Error al conectar con YouTube: {e}")

    visible = [c for c in st.session_state.comments if c['comment_id'] not in st.session_state.done]
    pending = [c for c in visible if c['comment_id'] not in st.session_state.published_ids]

    if st.session_state.comments:
        m1, m2, m3, m4 = st.columns(4)
        creditos_restantes = max(0, LIMITE_CREDITOS - st.session_state.creditos_usados)
        m1.metric("💬 Pendientes", len(pending))
        m2.metric("✅ Publicados", st.session_state.published)
        m3.metric("⏭ Saltados", len(st.session_state.done))
        m4.metric("🎟️ Créditos", f"{creditos_restantes}/{LIMITE_CREDITOS}")
        st.divider()

    if not visible and st.session_state.comments:
        st.success("🎉 ¡Todos los comentarios han sido revisados!")
    elif visible:
        for c in visible:
            cid = c['comment_id']
            is_published = cid in st.session_state.published_ids

            with st.container(border=True):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    if is_published:
                        st.markdown(f"**👤 {c['author']}** ✅ *Respondido*")
                    else:
                        st.markdown(f"**👤 {c['author']}**")
                with col_b:
                    st.markdown(f"[🎬 Ver video](https://youtu.be/{c['video_id']})")

                st.markdown(f"> {c['text'][:400]}")
                st.divider()

                if is_published:
                    st.markdown(f"**Respuesta enviada:** {st.session_state.replies.get(cid, '')}")
                    if st.button("✖ Cerrar", key=f"close_{cid}", use_container_width=True):
                        st.session_state.done.add(cid)
                        st.rerun()
                elif cid not in st.session_state.replies:
                    creditos_restantes = max(0, LIMITE_CREDITOS - st.session_state.creditos_usados)
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
                    reply = st.text_area(
                        "🤖 Respuesta de IA — edítala si quieres:",
                        value=st.session_state.replies[cid],
                        key=f"ta_{cid}",
                        height=90
                    )

                    b1, b2 = st.columns(2)
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
                        if st.button("⏭ Saltar", key=f"skip_{cid}", use_container_width=True):
                            st.session_state.done.add(cid)
                            st.rerun()
    else:
        st.info("👆 Pulsa **Buscar comentarios nuevos** para empezar.")
