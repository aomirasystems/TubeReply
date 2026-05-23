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

T = {
    'es': {
        'welcome_sub':    '¿Listo para responder comentarios y ahorrar tiempo?',
        'start':          'INICIAR',
        'tab_comments':   '💬 Comentarios',
        'tab_style':      '✏️ Mi estilo',
        'search':         '🔍 Buscar comentarios nuevos',
        'clear':          '🧹 Limpiar',
        'mode_question':  '¿Cómo quieres responder?',
        'mode_auto':      '🤖 Automático',
        'mode_assisted':  '🧑 Asistido',
        'mode_bulk':      '⚡ Bulk',
        'batch_label':    'Comentarios a mostrar:',
        'pending':        '💬 Pendientes',
        'published':      '✅ Publicados',
        'skipped':        '⏭ Saltados',
        'credits':        '🎟️ Créditos',
        'auto_info':      'Se generarán y publicarán **{n} respuestas** automáticamente sin revisión.',
        'auto_btn':       '🚀 Responder {n} comentarios automáticamente',
        'auto_no_credits':'🚫 Créditos insuficientes. Tienes {r} y necesitas {n}.',
        'bulk_generate':  '⚡ Generar {n} respuestas',
        'bulk_all_done':  '⚡ Todas generadas',
        'bulk_publish':   '✅ Publicar {n} respuestas',
        'bulk_nothing':   '✅ Nada que publicar',
        'generate':       '🤖 Generar respuesta',
        'regenerate':     'Regenerar respuesta',
        'publish':        '✅ Publicar',
        'skip':           '⏭ Saltar',
        'skip_icon':      '⏭',
        'close':          '✖ Cerrar',
        'replied':        '✅ <b>Respondido:</b>',
        'pending_gen':    'Pendiente de generar',
        'no_credits':     '🚫 Se acabaron los créditos.',
        'buy_credits':    '💳 Conseguir 500 créditos por $10',
        'buy_soon':       'Sistema de pago próximamente disponible.',
        'no_credits_reg': 'Sin créditos para regenerar.',
        'all_reviewed':   '🎉 ¡Todos los comentarios han sido revisados!',
        'all_replied':    '🎉 ¡Todos los comentarios han sido respondidos!',
        'connecting':     'Conectando con YouTube...',
        'generating':     'Generando respuestas...',
        'gen_progress':   'Generando {i}/{n}...',
        'publishing':     'Publicando...',
        'pub_progress':   'Publicando {i}/{n}...',
        'style_title':    '### Cómo quieres que responda la IA',
        'style_sub':      'Tu tono, frases típicas, cosas a mencionar o evitar. Cuanto más detallado, mejor.',
        'style_save':     '💾 Guardar estilo',
        'style_saved':    '✅ Guardado para esta sesión.',
        'style_prompt':   'Ver prompt completo que recibe la IA',
        'no_style':       '💡 Ve a **Mi estilo** y escribe cómo quieres que responda la IA.',
        'no_connected':   'Canal de YouTube no conectado. Ejecuta `iniciar.bat` primero.',
        'start_hint':     '👆 Pulsa **Buscar comentarios nuevos** para empezar.',
        'yt_error':       'Error al conectar con YouTube: {e}',
        'pub_error':      'No se pudo publicar: {e}',
        'groq_error':     'Error inesperado: {e}',
        'warn_failed':    '⚠️ {n} comentarios fallaron por límite de API.',
        'warn_pub':       '⚠️ {n} no se pudieron publicar.',
        'lang_label':     'Idioma',
    },
    'en': {
        'welcome_sub':    'Ready to reply to comments and save time?',
        'start':          'START',
        'tab_comments':   '💬 Comments',
        'tab_style':      '✏️ My style',
        'search':         '🔍 Find new comments',
        'clear':          '🧹 Clear',
        'mode_question':  'How do you want to reply?',
        'mode_auto':      '🤖 Automatic',
        'mode_assisted':  '🧑 Assisted',
        'mode_bulk':      '⚡ Bulk',
        'batch_label':    'Comments to show:',
        'pending':        '💬 Pending',
        'published':      '✅ Published',
        'skipped':        '⏭ Skipped',
        'credits':        '🎟️ Credits',
        'auto_info':      '**{n} replies** will be generated and published automatically without review.',
        'auto_btn':       '🚀 Reply to {n} comments automatically',
        'auto_no_credits':'🚫 Not enough credits. You have {r} and need {n}.',
        'bulk_generate':  '⚡ Generate {n} replies',
        'bulk_all_done':  '⚡ All generated',
        'bulk_publish':   '✅ Publish {n} replies',
        'bulk_nothing':   '✅ Nothing to publish',
        'generate':       '🤖 Generate reply',
        'regenerate':     'Regenerate reply',
        'publish':        '✅ Publish',
        'skip':           '⏭ Skip',
        'skip_icon':      '⏭',
        'close':          '✖ Close',
        'replied':        '✅ <b>Replied:</b>',
        'pending_gen':    'Pending generation',
        'no_credits':     '🚫 Credits exhausted.',
        'buy_credits':    '💳 Get 500 credits for $10',
        'buy_soon':       'Payment system coming soon.',
        'no_credits_reg': 'Not enough credits to regenerate.',
        'all_reviewed':   '🎉 All comments have been reviewed!',
        'all_replied':    '🎉 All comments have been replied to!',
        'connecting':     'Connecting to YouTube...',
        'generating':     'Generating replies...',
        'gen_progress':   'Generating {i}/{n}...',
        'publishing':     'Publishing...',
        'pub_progress':   'Publishing {i}/{n}...',
        'style_title':    '### How do you want the AI to respond?',
        'style_sub':      'Your tone, typical phrases, things to mention or avoid. The more detail, the better.',
        'style_save':     '💾 Save style',
        'style_saved':    '✅ Saved for this session.',
        'style_prompt':   'View full prompt sent to the AI',
        'no_style':       '💡 Go to **My style** and describe how you want the AI to respond.',
        'no_connected':   'YouTube channel not connected. Run `iniciar.bat` first.',
        'start_hint':     '👆 Press **Find new comments** to start.',
        'yt_error':       'Error connecting to YouTube: {e}',
        'pub_error':      'Could not publish: {e}',
        'groq_error':     'Unexpected error: {e}',
        'warn_failed':    '⚠️ {n} comments failed due to API limit.',
        'warn_pub':       '⚠️ {n} could not be published.',
        'lang_label':     'Language',
    }
}

def t(key, **kwargs):
    lang = st.session_state.get('lang', 'es')
    text = T[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text

BASE_PROMPT = """Eres el community manager de un canal de YouTube.
Responde comentarios de fans siguiendo estas reglas base:
- Máximo 2-3 oraciones, respuestas cortas y directas
- Nunca inventes datos incorrectos
- Devuelve SOLO el texto de la respuesta, sin explicaciones adicionales

El creador del canal ha dado estas instrucciones sobre su estilo:
{contexto}"""

st.set_page_config(page_title="TubeReply", page_icon="▶️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700;800&display=swap');

/* ═══════════════════════════════════════
   HIDE STREAMLIT CHROME
═══════════════════════════════════════ */
#MainMenu,
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
.stDeployButton,
footer { display: none !important; }

/* ═══════════════════════════════════════
   BASE
═══════════════════════════════════════ */
*, *::before, *::after {
  box-sizing: border-box;
  font-family: 'Inter', -apple-system, sans-serif !important;
}

.stApp {
  background: #07010f !important;
  color: #e2d9f3 !important;
}

.block-container {
  max-width: 860px !important;
  padding: 0 1.8rem 5rem !important;
  margin: 0 auto !important;
}

/* ── Background glow ── */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 70% 55% at 8% 0%,  rgba(124,58,237,0.18) 0%, transparent 55%),
    radial-gradient(ellipse 55% 45% at 92% 98%, rgba(79,70,229,0.12)  0%, transparent 50%),
    radial-gradient(ellipse 40% 35% at 50% 50%, rgba(124,58,237,0.04) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

/* ── Noise texture ── */
.stApp::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
  opacity: 0.45;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; background: #07010f; }
::-webkit-scrollbar-thumb { background: #3b0764; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #7c3aed; }

/* ═══════════════════════════════════════
   WELCOME SCREEN
═══════════════════════════════════════ */
.welcome-screen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
}

.welcome-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(124,58,237,0.1);
  border: 1px solid rgba(124,58,237,0.3);
  border-radius: 999px;
  padding: 6px 16px;
  color: #a78bfa;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 2rem;
}

.welcome-badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #7c3aed;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(0.8); }
}

.welcome-logo {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: clamp(3rem, 10vw, 5.5rem);
  font-weight: 800;
  color: #e2d9f3;
  letter-spacing: -0.04em;
  line-height: 1;
  margin-bottom: 1.2rem;
}

.welcome-logo-accent { color: #7c3aed; }

.welcome-sub {
  color: rgba(149,117,205,0.85);
  font-size: 1.05rem;
  line-height: 1.7;
  max-width: 420px;
  margin: 0 auto 2.2rem;
}

/* Pulse glow behind start button */
.welcome-btn-wrap {
  position: relative;
  display: inline-block;
}

.welcome-btn-wrap::before {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 20px;
  background: rgba(124,58,237,0.3);
  filter: blur(18px);
  animation: glow-pulse 2.5s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.05); }
}

/* Welcome start button override */
.welcome-screen + div .stButton button,
[data-testid="stMainBlockContainer"] .stButton button[kind="primary"] {
  font-size: 1rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.15em !important;
  height: 56px !important;
  border-radius: 14px !important;
  box-shadow: 0 8px 40px rgba(124,58,237,0.5) !important;
}

/* ═══════════════════════════════════════
   HEADER
═══════════════════════════════════════ */
.tr-header {
  display: flex;
  align-items: center;
  padding: 1.8rem 0 1.4rem;
  border-bottom: 1px solid rgba(124,58,237,0.15);
  margin-bottom: 2rem;
}

.tr-logo {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 1.55rem;
  font-weight: 800;
  color: #e2d9f3;
  letter-spacing: -0.03em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tr-logo-accent { color: #7c3aed; }

.tr-sub {
  font-size: 0.65rem;
  color: rgba(107,91,149,0.75);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-top: 3px;
  font-weight: 500;
}

/* ═══════════════════════════════════════
   TABS
═══════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid rgba(124,58,237,0.15) !important;
  border-radius: 0 !important;
  gap: 0 !important;
  padding: 0 !important;
}

.stTabs [data-baseweb="tab"] {
  border-radius: 0 !important;
  background: transparent !important;
  color: rgba(107,91,149,0.8) !important;
  font-weight: 600 !important;
  font-size: 0.82rem !important;
  letter-spacing: 0.04em !important;
  padding: 12px 26px !important;
  border-bottom: 2px solid transparent !important;
  margin-bottom: -1px !important;
  transition: color 0.2s !important;
}

.stTabs [aria-selected="true"] {
  color: #e2d9f3 !important;
  border-bottom-color: #7c3aed !important;
  background: transparent !important;
}

.stTabs [data-baseweb="tab-panel"] { padding-top: 1.8rem !important; }

/* ═══════════════════════════════════════
   METRIC CARDS
═══════════════════════════════════════ */
div[data-testid="metric-container"] {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(124,58,237,0.18) !important;
  border-top: 2px solid #7c3aed !important;
  border-radius: 14px !important;
  padding: 16px 18px 14px !important;
  transition: border-color 0.2s !important;
}

div[data-testid="metric-container"]:hover {
  border-color: rgba(124,58,237,0.4) !important;
  border-top-color: #8b5cf6 !important;
}

div[data-testid="metric-container"] label {
  color: rgba(107,91,149,0.85) !important;
  font-size: 0.63rem !important;
  letter-spacing: 0.2em !important;
  text-transform: uppercase !important;
  font-weight: 700 !important;
}

div[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: #e2d9f3 !important;
  font-size: 2rem !important;
  font-weight: 800 !important;
  font-family: 'Space Grotesk', sans-serif !important;
  line-height: 1.1 !important;
}

/* ═══════════════════════════════════════
   COMMENT CARDS
═══════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
  background: rgba(255,255,255,0.022) !important;
  border: 1px solid rgba(124,58,237,0.18) !important;
  border-radius: 16px !important;
  padding: 1.3rem 1.5rem !important;
  box-shadow: 0 2px 20px rgba(0,0,0,0.25) !important;
  transition: border-color 0.25s, box-shadow 0.25s !important;
  backdrop-filter: blur(6px) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover > div {
  border-color: rgba(124,58,237,0.38) !important;
  box-shadow: 0 4px 32px rgba(124,58,237,0.1) !important;
}

/* ── Author chip ── */
.author-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(124,58,237,0.1);
  border: 1px solid rgba(124,58,237,0.28);
  border-radius: 999px;
  padding: 3px 12px 3px 8px;
  color: #c4b5fd;
  font-weight: 600;
  font-size: 0.78rem;
  letter-spacing: 0.01em;
}

.author-tag.replied {
  background: rgba(16,185,129,0.08);
  border-color: rgba(16,185,129,0.28);
  color: #6ee7b7;
}

/* ── Comment text ── */
.comment-text {
  background: rgba(0,0,0,0.2);
  border-left: 2px solid rgba(124,58,237,0.45);
  border-radius: 0 10px 10px 0;
  padding: 12px 16px;
  color: rgba(196,181,253,0.65);
  font-size: 0.875rem;
  line-height: 1.7;
  margin: 10px 0;
  font-style: italic;
}

/* ── AI reply preview ── */
.reply-ai {
  background: rgba(124,58,237,0.07);
  border: 1px solid rgba(124,58,237,0.22);
  border-radius: 10px;
  padding: 12px 16px;
  color: #c4b5fd;
  font-size: 0.875rem;
  line-height: 1.65;
  margin: 8px 0;
}

/* ── Published reply ── */
.reply-sent {
  background: rgba(16,185,129,0.06);
  border: 1px solid rgba(16,185,129,0.18);
  border-radius: 10px;
  padding: 12px 16px;
  color: #6ee7b7;
  font-size: 0.875rem;
  line-height: 1.65;
  margin: 8px 0;
}

/* ═══════════════════════════════════════
   TEXTAREA
═══════════════════════════════════════ */
.stTextArea textarea {
  background: rgba(0,0,0,0.25) !important;
  color: #e2d9f3 !important;
  border: 1px solid rgba(124,58,237,0.25) !important;
  border-radius: 10px !important;
  font-size: 0.875rem !important;
  line-height: 1.65 !important;
  resize: vertical !important;
}

.stTextArea textarea:focus {
  border-color: #7c3aed !important;
  box-shadow: 0 0 0 2px rgba(124,58,237,0.18) !important;
  outline: none !important;
}

/* ═══════════════════════════════════════
   BUTTONS
═══════════════════════════════════════ */
.stButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  font-size: 0.83rem !important;
  letter-spacing: 0.02em !important;
  transition: all 0.22s !important;
  height: 42px !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 4px 18px rgba(124,58,237,0.35) !important;
}

.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
  box-shadow: 0 6px 28px rgba(124,58,237,0.5) !important;
  transform: translateY(-1px) !important;
}

.stButton > button[kind="primary"]:active {
  transform: translateY(0) !important;
}

.stButton > button[kind="secondary"] {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(124,58,237,0.28) !important;
  color: #9575cd !important;
}

.stButton > button[kind="secondary"]:hover {
  background: rgba(124,58,237,0.1) !important;
  border-color: rgba(124,58,237,0.55) !important;
  color: #e2d9f3 !important;
}

/* ═══════════════════════════════════════
   DIVIDER
═══════════════════════════════════════ */
hr {
  border: none !important;
  height: 1px !important;
  background: linear-gradient(to right, transparent, rgba(124,58,237,0.25), transparent) !important;
  margin: 1rem 0 !important;
}

/* ═══════════════════════════════════════
   ALERTS / EXPANDER / PROGRESS
═══════════════════════════════════════ */
.stAlert {
  border-radius: 12px !important;
  border-width: 1px !important;
  font-size: 0.875rem !important;
}

details {
  background: rgba(255,255,255,0.02) !important;
  border: 1px solid rgba(124,58,237,0.18) !important;
  border-radius: 10px !important;
}

[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(to right, #7c3aed, #8b5cf6) !important;
  border-radius: 999px !important;
}

/* ═══════════════════════════════════════
   LANG TOGGLE PILL
═══════════════════════════════════════ */
div:has(> [data-testid="stRadio"][aria-label="lang2"]) > div > div[role="radiogroup"] {
  display: inline-flex !important;
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(124,58,237,0.28) !important;
  border-radius: 999px !important;
  padding: 3px !important;
  gap: 2px !important;
}

div:has(> [data-testid="stRadio"][aria-label="lang2"]) label {
  padding: 4px 12px !important;
  border-radius: 999px !important;
  font-size: 1.05rem !important;
  cursor: pointer !important;
  transition: background 0.15s !important;
  margin: 0 !important;
}

div:has(> [data-testid="stRadio"][aria-label="lang2"]) label:has(input:checked) {
  background: rgba(124,58,237,0.4) !important;
}

div:has(> [data-testid="stRadio"][aria-label="lang2"]) input[type="radio"] {
  display: none !important;
}

/* ═══════════════════════════════════════
   MODE SELECTOR PILLS
═══════════════════════════════════════ */
div:has(> [data-testid="stRadio"][aria-label="modo"]) > div > div[role="radiogroup"] {
  display: flex !important;
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(124,58,237,0.18) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  gap: 4px !important;
}

div:has(> [data-testid="stRadio"][aria-label="modo"]) label {
  flex: 1 !important;
  text-align: center !important;
  padding: 9px 16px !important;
  border-radius: 8px !important;
  font-size: 0.83rem !important;
  font-weight: 600 !important;
  color: rgba(107,91,149,0.9) !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
}

div:has(> [data-testid="stRadio"][aria-label="modo"]) label:has(input:checked) {
  background: rgba(124,58,237,0.28) !important;
  color: #e2d9f3 !important;
}

div:has(> [data-testid="stRadio"][aria-label="modo"]) input[type="radio"] {
  display: none !important;
}
</style>
""", unsafe_allow_html=True)


def get_secret(key, fallback_env=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(fallback_env or key, '')


@st.cache_resource
def get_supabase_client():
    try:
        from supabase import create_client
        url = get_secret('SUPABASE_URL')
        key = get_secret('SUPABASE_KEY')
        if url and key:
            return create_client(url, key)
    except Exception:
        pass
    return None


ESTILO_FILE = 'mi_estilo.txt'

def load_estilo():
    if 'estilo' in st.session_state:
        return st.session_state['estilo']
    try:
        sb = get_supabase_client()
        if sb:
            res = sb.table('settings').select('value').eq('key', 'estilo').execute()
            if res.data:
                val = res.data[0]['value']
                st.session_state['estilo'] = val
                return val
    except Exception:
        pass
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
    saved_to_db = False
    try:
        sb = get_supabase_client()
        if sb:
            sb.table('settings').upsert({'key': 'estilo', 'value': text}).execute()
            saved_to_db = True
    except Exception:
        pass
    try:
        with open(ESTILO_FILE, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass
    return saved_to_db

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


DEMO_COMMENTS = [
    {'comment_id': 'demo_001', 'author': 'DinoFan2024',
     'text': '¿Crees que el T-Rex realmente no podía verte si no te movías, como en Jurassic Park? 🦖',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_002', 'author': 'PaleontologíaLover',
     'text': 'Acabo de ver el video sobre el Spinosaurus, ¡increíble que fuera más grande que el T-Rex! ¿Cuál crees que ganaría en una pelea real?',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_003', 'author': 'MartinaGarcia',
     'text': '¿Es verdad que los pájaros son básicamente dinosaurios? Mi profe lo dijo y no me lo creo jaja',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_004', 'author': 'CarlosRuiz_Dinos',
     'text': 'Oye, ¿por qué los dinosaurios eran tan enormes comparados con los animales de hoy? ¿Tiene que ver con el oxígeno?',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_005', 'author': 'JuanDelMonte',
     'text': 'Me encanta tu canal, siempre aprendo algo nuevo 🦕 ¿Vas a hacer un video sobre el Brachiosaurus?',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_006', 'author': 'SofiaP_Ciencia',
     'text': '¿Cuál es el dinosaurio más grande que se ha descubierto hasta ahora? ¿El Argentinosaurus sigue siendo el campeón?',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_007', 'author': 'RobertoAlva',
     'text': 'Los velociraptors del cine son muy diferentes a los reales ¿verdad? Cuéntanos más sobre cómo eran de verdad',
     'video_id': 'dQw4w9WgXcQ'},
    {'comment_id': 'demo_008', 'author': 'IsabelCano',
     'text': '¿Cómo saben los paleontólogos de qué color eran los dinosaurios si solo quedan huesos?',
     'video_id': 'dQw4w9WgXcQ'},
]

DEMO_REPLIES = {
    'demo_001': '¡Ese mito viene directo de Crichton, pero la biología no acompaña! El T-Rex tenía visión binocular bastante desarrollada, similar a la de las águilas. Lo que sí es cierto es que detectaba mejor el movimiento. ¿Sabías que su ojo era del tamaño de una pelota de béisbol?',
    'demo_002': 'El Spinosaurus medía hasta 15m y probablemente pesaba más, pero vivían en épocas y hábitats distintos. En el agua el Spino ganaba sin duda, en tierra firme era otro cuento. ¿Tú con cuál te quedas?',
    'demo_003': '¡100% cierto y es de mis cosas favoritas! Las aves son dinosaurios terópodos que sobrevivieron a la extinción del Cretácico. Cuando ves un gorrión estás viendo un dino de verdad. ¿No te parece alucinante que el linaje siga vivo?',
    'demo_004': 'El oxígeno influía, pero también los sacos aéreos en los huesos (como en las aves actuales) y la abundante vegetación de la época. Eran eficientes de una forma que ya no existe. ¿Qué es lo que más te fascina de ese gigantismo?',
    'demo_005': '¡Gracias! El Brachiosaurus está en la lista, hay cosas nuevas sobre su locomoción que molan mucho. ¿Prefieres que enfoque más la anatomía o el ecosistema en el que vivía?',
    'demo_006': 'El Patagotitan mayorum le está quitando el trono según los estudios más recientes, aunque medir un animal por fragmentos siempre tiene margen de error. ¡La carrera al más grande nunca termina! ¿Prefieres los gigantes herbívoros o los carnívoros?',
    'demo_007': 'Exacto, los raptors reales eran del tamaño de un pavo y tenían plumas. Lo del cine fue basado en el Deinonychus con mucha licencia artística. Aunque con inteligencia similar a un cuervo moderno, seguían siendo peligrosos. ¿Te hago un video comparando cine vs realidad?',
    'demo_008': 'Con melanosomas fosilizados en plumas excepcionalmente bien preservadas, son microestructuras celulares que aún conservan información química. Solo funciona en fósiles en condiciones muy especiales, por eso solo conocemos el color de muy pocos. ¿No es una historia de detective increíble?',
}

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

def get_reply(c):
    if st.session_state.get('demo_mode'):
        import time; time.sleep(0.35)
        return DEMO_REPLIES.get(c['comment_id'],
            "¡Gracias por el comentario! ¿Qué tema de paleontología te gustaría que cubriera próximamente?")
    return generate_reply(c['text'])

def publish_reply(comment_id, text):
    if not st.session_state.get('demo_mode'):
        post_reply(comment_id, text)


# ══════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════
for key, default in [('iniciado', False), ('lang', 'es'), ('demo_mode', False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── WELCOME SCREEN ────────────────────────────────────────────
if not st.session_state.iniciado:
    st.markdown("""
    <style>
    .block-container { padding-top: 0 !important; }
    div[data-testid="stMainBlockContainer"] {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    </style>
    <div class="welcome-screen">
      <div class="welcome-badge">
        <div class="welcome-badge-dot"></div>
        AI · YouTube · Groq
      </div>
      <div class="welcome-logo">Tube<span class="welcome-logo-accent">Reply</span></div>
    </div>
    """, unsafe_allow_html=True)

    lc, cc, rc = st.columns([1, 1.3, 1])
    with cc:
        lang_choice = st.radio("lang", ["🇪🇸 Español", "🇺🇸 English"],
                               index=0 if st.session_state.lang == 'es' else 1,
                               horizontal=True, label_visibility="collapsed")
        st.session_state.lang = 'es' if 'Español' in lang_choice else 'en'
        st.markdown(
            f'<p style="text-align:center;color:rgba(149,117,205,0.85);font-size:1rem;'
            f'margin:0.6rem 0 1.8rem;line-height:1.6;">{t("welcome_sub")}</p>',
            unsafe_allow_html=True
        )
        if st.button(t('start'), type="primary", use_container_width=True):
            st.session_state.iniciado = True
            st.rerun()
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        demo_label = "👀 Ver demo" if st.session_state.lang == 'es' else "👀 View demo"
        if st.button(demo_label, use_container_width=True):
            st.session_state.demo_mode = True
            st.session_state.iniciado = True
            st.rerun()
        st.markdown(
            '<p style="text-align:center;color:rgba(107,91,149,0.5);font-size:0.72rem;margin-top:6px;">'
            + ("Sin cuenta · Sin API · Solo para ver" if st.session_state.lang == 'es' else "No account · No API · Just to explore")
            + '</p>',
            unsafe_allow_html=True
        )
    st.stop()

# ── HEADER ────────────────────────────────────────────────────
h1, h2 = st.columns([5, 1])
with h1:
    demo_badge = (
        '<span style="display:inline-flex;align-items:center;gap:6px;'
        'background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.35);'
        'border-radius:999px;padding:3px 12px;color:#fbbf24;font-size:0.68rem;'
        'font-weight:700;letter-spacing:0.15em;text-transform:uppercase;margin-left:12px;">'
        '👁 DEMO</span>'
        if st.session_state.get('demo_mode') else ''
    )
    st.markdown(f"""
    <div class="tr-header">
      <div style="display:flex;align-items:center;">
        <div>
          <div class="tr-logo">▶️&nbsp;Tube<span class="tr-logo-accent">Reply</span>{demo_badge}</div>
          <div class="tr-sub">AI · YouTube · Groq</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
with h2:
    st.markdown("<div style='padding-top:30px'></div>", unsafe_allow_html=True)
    lang_toggle = st.radio("lang2", ["🇪🇸", "🇺🇸"],
                           index=0 if st.session_state.lang == 'es' else 1,
                           horizontal=True, label_visibility="collapsed")
    st.session_state.lang = 'es' if lang_toggle == "🇪🇸" else 'en'

if not st.session_state.get('demo_mode'):
    token_ok = os.path.exists('token.json') or ('YOUTUBE_TOKEN' in (st.secrets if hasattr(st, 'secrets') else {}))
    if not token_ok:
        st.error(t('no_connected'))
        st.stop()

tab_bot, tab_estilo = st.tabs([t('tab_comments'), t('tab_style')])

# ── TAB: MI ESTILO ────────────────────────────────────────────
with tab_estilo:
    st.markdown(t('style_title'))
    st.caption(t('style_sub'))

    nuevo_estilo = st.text_area(
        label="style",
        value=load_estilo(),
        height=280,
        placeholder="""Ejemplos / Examples:
- Habla siempre en español con entusiasmo por los dinosaurios
- Usa frases como "¡Qué buena pregunta!" o "¡Exacto!"
- No uses más de 1 emoji por respuesta""",
        label_visibility="collapsed"
    )

    if st.button(t('style_save'), type="primary", use_container_width=True):
        saved_db = save_estilo(nuevo_estilo)
        if saved_db:
            st.success('✅ Guardado permanentemente.' if st.session_state.lang == 'es' else '✅ Saved permanently.')
        else:
            st.success(t('style_saved'))

    if load_estilo():
        with st.expander(t('style_prompt')):
            st.code(build_prompt(), language=None)

# ── TAB: COMENTARIOS ──────────────────────────────────────────
with tab_bot:
    for key, default in [
        ('comments', []), ('replies', {}), ('done', set()), ('closed', set()),
        ('published_ids', set()), ('published', 0), ('creditos_usados', 0),
        ('batch_size', 10), ('modo', 'Asistido')
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    if not load_estilo():
        st.warning(t('no_style'))

    col1, col2 = st.columns([3, 1])
    with col1:
        fetch = st.button(t('search'), type="primary", use_container_width=True)
    with col2:
        if st.button(t('clear'), use_container_width=True):
            for k in ['comments', 'replies', 'done', 'closed', 'published_ids']:
                st.session_state[k] = [] if k == 'comments' else {} if k == 'replies' else set()
            st.session_state.published = 0
            st.rerun()

    if fetch:
        if st.session_state.get('demo_mode'):
            import time; time.sleep(0.6)
            st.session_state.comments = DEMO_COMMENTS.copy()
            st.session_state.done = set()
            st.session_state.closed = set()
            st.session_state.replies = {}
            st.session_state.published_ids = set()
            st.session_state.published = 0
        else:
            with st.spinner(t('connecting')):
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
                    st.error(t('yt_error', e=e))

    all_visible = [c for c in st.session_state.comments
                   if c['comment_id'] not in st.session_state.done
                   and c['comment_id'] not in st.session_state.closed]
    all_pending = [c for c in all_visible if c['comment_id'] not in st.session_state.published_ids]
    creditos_restantes = max(0, LIMITE_CREDITOS - st.session_state.creditos_usados)

    if st.session_state.comments:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t('pending'),   len(all_pending))
        m2.metric(t('published'), st.session_state.published)
        m3.metric(t('skipped'),   len(st.session_state.done))
        m4.metric(t('credits'),   f"{creditos_restantes}/{LIMITE_CREDITOS}")
        st.divider()

    # ── Modo y batch ──────────────────────────────────────────
    MODOS = [t('mode_auto'), t('mode_assisted'), t('mode_bulk')]
    if st.session_state.comments:
        st.markdown(
            f'<p style="font-size:0.72rem;letter-spacing:0.18em;text-transform:uppercase;'
            f'color:#7c3aed;font-weight:700;margin-bottom:8px;">{t("mode_question")}</p>',
            unsafe_allow_html=True
        )
        modo = st.radio("modo", MODOS, index=1, horizontal=True, label_visibility="collapsed")
        st.session_state.modo = modo

        if modo != t('mode_auto'):
            st.markdown(
                f'<p style="font-size:0.72rem;letter-spacing:0.18em;text-transform:uppercase;'
                f'color:rgba(107,91,149,0.8);font-weight:700;margin:12px 0 6px;">{t("batch_label")}</p>',
                unsafe_allow_html=True
            )
            batch_size = st.radio(
                "batch", [1, 10, 30, 50, 100],
                index=[1, 10, 30, 50, 100].index(st.session_state.batch_size),
                horizontal=True, label_visibility="collapsed"
            )
            st.session_state.batch_size = batch_size
        st.divider()

    visible = all_visible if st.session_state.modo == t('mode_auto') else all_visible[:st.session_state.batch_size]
    pending = [c for c in visible if c['comment_id'] not in st.session_state.published_ids]

    def run_batch(comentarios, generar=True, publicar=True):
        sin_generar = [c for c in comentarios if c['comment_id'] not in st.session_state.replies]
        if generar and sin_generar:
            prog = st.progress(0, text=t('generating'))
            for i, c in enumerate(sin_generar):
                try:
                    st.session_state.replies[c['comment_id']] = get_reply(c)
                    st.session_state.creditos_usados += 1
                except Exception:
                    pass
                prog.progress((i + 1) / len(sin_generar), text=t('gen_progress', i=i+1, n=len(sin_generar)))
            prog.empty()
        if publicar:
            listos = [c for c in comentarios
                      if c['comment_id'] in st.session_state.replies
                      and c['comment_id'] not in st.session_state.published_ids]
            prog = st.progress(0, text=t('publishing'))
            for i, c in enumerate(listos):
                try:
                    publish_reply(c['comment_id'], st.session_state.replies[c['comment_id']])
                    st.session_state.published_ids.add(c['comment_id'])
                    st.session_state.published += 1
                except Exception:
                    pass
                prog.progress((i + 1) / len(listos), text=t('pub_progress', i=i+1, n=len(listos)))
            prog.empty()

    def render_card(c, cid, is_published, mode_key):
        with st.container(border=True):
            col_a, col_b = st.columns([5, 1])
            with col_a:
                tag_class = "author-tag replied" if is_published else "author-tag"
                icon = "✅" if is_published else "👤"
                st.markdown(f'<span class="{tag_class}">{icon} {c["author"]}</span>', unsafe_allow_html=True)
            with col_b:
                st.markdown(
                    f'<div style="text-align:right;padding-top:2px;">'
                    f'<a href="https://youtu.be/{c["video_id"]}" target="_blank" '
                    f'style="color:#6b5b95;font-size:0.78rem;text-decoration:none;'
                    f'border:1px solid rgba(107,91,149,0.3);border-radius:6px;padding:3px 8px;">'
                    f'▶ ver</a></div>',
                    unsafe_allow_html=True
                )
            st.markdown(f'<div class="comment-text">{c["text"][:400]}</div>', unsafe_allow_html=True)
            if is_published:
                st.markdown(
                    f'<div class="reply-sent">{t("replied")} {st.session_state.replies.get(cid, "")}</div>',
                    unsafe_allow_html=True
                )
                if st.button(t('close'), key=f"close_{mode_key}_{cid}", use_container_width=True):
                    st.session_state.closed.add(cid)
                    st.rerun()
            elif cid in st.session_state.replies:
                st.markdown(
                    f'<div class="reply-ai">🤖 {st.session_state.replies[cid]}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<p style="color:rgba(107,91,149,0.6);font-size:0.78rem;margin:4px 0;">'
                    f'⏳ {t("pending_gen")}</p>',
                    unsafe_allow_html=True
                )

    # ── MODO AUTOMÁTICO ───────────────────────────────────────
    if st.session_state.modo == t('mode_auto'):
        if not st.session_state.comments:
            st.info(t('start_hint'))
        elif not pending:
            st.success(t('all_replied'))
        else:
            st.info(t('auto_info', n=len(pending)))
            if creditos_restantes >= len(pending):
                if st.button(t('auto_btn', n=len(pending)), type="primary", use_container_width=True):
                    run_batch(pending, generar=True, publicar=True)
                    st.rerun()
            else:
                st.warning(t('auto_no_credits', r=creditos_restantes, n=len(pending)))

    # ── MODO BULK ─────────────────────────────────────────────
    elif st.session_state.modo == t('mode_bulk'):
        if not st.session_state.comments:
            st.info(t('start_hint'))
        elif not visible:
            st.success(t('all_reviewed'))
        else:
            sin_generar = [c for c in pending if c['comment_id'] not in st.session_state.replies]
            listos = [c for c in pending if c['comment_id'] in st.session_state.replies]
            ba1, ba2 = st.columns(2)
            with ba1:
                label = t('bulk_generate', n=len(sin_generar)) if sin_generar else t('bulk_all_done')
                if st.button(label, type="primary", use_container_width=True,
                             disabled=not sin_generar or creditos_restantes < len(sin_generar)):
                    run_batch(sin_generar, generar=True, publicar=False)
                    st.rerun()
            with ba2:
                label = t('bulk_publish', n=len(listos)) if listos else t('bulk_nothing')
                if st.button(label, use_container_width=True, disabled=not listos):
                    run_batch(listos, generar=False, publicar=True)
                    st.rerun()
            st.divider()
            for c in visible:
                cid = c['comment_id']
                render_card(c, cid, cid in st.session_state.published_ids, 'bulk')

    # ── MODO ASISTIDO ─────────────────────────────────────────
    elif st.session_state.modo == t('mode_assisted'):
        if not st.session_state.comments:
            st.info(t('start_hint'))
        elif not visible:
            st.success(t('all_reviewed'))
        else:
            for c in visible:
                cid = c['comment_id']
                is_published = cid in st.session_state.published_ids
                with st.container(border=True):
                    col_a, col_b = st.columns([5, 1])
                    with col_a:
                        tag_class = "author-tag replied" if is_published else "author-tag"
                        icon = "✅" if is_published else "👤"
                        st.markdown(f'<span class="{tag_class}">{icon} {c["author"]}</span>', unsafe_allow_html=True)
                    with col_b:
                        st.markdown(
                            f'<div style="text-align:right;padding-top:2px;">'
                            f'<a href="https://youtu.be/{c["video_id"]}" target="_blank" '
                            f'style="color:#6b5b95;font-size:0.78rem;text-decoration:none;'
                            f'border:1px solid rgba(107,91,149,0.3);border-radius:6px;padding:3px 8px;">'
                            f'▶ ver</a></div>',
                            unsafe_allow_html=True
                        )
                    st.markdown(f'<div class="comment-text">{c["text"][:400]}</div>', unsafe_allow_html=True)

                    if is_published:
                        st.markdown(
                            f'<div class="reply-sent">{t("replied")} {st.session_state.replies.get(cid, "")}</div>',
                            unsafe_allow_html=True
                        )
                        if st.button(t('close'), key=f"close_a_{cid}", use_container_width=True):
                            st.session_state.closed.add(cid)
                            st.rerun()

                    elif cid not in st.session_state.replies:
                        if creditos_restantes == 0:
                            st.warning(t('no_credits'))
                            if st.button(t('buy_credits'), key=f"buy_{cid}", use_container_width=True):
                                st.info(t('buy_soon'))
                        else:
                            b_gen, b_skip = st.columns([3, 1])
                            with b_gen:
                                if st.button(t('generate'), key=f"gen_{cid}", type="primary", use_container_width=True):
                                    with st.spinner(t('generating')):
                                        try:
                                            st.session_state.replies[cid] = get_reply(c)
                                            st.session_state.creditos_usados += 1
                                            st.rerun()
                                        except RuntimeError as e:
                                            st.error(str(e))
                                        except Exception as e:
                                            st.error(t('groq_error', e=e))
                            with b_skip:
                                if st.button(t('skip'), key=f"skip_{cid}", use_container_width=True):
                                    st.session_state.done.add(cid)
                                    st.rerun()
                    else:
                        reply_text = st.session_state.replies[cid]
                        reply = st.text_area("r", value=reply_text, key=f"ta_{cid}",
                                             height=textarea_height(reply_text),
                                             label_visibility="collapsed")
                        b1, b2, b3 = st.columns([3, 1, 1])
                        with b1:
                            if st.button(t('publish'), key=f"pub_{cid}", type="primary", use_container_width=True):
                                try:
                                    publish_reply(cid, reply)
                                    st.session_state.published_ids.add(cid)
                                    st.session_state.published += 1
                                    st.rerun()
                                except Exception as e:
                                    st.error(t('pub_error', e=e))
                        with b2:
                            if st.button("🔄", key=f"regen_{cid}", use_container_width=True, help=t('regenerate')):
                                if creditos_restantes > 0:
                                    with st.spinner(t('generating')):
                                        try:
                                            del st.session_state.replies[cid]
                                            st.session_state.replies[cid] = get_reply(c)
                                            st.session_state.creditos_usados += 1
                                            st.rerun()
                                        except RuntimeError as e:
                                            st.error(str(e))
                                        except Exception as e:
                                            st.error(t('groq_error', e=e))
                                else:
                                    st.warning(t('no_credits_reg'))
                        with b3:
                            if st.button(t('skip_icon'), key=f"skip2_{cid}", use_container_width=True, help=t('skip')):
                                st.session_state.done.add(cid)
                                st.rerun()
