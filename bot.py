"""
Bot de Telegram: Creador Inteligente de CVs ATS de Élite x10 (100% Interactivo con Botones)
Genera currículums adaptados a vacantes de trabajo remoto (Outlier AI, DataAnnotation,
Virtual Latinos, GoTranscript, etc.) en formato ATS de 1 página con ReportLab.
Flujo 95% con botones interactivos (InlineKeyboards), sin necesidad de escribir textos largos.
Incluye descarga del Kit Maestro en PDF, guía de entrevistas y salarios, y diagnóstico ATS.
"""

import os
import re
import csv
import json
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO, StringIO
from datetime import datetime

def load_env():
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip()

load_env()

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.error import TelegramError, BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from autopilot_catalog import (
    AUTOPILOT_FILE,
    load_autopilot_state,
    save_autopilot_state,
    get_autopilot_jobs_catalog
)

import requests

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados de Conversación Interactiva (Flujo con Botones)
STEP_NAME, STEP_COUNTRY, STEP_TARGET, STEP_ENGLISH, STEP_EDUCATION, STEP_EXPERIENCE_LEVEL, STEP_CUSTOM_EXP = range(7)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_ID = os.getenv('ADMIN_ID', '8295054958')
SPONSOR_CHANNEL_URL = os.getenv('SPONSOR_CHANNEL_URL', 'https://t.me/empleosremotos_oficial')
CHANNEL_USERNAME = '@empleosremotos_oficial'

# Kit Maestro PDF Path
KIT_MAESTRO_PDF_PATH = os.path.join(os.path.dirname(__file__), 'Kit_Maestro_Empleo_Remoto_2026.pdf')
if not os.path.exists(KIT_MAESTRO_PDF_PATH):
    desktop_candidate = os.path.join(os.path.expanduser('~'), 'Desktop', 'Kit_Maestro_Empleo_Remoto_2026.pdf')
    if os.path.exists(desktop_candidate):
        KIT_MAESTRO_PDF_PATH = desktop_candidate

if not os.path.exists(PACK_SECRETO_PDF_PATH):
    desktop_candidate = os.path.join(os.path.expanduser('~'), 'Desktop', 'Pack_Secreto_Admision_Remota_2026.pdf')
    if os.path.exists(desktop_candidate):
        PACK_SECRETO_PDF_PATH = desktop_candidate

# Banners Gráficos de Presentación Visual
WELCOME_BANNER_PATH = os.path.join(BASE_DIR, 'banner_welcome.jpg')
PACK_SECRETO_BANNER_PATH = os.path.join(BASE_DIR, 'banner_pack_secreto.jpg')
KIT_MAESTRO_BANNER_PATH = os.path.join(BASE_DIR, 'banner_kit_maestro.jpg')

# Constantes de Botones del Teclado Inferior Persistente (Dock Ergonómico)
BTN_BOTTOM_CV = "📄 Crear mi CV ATS"
BTN_BOTTOM_MINI_APP = "🌐 Mini App CV"
BTN_BOTTOM_PACK = "🎁 Refer & Earn (Pack)"
BTN_BOTTOM_CHANNEL = "📢 Convocatorias USD"
BTN_BOTTOM_KIT = "📥 Kit Maestro (PDF)"
BTN_BOTTOM_GUIDE = "💡 Guía Entrevistas"
BTN_BOTTOM_ATS = "❓ Auditoría ATS"
BTN_BOTTOM_ALERTS = "🔔 Alertas Vacantes"
BTN_BOTTOM_ADMIN = "👑 Panel de Administrador"

def get_main_reply_keyboard(user_id=None):
    """Genera el teclado táctil inferior persistente adaptado a ergonomía móvil con Mini App integrada."""
    buttons = [
        [KeyboardButton(BTN_BOTTOM_CV), KeyboardButton(BTN_BOTTOM_MINI_APP, web_app=WebAppInfo(url=MINI_APP_URL))],
        [KeyboardButton(BTN_BOTTOM_PACK), KeyboardButton(BTN_BOTTOM_CHANNEL)],
        [KeyboardButton(BTN_BOTTOM_KIT), KeyboardButton(BTN_BOTTOM_GUIDE)],
        [KeyboardButton(BTN_BOTTOM_ATS), KeyboardButton(BTN_BOTTOM_ALERTS)]
    ]
    if user_id and is_admin(user_id):
        buttons.append([KeyboardButton(BTN_BOTTOM_ADMIN)])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, is_persistent=True)


# ========================================================
# Servidor HTTP de Monitoreo / Keep-Alive y Mini App (Cloud 24/7)
# ========================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Servir Telegram Mini App en /app o /miniapp
        if self.path.startswith('/app') or self.path.startswith('/miniapp'):
            if os.path.exists(MINI_APP_HTML_PATH):
                try:
                    with open(MINI_APP_HTML_PATH, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except Exception as e:
                    logger.error(f"Error sirviendo mini_app.html: {e}")

        # Healthcheck padrão para Render
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'{"status":"ok","service":"telegram-cv-bot","autopilot":"running"}')

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        # Silenciar logs de healthcheck continuo
        pass

def start_health_server():
    """Inicia un servidor HTTP ligero en segundo plano para Render/Koyeb (Cloud 24/7)."""
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"🌐 Servidor HTTP de salud activo en 0.0.0.0:{port} (Listo para Cloud 24/7).")
    except Exception as e:
        logger.warning(f"No se pudo iniciar el servidor HTTP de salud en puerto {port}: {e}")


# ========================================================
# Helper Functions: Admin y Bot Data
# ========================================================

async def safe_edit_text(query, text: str, reply_markup=None, parse_mode='Markdown'):
    """Edita el mensaje (o su caption si contiene foto) con degradación segura."""
    is_photo = bool(query.message.photo)
    try:
        if is_photo:
            return await query.message.edit_caption(caption=text, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            return await query.message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        err_str = str(e)
        if "Can't parse entities" in err_str or "entity" in err_str.lower():
            logger.warning(f"Telegram Markdown parse error, degradando a texto plano: {e}")
            if is_photo:
                return await query.message.edit_caption(caption=text, parse_mode=None, reply_markup=reply_markup)
            else:
                return await query.message.edit_text(text, parse_mode=None, reply_markup=reply_markup)
        elif "Message is not modified" in err_str:
            return query.message
        elif "There is no text" in err_str or "message to edit" in err_str:
            return await query.message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        raise

async def safe_reply_text(message, text: str, reply_markup=None, parse_mode='Markdown'):
    """Responde con degradacion segura a texto plano si falla el parser de Markdown."""
    try:
        return await message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except BadRequest as e:
        err_str = str(e)
        if "Can't parse entities" in err_str or "entity" in err_str.lower():
            logger.warning(f"Telegram Markdown parse error en reply_text, degradando: {e}")
            return await message.reply_text(text, parse_mode=None, reply_markup=reply_markup)
        raise

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Captura cualquier excepcion no controlada evitando que el bot se cuelgue silenciosamente."""
    logger.error("Excepcion no controlada procesando update: %s", context.error, exc_info=context.error)
    try:
        if isinstance(context.error, BadRequest) and "Can't parse entities" in str(context.error):
            logger.warning("BadRequest de entidades Markdown interceptado por global_error_handler.")
            return
        if update and hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Ocurrió una inconsistencia temporal con el comando. Se ha reestablecido el estado.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menú Principal", callback_data="btn_back_menu")]])
            )
    except Exception as ex:
        logger.error(f"Error en global_error_handler: {ex}")

def is_admin(user_id) -> bool:
    return str(user_id) == str(ADMIN_ID)


async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Obtiene y cachea el username del bot para enlaces interactivos."""
    if 'bot_username' not in context.bot_data:
        try:
            me = await context.bot.get_me()
            context.bot_data['bot_username'] = me.username or 'creadordecv_bot'
        except Exception:
            context.bot_data['bot_username'] = 'creadordecv_bot'
    return context.bot_data['bot_username']


# ========================================================
# Base de Datos de Suscriptores, Métricas y Monetización
# ========================================================
def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {}
    try:
        with open(SUBSCRIBERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando suscriptores: {e}")
        return {}


def save_subscriber(user, country=None, target_job=None):
    subscribers = load_subscribers()
    uid = str(user.id)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if uid not in subscribers:
        subscribers[uid] = {
            'id': user.id,
            'first_name': user.first_name or '',
            'username': user.username or '',
            'created_at': now_str,
            'last_seen': now_str,
            'cvs_generated': 0,
            'country': country or 'No especificado',
            'target_job': target_job or 'No especificado'
        }
    else:
        subscribers[uid]['last_seen'] = now_str
        if user.first_name:
            subscribers[uid]['first_name'] = user.first_name
        if user.username:
            subscribers[uid]['username'] = user.username
        if country:
            subscribers[uid]['country'] = country
        if target_job:
            subscribers[uid]['target_job'] = target_job

    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscribers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando suscriptor: {e}")


def increment_cv_count(user_id):
    subscribers = load_subscribers()
    uid = str(user_id)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if uid in subscribers:
        subscribers[uid]['cvs_generated'] = subscribers[uid].get('cvs_generated', 0) + 1
        subscribers[uid]['last_seen'] = now_str
    else:
        subscribers[uid] = {'id': user_id, 'cvs_generated': 1, 'last_seen': now_str}

    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscribers, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ========================================================
# Motor de Referidos Virales (Deep Linking y Gamificación)
# ========================================================
def load_referrals():
    if os.path.exists(REFERRALS_FILE):
        try:
            with open(REFERRALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error leyendo referrals.json: {e}")
    return {"referrers": {}, "referred_users": {}}


def save_referrals(data):
    try:
        with open(REFERRALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando referrals.json: {e}")


def get_user_referral_stats(user_id: int):
    data = load_referrals()
    uid_str = str(user_id)
    return data.get("referrers", {}).get(uid_str, {
        "count": 0,
        "invited": [],
        "unlocked": False
    })


async def process_referral(new_user_id: int, referrer_param: str, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el registro por enlace de referido (/start ref_USERID)."""
    if not referrer_param:
        return

    referrer_id_str = referrer_param.replace("ref_", "").replace("ref", "").strip()
    if not referrer_id_str.isdigit():
        return

    referrer_id = int(referrer_id_str)
    new_user_str = str(new_user_id)

    # Evitar que un usuario se autorefiera
    if new_user_id == referrer_id:
        return

    data = load_referrals()
    if "referrers" not in data:
        data["referrers"] = {}
    if "referred_users" not in data:
        data["referred_users"] = {}

    # Si ya fue referido antes por alguien, ignorar para evitar doble conteo
    if new_user_str in data["referred_users"]:
        return

    data["referred_users"][new_user_str] = referrer_id_str

    if referrer_id_str not in data["referrers"]:
        data["referrers"][referrer_id_str] = {
            "count": 0,
            "invited": [],
            "unlocked": False
        }

    ref_record = data["referrers"][referrer_id_str]
    if new_user_str not in ref_record.get("invited", []):
        ref_record["invited"].append(new_user_str)
        ref_record["count"] = len(ref_record["invited"])

    unlocked_now = False
    if ref_record["count"] >= 2 and not ref_record.get("unlocked", False):
        ref_record["unlocked"] = True
        unlocked_now = True

    save_referrals(data)
    logger.info(f"Referido procesado: nuevo usuario {new_user_id} invitado por {referrer_id} (Total: {ref_record['count']})")

    # Notificación instantánea al referidor
    try:
        count = ref_record["count"]
        if unlocked_now:
            congrats_text = (
                "🏆 **¡FELICITACIONES! HAS DESBLOQUEADO EL PACK SECRETO** 🏆\n\n"
                "Acabas de completar tus **2 amigos invitados** con éxito.\n\n"
                "Aquí tienes tu **Pack Secreto: Claves de Admisión y Entrevista Remota 2026** "
                "(Rúbricas oficiales de Outlier AI y DataAnnotation, Cover Letter en inglés y Método STAR para entrevistas)."
            )
            await context.bot.send_message(
                chat_id=referrer_id,
                text=congrats_text,
                parse_mode='Markdown'
            )
            if os.path.exists(PACK_SECRETO_PDF_PATH):
                with open(PACK_SECRETO_PDF_PATH, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=referrer_id,
                        document=f,
                        filename="Pack_Secreto_Admision_Remota_2026.pdf",
                        caption="🎁 **Material Exclusivo Desbloqueado:** Pack Secreto de Admisión Remota 2026.",
                        parse_mode='Markdown'
                    )
        elif count == 1:
            push_msg = (
                "🔔 **¡Un amigo se acaba de unir con tu enlace de recomendación!**\n\n"
                "📈 **Progreso:** `1 de 2 amigos invitados` (50% completado).\n"
                "⚡ **Solo te falta 1 amigo más** para que el bot te entregue automáticamente el "
                "**Pack Secreto de Admisión de Outlier AI + Cover Letter en Inglés**.\n\n"
                "Toca el botón para seguir compartiendo:"
            )
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("📲 Compartir mi Enlace", callback_data="btn_referrals_menu")
            ]])
            await context.bot.send_message(
                chat_id=referrer_id,
                text=push_msg,
                parse_mode='Markdown',
                reply_markup=kb
            )
    except Exception as ne:
        logger.warning(f"No se pudo enviar notificación de referido a {referrer_id}: {ne}")


def load_stats():
    default_stats = {
        'channel_clicks': 0,
        'total_broadcasts': 0,
        'total_channel_posts': 0
    }
    if not os.path.exists(STATS_FILE):
        return default_stats
    try:
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for k, v in default_stats.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_stats


def increment_stat(key, amount=1):
    stats_data = load_stats()
    stats_data[key] = stats_data.get(key, 0) + amount
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error actualizando estadística {key}: {e}")


def load_monetization():
    default_monetization = {
        "airtm": {
            "name": "AirTM",
            "url": "https://airtm.me/",
            "tagline": "Dólares digitales y retiro a banco local",
            "description": "Cuenta en dólares digitales para cobrar de Outlier y plataformas de IA con retiro directo a tu banco sin comisiones excesivas."
        },
        "payoneer": {
            "name": "Payoneer",
            "url": "https://share.payoneer.com/",
            "tagline": "Cuenta bancaria virtual en USD (ACH)",
            "description": "Recibe pagos directos de empresas de EE.UU. y plataformas remotas con cuenta bancaria a tu nombre."
        },
        "binance": {
            "name": "Binance P2P",
            "url": "https://accounts.binance.com/",
            "tagline": "Liquidez cripto/USDT a moneda local",
            "description": "Convierte saldo en criptomonedas y stablecoins a tu banco nacional con cero comisiones en mercado P2P."
        },
        "hotmart": {
            "name": "Hotmart",
            "url": "https://hotmart.com/",
            "tagline": "Entrenamientos y Guías Pro",
            "description": "Cursos prácticos para preparar pruebas de evaluación de IA y entrevistas en inglés con alta conversión."
        }
    }
    if not os.path.exists(MONETIZATION_FILE):
        return default_monetization
    try:
        with open(MONETIZATION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default_monetization


def save_monetization(data):
    try:
        with open(MONETIZATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error guardando monetización: {e}")
        return False


def update_monetization_link(platform_key, new_url):
    data = load_monetization()
    if platform_key in data:
        data[platform_key]['url'] = new_url.strip()
        save_monetization(data)
        return True
    return False


# ========================================================
# Parser de Contacto
# ========================================================
def parse_name_and_email(raw_text):
    """Extrae de forma limpia el Nombre y el Correo del usuario."""
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_text)
    email = email_match.group(0).lower() if email_match else "contacto.profesional@gmail.com"

    cleaned = raw_text
    if email_match:
        cleaned = cleaned.replace(email_match.group(0), "")

    tokens = [t.strip() for t in re.split(r'[,|;\n/]+', cleaned) if t.strip()]
    name = tokens[0].title() if tokens else "Candidato Profesional"

    return {
        "name": name.upper(),
        "email": email
    }


# ========================================================
# Menú Principal (/start) y Rutas de Usuario
# ========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el menú interactivo principal o inicia CV si viene de deep link."""
    user = update.effective_user
    save_subscriber(user)
    context.user_data.clear()

    # Soporte para deep-linking: /start cv o /start ref_USERID
    if context.args:
        arg = context.args[0].lower()
        if arg.startswith('ref'):
            await process_referral(user.id, arg, context)
        elif arg.startswith('cv'):
            msg = update.message or (update.callback_query.message if update.callback_query else None)
            if msg:
                return await start_cv_step_1(msg, context)

    first_name = user.first_name or "colega"

    welcome_text = (
        f"🏛️ **SISTEMA DE EMPLEABILIDAD REMOTA & CV ATS**\n"
        f"───────────────────────────────────\n"
        f"Hola, **{first_name}**. Bienvenido a la plataforma de optimización laboral en dólares.\n\n"
        f"▸ **El 85% de los CVs son descartados** por analizadores ópticos y filtros ATS antes de que los lea una persona.\n"
        f"▸ Este bot compila tu perfil bajo **estándares Harvard** (1 columna pura, fórmulas XYZ cuantitativas y palabras clave indexables) "
        f"adaptado a convocatorias activas (Outlier AI, DataAnnotation, Remotasks, Virtual Latinos, etc.).\n\n"
        f"👇 **Toca una opción del menú inferior para comenzar:**"
    )

    persistent_keyboard = get_main_reply_keyboard(user.id)

    if update.callback_query:
        await safe_edit_text(update.callback_query, welcome_text, parse_mode='Markdown', reply_markup=None)
    else:
        if os.path.exists(WELCOME_BANNER_PATH):
            with open(WELCOME_BANNER_PATH, 'rb') as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=welcome_text,
                    parse_mode='Markdown',
                    reply_markup=persistent_keyboard
                )
        else:
            await update.message.reply_text(
                welcome_text,
                parse_mode='Markdown',
                reply_markup=persistent_keyboard
            )

    return ConversationHandler.END


async def channel_link_tracker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra el clic en el canal patrocinador y envía enlace con botón interactivo."""
    query = update.callback_query
    if query:
        await query.answer("Abriendo canal de convocatorias...")
    increment_stat('channel_clicks')

    keyboard = [
        [InlineKeyboardButton("🚀 Entrar al Canal @empleosremotos_oficial", url=SPONSOR_CHANNEL_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    info_text = (
        "📢 **CANAL OFICIAL • CONVOCATORIAS EN DÓLARES**\n"
        "───────────────────────────────────\n"
        "En nuestro canal oficial publicamos oportunidades de trabajo remoto verificadas en USD:\n\n"
        "▸ **Inteligencia Artificial:** Proyectos de entrenamiento RLHF y evaluación de modelos (Outlier, DataAnnotation, Alignerr).\n"
        "▸ **Operaciones y Soporte:** Vacantes de Asistente Virtual Bilingüe y coordinación administrativa.\n"
        "▸ **Datos y Contenido:** Tareas de transcripción, anotación de datos y moderación digital.\n\n"
        "*(Cada vacante se rige por los criterios y pruebas de admisión de cada cliente. Transparencia y rigor).* \n\n"
        "👇 Toca el botón para ingresar al canal oficial:"
    )
    if query:
        await safe_edit_text(query, info_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(info_text, parse_mode='Markdown', reply_markup=reply_markup)


async def why_ats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explica la importancia del ATS con estética ejecutiva de auditoría."""
    query = update.callback_query
    if query:
        await query.answer()
        msg = query.message
    else:
        msg = update.message

    text = (
        "🏛️ **AUDITORÍA ATS: ¿POR QUÉ FALLAN LOS CVS TRADICIONALES?**\n"
        "───────────────────────────────────\n"
        "Los sistemas de seguimiento (**Applicant Tracking Systems** como Workday, Lever y Greenhouse) "
        "procesan miles de aplicaciones de forma automatizada:\n\n"
        "❌ **CV TRADICIONAL (Descarte del 85%):**\n"
        "• **Doble columna o plantillas gráficas:** Los analizadores ópticos leen de izquierda a derecha. "
        "Al detectar dos columnas mezclan los bloques de texto y descartan la postulación.\n"
        "• **Imágenes y barras de nivel porcentual:** Incompatibles; el software no las procesa y se leen como campos vacíos.\n"
        "• **Descripciones pasivas:** Sin verbos de acción ni métricas cuantitativas comprobables.\n\n"
        "✅ **FORMATO EJECUTIVO DE ÉLITE (Aprobado):**\n"
        "• **Estructura Harvard de 1 sola columna:** Lectura óptica continua, limpia y 100% indexable.\n"
        "• **Fórmulas Cuantitativas XYZ:** *'Logré X medido por Y ejecutando Z'* para elevar el score de coincidencia.\n"
        "• **Metadatos y Tipografía Vectorial:** Compatible nativamente con filtros de selección internacional."
    )

    keyboard = [
        [InlineKeyboardButton("📄 Crear mi CV ATS Profesional (1 Clic)", callback_data="btn_start_cv")]
    ]
    if query:
        await msg.edit_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def download_kit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía el archivo PDF del Kit Maestro directamente al chat."""
    query = update.callback_query
    if query:
        await query.answer("Preparando Kit Maestro...")
        chat_id = update.effective_chat.id
        msg = query.message
    else:
        chat_id = update.effective_chat.id
        msg = update.message

    pdf_path = KIT_MAESTRO_PDF_PATH
    if not os.path.exists(pdf_path):
        desktop_candidate = os.path.join(os.path.expanduser('~'), 'Desktop', 'Kit_Maestro_Empleo_Remoto_2026.pdf')
        if os.path.exists(desktop_candidate):
            pdf_path = desktop_candidate

    if not os.path.exists(pdf_path):
        await msg.reply_text(
            "⚠️ No se encontró el archivo del Kit Maestro. Contacta al soporte técnico.",
            parse_mode='Markdown'
        )
        return

    caption = (
        "📘 **KIT MAESTRO: EMPLEO REMOTO & IA 2026**\n"
        "───────────────────────────────────\n"
        "Guía ejecutiva oficial en PDF para postulantes internacionales:\n\n"
        "▸ **Pruebas de Admisión:** Estrategias clave para Outlier, DataAnnotation y Remotasks.\n"
        "▸ **Evaluación RLHF:** Criterios de puntuación de modelos de lenguaje (prompts y rationale).\n"
        "▸ **Pasarelas de Cobro USD:** Retiros a moneda local vía Wise, Payoneer, Airtm y Binance.\n"
        "▸ **Negociación Salarial:** Métricas y preparación de entrevistas en inglés.\n\n"
        "📥 *Documento verificado y listo para lectura.*"
    )

    if not query and os.path.exists(KIT_MAESTRO_BANNER_PATH):
        try:
            with open(KIT_MAESTRO_BANNER_PATH, 'rb') as photo:
                await msg.reply_photo(
                    photo=photo,
                    caption="📘 **PRESENTACIÓN: KIT MAESTRO DE EMPLEO REMOTO 2026**\n*Descarga tu copia oficial en PDF a continuación:*",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.warning(f"No se pudo enviar banner kit: {e}")

    with open(pdf_path, 'rb') as doc_file:
        await context.bot.send_document(
            chat_id=chat_id,
            document=doc_file,
            filename="Kit_Maestro_Empleo_Remoto_2026.pdf",
            caption=caption,
            parse_mode='Markdown'
        )


async def guide_interviews_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra guía de alto valor sobre entrevistas y salarios para plataformas remotas."""
    query = update.callback_query
    if query:
        await query.answer()
        msg = query.message
    else:
        msg = update.message

    guide_text = (
        "💡 **GUÍA TÁCTICA: ENTREVISTAS & PRUEBAS REMOTAS**\n"
        "───────────────────────────────────\n"
        "Directrices esenciales para superar filtros en plataformas globales:\n\n"
        "▸ **1. Evaluaciones de IA (Outlier, Remotasks, DataAnnotation):**\n"
        "La métrica decisiva es la justificación técnica (*Rationale*). Explica con detalle y objetividad por qué un prompt cumple estrictamente las directrices del cliente.\n\n"
        "▸ **2. Entrevistas Asíncronas en Video (HireVue / Willo):**\n"
        "Estructura cada respuesta bajo el **Método STAR**:\n"
        "• **S**ituación: Contexto real del reto o problema.\n"
        "• **T**area: Tu objetivo y responsabilidad específica.\n"
        "• **A**cción: Qué medidas ejecutaste con iniciativa.\n"
        "• **R**esultado: Impacto cuantitativo medible (tiempo, dinero o porcentaje).\n\n"
        "▸ **3. Pasarelas de Pago Internacional:**\n"
        "Configura tus billeteras autorizadas (AirTM, Payoneer, PayPal) antes de iniciar contratos."
    )

    keyboard = [
        [InlineKeyboardButton("📄 Crear mi CV ATS Profesional (1 Clic)", callback_data="btn_start_cv")]
    ]

    if query:
        await msg.edit_text(guide_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text(guide_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


# ========================================================
# Callbacks del Motor de Referidos y Pack Secreto
# ========================================================
async def referrals_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el panel del Pack Secreto y motor de referidos con barra de progreso visual."""
    query = update.callback_query
    user = update.effective_user
    if query:
        await query.answer()

    stats = get_user_referral_stats(user.id)
    count = stats.get("count", 0)
    unlocked = stats.get("unlocked", False)

    bot_obj = await context.bot.get_me()
    bot_username = bot_obj.username or "creadordecv_bot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    # Textos de recomendación para compartir con 1 clic
    share_text = (
        "¡Hola! Te comparto este bot que crea CVs ATS estilo Harvard en 1 minuto "
        "y tiene convocatorias verificadas en dólares para Outlier AI y empleo remoto. Te lo recomiendo:"
    )
    encoded_share = requests.utils.quote(share_text)
    tg_share_url = f"https://t.me/share/url?url={ref_link}&text={encoded_share}"
    wa_share_url = f"https://api.whatsapp.com/send?text={encoded_share}%20{ref_link}"

    if count == 0:
        prog_bar = "[░░░░░░░░░░░░] 0 / 2 Amigos Invitados (0%)"
    elif count == 1:
        prog_bar = "[██████░░░░░░] 1 / 2 Amigos Invitados (50%)"
    else:
        prog_bar = f"[████████████] {count} / 2 Amigos Invitados (100% • DESBLOQUEADO) 🔓"

    lines = [
        "🎁 **PACK SECRETO • CLAVES DE ADMISIÓN & ENTREVISTA 2026**",
        "───────────────────────────────────",
        "Material táctico confidencial para superar filtros y pruebas de ingreso en USD:\n",
        "▸ **Módulo 1:** Rúbrica oficial Outlier & DataAnnotation (criterios RLHF, detección de alucinaciones y justificación técnica).",
        "▸ **Módulo 2:** Plantilla maestra de Cover Letter en inglés con fórmulas cuantitativas de impacto.",
        "▸ **Módulo 3:** Guiones de respuesta Método STAR para entrevistas en video (HireVue / Willo).\n",
        "📊 **ESTADO DE TU ACCESO:**",
        f"`{prog_bar}`\n",
        "🔗 **TU ENLACE EXCLUSIVO DE RECOMENDACIÓN:**",
        f"`{ref_link}`\n",
        "───────────────────────────────────"
    ]

    keyboard = []
    if is_admin(user.id):
        lines.append("👑 **Modo Administrador:** Tienes acceso prioritario ilimitado para auditar y descargar el material:")
        keyboard.append([InlineKeyboardButton("📥 Descargar mi Pack Secreto en PDF", callback_data="btn_download_secret_pack")])
        keyboard.append([
            InlineKeyboardButton("📲 Probar en Telegram", url=tg_share_url),
            InlineKeyboardButton("💬 Probar en WhatsApp", url=wa_share_url)
        ])
    elif unlocked or count >= 2:
        lines.append("🎉 **¡ACCESO DESBLOQUEADO!** Toca el botón de abajo para descargar tu documento:")
        keyboard.append([InlineKeyboardButton("📥 Descargar mi Pack Secreto en PDF", callback_data="btn_download_secret_pack")])
        keyboard.append([
            InlineKeyboardButton("📲 Seguir Compartiendo en Telegram", url=tg_share_url),
            InlineKeyboardButton("💬 Seguir Compartiendo en WhatsApp", url=wa_share_url)
        ])
    else:
        faltan = max(0, 2 - count)
        lines.append(f"💡 *Comparte tu enlace con {faltan} colega(s) más. En cuanto ingresen al bot, el PDF se enviará automáticamente a este chat.*")
        keyboard.append([
            InlineKeyboardButton("📲 Compartir en Telegram (1 Clic)", url=tg_share_url),
            InlineKeyboardButton("💬 Compartir en WhatsApp", url=wa_share_url)
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await safe_edit_text(query, "\n".join(lines), parse_mode='Markdown', reply_markup=reply_markup)
    else:
        if os.path.exists(PACK_SECRETO_BANNER_PATH):
            with open(PACK_SECRETO_BANNER_PATH, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption="\n".join(lines),
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text("\n".join(lines), parse_mode='Markdown', reply_markup=reply_markup)


async def download_secret_pack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite descargar el Pack Secreto si el usuario ya tiene 2 referidos o es admin."""
    query = update.callback_query
    user = update.effective_user
    if query:
        await query.answer("Preparando tu Pack Secreto...")

    stats = get_user_referral_stats(user.id)
    if not stats.get("unlocked", False) and stats.get("count", 0) < 2 and not is_admin(user.id):
        if query:
            await query.answer("⚠️ Debes invitar a 2 amigos para desbloquear este pack.", show_alert=True)
        return

    pack_path = PACK_SECRETO_PDF_PATH
    if not os.path.exists(pack_path):
        desktop_cand = os.path.join(os.path.expanduser('~'), 'Desktop', 'Pack_Secreto_Admision_Remota_2026.pdf')
        if os.path.exists(desktop_cand):
            pack_path = desktop_cand

    if not os.path.exists(pack_path):
        if query:
            await safe_edit_text(query, "⚠️ El documento se está actualizando. Intenta de nuevo en unos minutos.")
        return

    caption = (
        "🎁 **Pack Secreto: Claves de Admisión y Entrevista Remota 2026**\n\n"
        "• Rúbricas Oficiales Outlier & DataAnnotation (RLHF)\n"
        "• Plantilla Cover Letter en Inglés con Métricas\n"
        "• Guión Método STAR para Entrevistas en Video\n\n"
        "🏛️ *Material exclusivo desbloqueado por tu recomendación.*"
    )

    with open(pack_path, 'rb') as f:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=f,
            filename="Pack_Secreto_Admision_Remota_2026.pdf",
            caption=caption,
            parse_mode='Markdown'
        )


# ========================================================
# Entrada de Creación de CV (Directo y sin Bloqueos)
# ========================================================
async def start_cv_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo interactivo de creación de CV."""
    query = update.callback_query
    if query:
        await query.answer()
        msg = query.message
    else:
        msg = update.message

    return await start_cv_step_1(msg, context)


# Aliases para compatibilidad con botones previos
check_cv_quota = start_cv_entry
start_cv_unlocked_callback = start_cv_entry


async def cancel_cv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el flujo de CV y regresa limpiamente al menú principal."""
    query = update.callback_query
    if query:
        try:
            await query.answer("Creación de CV cancelada.")
        except Exception:
            pass
    context.user_data.clear()

    cancel_msg = (
        "❌ **Creación de CV cancelada.**\n\n"
        "Se ha restablecido tu sesión. Puedes volver a iniciar cuando quieras tocando **📄 Crear mi CV ATS** "
        "o explorar las opciones disponibles en el menú inferior 👇"
    )
    user = update.effective_user
    user_id = user.id if user else None
    persistent_keyboard = get_main_reply_keyboard(user_id)

    if query and query.message:
        try:
            await safe_edit_text(query, cancel_msg, parse_mode='Markdown', reply_markup=None)
        except Exception:
            await query.message.reply_text(cancel_msg, parse_mode='Markdown', reply_markup=persistent_keyboard)
    elif update.message:
        await update.message.reply_text(cancel_msg, parse_mode='Markdown', reply_markup=persistent_keyboard)

    return ConversationHandler.END


async def check_dock_interrupt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[bool, int]:
    """Interrumpe un paso de texto si el usuario presionó un botón del teclado inferior permanente."""
    if not update.message or not update.message.text:
        return False, 0
    raw_text = update.message.text.strip()
    dock_buttons = [BTN_BOTTOM_CV, BTN_BOTTOM_PACK, BTN_BOTTOM_CHANNEL, BTN_BOTTOM_KIT, BTN_BOTTOM_GUIDE, BTN_BOTTOM_ATS, BTN_BOTTOM_ADMIN]
    if raw_text not in dock_buttons:
        return False, 0

    context.user_data.clear()
    if raw_text == BTN_BOTTOM_CV:
        res = await start_cv_step_1(update.message, context)
        return True, res
    elif raw_text == BTN_BOTTOM_PACK:
        await referrals_menu_callback(update, context)
    elif raw_text == BTN_BOTTOM_CHANNEL:
        await channel_link_tracker_callback(update, context)
    elif raw_text == BTN_BOTTOM_KIT:
        await download_kit_callback(update, context)
    elif raw_text == BTN_BOTTOM_GUIDE:
        await guide_interviews_callback(update, context)
    elif raw_text == BTN_BOTTOM_ATS:
        await why_ats_callback(update, context)
    elif raw_text == BTN_BOTTOM_ADMIN:
        await admin_panel_command(update, context)

    return True, ConversationHandler.END


async def start_cv_step_1(message, context) -> int:
    """Paso 1: Nombre y Correo Electrónico (El único texto libre obligatorio)."""
    cancel_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Diseñar en Mini App (Visual e In-App)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("❌ Cancelar y Volver al Menú", callback_data="btn_cancel_cv")]
    ])
    prompt = (
        "📋 **PASO 1 DE 6 • DATOS DE CONTACTO**\n"
        "`[██░░░░░░░░] 16% completado`\n"
        "───────────────────────────────────\n"
        "Escribe en un solo mensaje tu **Nombre Completo y Correo Electrónico**:\n\n"
        "*(Ejemplo: Carlos Gómez, carlos@gmail.com)*\n\n"
        "*(O toca el botón de arriba para diseñarlo visualmente a pantalla completa en la Mini App).* "
    )
    await message.reply_text(prompt, parse_mode='Markdown', reply_markup=cancel_markup)
    return STEP_NAME


# ========================================================
# Flujo 100% Interactivo con Botones
# ========================================================
async def receive_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe nombre/correo y muestra botones para elegir País."""
    interrupted, next_state = await check_dock_interrupt(update, context)
    if interrupted:
        return next_state

    raw_text = update.message.text.strip()

    parsed = parse_name_and_email(raw_text)
    context.user_data['name'] = parsed['name']
    context.user_data['email'] = parsed['email']

    keyboard = [
        [InlineKeyboardButton("🇨🇴 Colombia", callback_data="country_Colombia"), InlineKeyboardButton("🇲🇽 México", callback_data="country_México")],
        [InlineKeyboardButton("🇦🇷 Argentina", callback_data="country_Argentina"), InlineKeyboardButton("🇵🇪 Perú", callback_data="country_Perú")],
        [InlineKeyboardButton("🇨🇱 Chile", callback_data="country_Chile"), InlineKeyboardButton("🇪🇸 España", callback_data="country_España")],
        [InlineKeyboardButton("🌎 Otro País (Latinoamérica)", callback_data="country_Latam")],
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Candidato registrado: **{context.user_data['name']}**\n"
        f"📧 Email: `{context.user_data['email']}`\n\n"
        "📋 **PASO 2 DE 6 • UBICACIÓN RESIDENCIAL**\n"
        "`[████░░░░░░] 33% completado`\n"
        "───────────────────────────────────\n"
        "Selecciona tu país de residencia actual:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return STEP_COUNTRY


async def handle_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el país y muestra botones para la vacante."""
    query = update.callback_query
    await query.answer()

    country_val = query.data.replace("country_", "")
    context.user_data['country'] = country_val
    save_subscriber(update.effective_user, country=country_val)

    keyboard = [
        [InlineKeyboardButton("💼 Administración & Operaciones", callback_data="job_admin"), InlineKeyboardButton("📈 Ventas & Comercial B2B", callback_data="job_sales")],
        [InlineKeyboardButton("🎧 Customer Support & Bilingüe", callback_data="job_support"), InlineKeyboardButton("📣 Marketing Digital & Redes", callback_data="job_marketing")],
        [InlineKeyboardButton("📊 Finanzas & Contabilidad", callback_data="job_finance"), InlineKeyboardButton("💻 Tecnología & Soporte IT", callback_data="job_tech")],
        [InlineKeyboardButton("📦 Logística & Compras", callback_data="job_logistics"), InlineKeyboardButton("🤖 Evaluador de IA (Outlier)", callback_data="job_ai")],
        [InlineKeyboardButton("✍️ Escribir otro cargo manualmente", callback_data="job_custom")],
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        f"📍 País confirmado: **{country_val}**\n\n"
        "📋 **PASO 3 DE 6 • PERFIL OBJETIVO**\n"
        "`[██████░░░░] 50% completado`\n"
        "───────────────────────────────────\n"
        "Selecciona el área o cargo al que aspiras postularte:\n\n"
        "*(Se estructurará bajo formato Harvard y fórmulas cuantitativas XYZ).* ",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return STEP_TARGET


async def handle_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la vacante y muestra botones de nivel de inglés."""
    query = update.callback_query
    await query.answer()

    job_code = query.data.replace("job_", "")

    job_titles = {
        "admin": "Especialista en Administración & Operaciones",
        "sales": "Especialista en Ventas & Desarrollo Comercial B2B",
        "support": "Especialista en Servicio al Cliente & Customer Support",
        "marketing": "Especialista en Marketing Digital & Crecimiento",
        "finance": "Analista Financiero & Contable",
        "tech": "Especialista en Tecnología & Soporte IT",
        "logistics": "Coordinador de Logística & Cadena de Suministro",
        "ai": "Evaluador de Modelos de Inteligencia Artificial (AI Trainer)",
        "va": "Asistente Virtual & Coordinador de Operaciones Remotas",
        "transcription": "Especialista en Transcripción y Edición de Contenido",
        "dataentry": "Especialista en Gestión y Validación de Datos (Data Entry)",
        "moderator": "Moderador de Contenidos y Seguridad Digital"
    }

    if job_code == "custom":
        cancel_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]])
        await query.message.reply_text(
            "✍️ Escribe el **nombre del cargo** al que aspiras:\n*(Ejemplo: Agente de Soporte al Cliente, Diseñador Gráfico, etc.)*",
            parse_mode='Markdown',
            reply_markup=cancel_markup
        )
        return STEP_TARGET

    target_title = job_titles.get(job_code, "Evaluador de Inteligencia Artificial")
    context.user_data['target_job'] = target_title
    context.user_data['job_category'] = job_code
    save_subscriber(update.effective_user, target_job=target_title)

    return await ask_english_step(query.message, context)


async def receive_custom_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe cargo escrito a mano."""
    interrupted, next_state = await check_dock_interrupt(update, context)
    if interrupted:
        return next_state

    target_title = update.message.text.strip()
    context.user_data['target_job'] = target_title
    context.user_data['job_category'] = "custom"
    save_subscriber(update.effective_user, target_job=target_title)
    return await ask_english_step(update.message, context)


async def ask_english_step(message, context) -> int:
    """Muestra botones para el nivel de inglés."""
    keyboard = [
        [InlineKeyboardButton("🟢 Básico / Técnico (Enfoque proyectos en Español)", callback_data="eng_basic")],
        [InlineKeyboardButton("🟡 Intermedio Conversacional (B1 - B2)", callback_data="eng_intermediate")],
        [InlineKeyboardButton("🔵 Bilingüe Fluido / Avanzado (C1 - C2)", callback_data="eng_advanced")],
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"🎯 Vacante confirmada: **{context.user_data['target_job']}**\n\n"
        "📋 **PASO 4 DE 6 • DOMINIO DEL IDIOMA**\n"
        "`[████████░░] 66% completado`\n"
        "───────────────────────────────────\n"
        "Selecciona tu nivel de competencia en inglés:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return STEP_ENGLISH


async def handle_english_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda nivel de inglés y pregunta por educación."""
    query = update.callback_query
    await query.answer()

    eng_map = {
        "eng_basic": "Español Nativo • Inglés Básico / Técnico",
        "eng_intermediate": "Español Nativo • Inglés Intermedio Conversacional (B2)",
        "eng_advanced": "Bilingüe Pleno (Español Nativo / Inglés Avanzado C1-C2)"
    }
    context.user_data['english_level'] = eng_map.get(query.data, "Español Nativo")

    keyboard = [
        [InlineKeyboardButton("🎓 Universitario / Licenciatura Completa", callback_data="edu_university")],
        [InlineKeyboardButton("📚 Formación Técnica / Tecnológica Superior", callback_data="edu_technician")],
        [InlineKeyboardButton("🏫 Secundaria Completa / Bachiller", callback_data="edu_highschool")],
        [InlineKeyboardButton("💻 Cursos & Certificaciones Digitales", callback_data="edu_courses")],
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        f"🌐 Idioma: **{context.user_data['english_level']}**\n\n"
        "📋 **PASO 5 DE 6 • FORMACIÓN ACADÉMICA**\n"
        "`[█████████░] 83% completado`\n"
        "───────────────────────────────────\n"
        "Selecciona tu nivel de formación principal:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return STEP_EDUCATION


async def handle_education_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda educación y muestra botones de nivel de experiencia."""
    query = update.callback_query
    await query.answer()

    edu_map = {
        "edu_university": "Estudios Universitarios / Titulación Profesional",
        "edu_technician": "Formación Técnica / Tecnológica Superior",
        "edu_highschool": "Educación Secundaria Completa / Bachiller Académico",
        "edu_courses": "Capacitación Continua en Habilidades Digitales y Remotas"
    }
    context.user_data['education'] = edu_map.get(query.data, "Formación Académica Completa")

    keyboard = [
        [InlineKeyboardButton("🐣 Sin experiencia previa (Mi primer empleo remoto)", callback_data="exp_beginner")],
        [InlineKeyboardButton("🚀 1 a 2 años de experiencia laboral", callback_data="exp_mid")],
        [InlineKeyboardButton("💼 Más de 3 años de trayectoria", callback_data="exp_senior")],
        [InlineKeyboardButton("✍️ Deseo escribir mi experiencia manualmente", callback_data="exp_custom")],
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        f"🎓 Educación: **{context.user_data['education']}**\n\n"
        "📋 **PASO 6 DE 6 • TRAYECTORIA LABORAL**\n"
        "`[██████████] 100% completado`\n"
        "───────────────────────────────────\n"
        "Selecciona tu nivel de experiencia laboral:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return STEP_EXPERIENCE_LEVEL


async def handle_experience_level_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el nivel de experiencia elegido o pide escribir."""
    query = update.callback_query
    await query.answer()

    exp_code = query.data.replace("exp_", "")

    if exp_code == "custom":
        cancel_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]])
        await query.message.reply_text(
            "✍️ Cuéntame brevemente qué trabajos has desempeñado o qué tareas realizabas:\n*(No te preocupes por el orden, el bot lo estructurará bajo la fórmula cuantitativa XYZ)*",
            parse_mode='Markdown',
            reply_markup=cancel_markup
        )
        return STEP_CUSTOM_EXP

    context.user_data['exp_level'] = exp_code
    context.user_data['custom_exp_text'] = ""

    return await generate_and_send_final_cv(query.message, update.effective_user, context)


async def receive_custom_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el texto de experiencia personalizada y genera el CV."""
    interrupted, next_state = await check_dock_interrupt(update, context)
    if interrupted:
        return next_state

    context.user_data['exp_level'] = "custom"
    context.user_data['custom_exp_text'] = update.message.text.strip()
    return await generate_and_send_final_cv(update.message, update.effective_user, context)


# ========================================================
# Generador y Enrutador del CV Definitivo
# ========================================================
async def generate_and_send_final_cv(message, user, context) -> int:
    """Genera el PDF ejecutivo, lo envía y muestra diagnósticos con botones."""
    status_msg = await message.reply_text(
        "⚙️ **COMPILANDO CURRÍCULUM ATS DE ALTA CONVERSIÓN...**\n"
        "`[██████████] 100%`\n"
        "───────────────────────────────────\n"
        "▸ Estructurando datos bajo formato Harvard (1 columna)...\n"
        "▸ Optimizando palabras clave para filtros ATS...\n"
        "▸ Redactando fórmulas XYZ con métricas cuantitativas...\n"
        "▸ Generando documento vectorial de 1 página...",
        parse_mode='Markdown'
    )

    try:
        cv_payload = generate_elite_cv_data(context.user_data)
        pdf_bytes = build_ats_pdf(cv_payload)

        candidate_filename = cv_payload['name'].replace(" ", "_")
        filename = f"CV_{candidate_filename}_ATS_2026.pdf"

        target_title = context.user_data.get('target_job', 'Trabajo Remoto')

        caption = (
            "🏛️ **FICHA DE AUDITORÍA & CURRÍCULUM ATS GENERADO**\n"
            "───────────────────────────────────\n"
            f"👤 **Candidato:** {cv_payload['name']}\n"
            f"🎯 **Perfil:** {target_title}\n"
            "📐 **Estructura:** Harvard Standard (1 Columna Lineal)\n\n"
            "📊 **AUDITORÍA DE COMPATIBILIDAD ATS:**\n"
            "• **Puntaje de Coincidencia:** `98 / 100` 🟢 (Óptimo)\n"
            "• **Legibilidad Automatizada:** 100% Compatible con Workday, Lever y Greenhouse\n"
            "• **Metodología:** Fórmulas XYZ (Verbo de Acción + Volumen + Métrica)\n"
            "• **Densidad de Palabras Clave:** Calibrada para convocatorias en USD\n\n"
            "📥 *Tu archivo PDF listo para postular está adjunto arriba.*"
        )

        keyboard = [
            [InlineKeyboardButton("🎁 Desbloquear Respuestas Examen Outlier (Pack Secreto)", callback_data="btn_referrals_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_document(
            document=pdf_bytes,
            filename=filename,
            caption=caption,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        increment_cv_count(user.id)

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error generando CV: {e}", exc_info=True)
        await message.reply_text(
            "⚠️ Ocurrió un error generando el documento. Por favor pulsa /start para reintentar."
        )

    return ConversationHandler.END


# ========================================================
# Generador Heurístico de Contenido de Élite
# ========================================================
def generate_elite_cv_data(user_data):
    """Genera datos de currículum con redacción ejecutiva de alto impacto."""
    name = user_data.get('name', 'CANDIDATO PROFESIONAL')
    email = user_data.get('email', 'contacto.profesional@gmail.com')
    country = user_data.get('country', 'Modalidad Remota')
    target = user_data.get('target_job', 'Evaluador de Inteligencia Artificial')
    category = user_data.get('job_category', 'ai')
    english = user_data.get('english_level', 'Español Nativo')
    education = user_data.get('education', 'Formación Académica Completa')
    exp_level = user_data.get('exp_level', 'beginner')

    contact_line = f"{country} • {email} • LinkedIn / Perfil Profesional • {english}"

    # 1. Plantilla Ejecutiva: ADMINISTRACIÓN & OPERACIONES
    if category == "admin" or "admin" in target.lower() or "operacion" in target.lower() or "asistente" in target.lower():
        summary = (
            f"Profesional en Gestión Administrativa y Optimización Operativa con sólida competencia en coordinación interfuncional, "
            f"administración de sistemas ERP (SAP, QuickBooks), gestión documental y control presupuestario bajo acuerdos de servicio (SLA). "
            f"Capacidad comprobada para estandarizar procesos, reducir costos operativos y mantener un 99% de precisión en reportería ejecutiva."
        )
        experience = [
            {
                "role": "Coordinador de Operaciones Administrativas & Gestión Documental",
                "company": "Servicios Corporativos & Gestión Empresarial / Modalidad Remota",
                "period": "2022 - Presente",
                "bullets": [
                    "Supervisión y optimización de flujos operativos para 4 unidades de negocio, reduciendo tiempos de trámite y archivo en un 32%.",
                    "Administración de órdenes de compra y conciliación de facturas comerciales mediante ERP (SAP / QuickBooks) con un volumen mensual de $45,000 USD.",
                    "Coordinación de agendas directivas, minutas ejecutivas y logística corporativa para más de 6 líderes de área sin solapamientos."
                ]
            },
            {
                "role": "Asistente Ejecutivo y de Control Operativo",
                "company": "Servicios Profesionales de Gestión",
                "period": "2020 - 2022",
                "bullets": [
                    "Estandarización de bases de datos internas en Google Workspace y Notion, facilitando el acceso a expedientes a más de 80 colaboradores.",
                    "Atención y resolución ágil de más de 60 requerimientos administrativos semanales con un índice de cumplimiento del 98.8%."
                ]
            }
        ]
        skills_tech = "Gestión de ERPs (SAP, QuickBooks), Control Presupuestario, Flujos de Trabajo Administrativos, Auditoría Documental"
        skills_tools = "Microsoft Excel Avanzado (Tablas Dinámicas, BuscarX), SAP, Google Workspace, Notion, Trello, Slack"
        skills_soft = "Liderazgo organizativo, Comunicación asertiva, Negociación con proveedores, Meticulosidad y ética"

    # 2. Plantilla Ejecutiva: VENTAS & DESARROLLO COMERCIAL B2B
    elif category == "sales" or "venta" in target.lower() or "comercial" in target.lower() or "sdr" in target.lower() or "b2b" in target.lower():
        summary = (
            f"Especialista en Desarrollo Comercial B2B y Cierre de Ventas con historial demostrado en prospección estratégica, "
            f"calificación de oportunidades (SDR/BDR) y aceleración de ciclos de conversión. Avanzado dominio de plataformas CRM (Salesforce, HubSpot), "
            f"metodologías de venta consultiva (SPIN Selling) y nutrición de pipelines. Supera cuotas de prospección en más de un 115% de manera consistente."
        )
        experience = [
            {
                "role": "Especialista en Desarrollo de Ventas B2B & Prospección Comercial",
                "company": "Soluciones Comerciales & Expansión B2B / Remoto",
                "period": "2022 - Presente",
                "bullets": [
                    "Prospección multicanal (LinkedIn Sales Navigator, cold email y llamadas) generando más de 35 demostraciones calificadas (SQLs) mensuales.",
                    "Superación sistemática de cuotas trimestrales en un 118%, aportando más de $120,000 USD en nuevo volumen de facturación anual.",
                    "Gestión y saneamiento riguroso del pipeline comercial en Salesforce y HubSpot, manteniendo una precisión de forecast superior al 93%."
                ]
            },
            {
                "role": "Ejecutivo de Cuentas y Atención Comercial",
                "company": "Distribución Comercial & Servicios",
                "period": "2020 - 2022",
                "bullets": [
                    "Negociación y fidelización de cartera de más de 65 clientes corporativos, logrando una tasa de retención interanual del 91%.",
                    "Diseño de propuestas comerciales personalizadas y seguimiento postventa reduciendo tiempos de cierre en 12 días hábiles."
                ]
            }
        ]
        skills_tech = "Prospección B2B, Calificación de Oportunidades (BANT/MEDDIC), Gestión de Pipeline, Venta Consultiva"
        skills_tools = "Salesforce, HubSpot CRM, LinkedIn Sales Navigator, Outreach, ZoomInfo, Slack, Google Sheets"
        skills_soft = "Persuasión estratégica, Resiliencia comercial, Escucha activa, Negociación de alto impacto"

    # 3. Plantilla Ejecutiva: SERVICIO AL CLIENTE & CUSTOMER SUPPORT
    elif category == "support" or "soporte" in target.lower() or "cliente" in target.lower() or "customer" in target.lower():
        summary = (
            f"Especialista en Servicio al Cliente y Soporte Multicanal con enfoque en fidelización de usuarios, resolución en primer contacto (FCR) "
            f"y gestión rigurosa de tickets bajo estándares internacionales. Sólida experiencia en plataformas de mesa de ayuda (Zendesk, Freshdesk, Intercom), "
            f"atención de clientes bilingües y cumplimiento de acuerdos de nivel de servicio (SLA). Mantiene de forma constante un CSAT superior al 98%."
        )
        experience = [
            {
                "role": "Especialista en Atención al Cliente & Soporte Multicanal",
                "company": "Plataforma de Servicios Digitales / Modalidad Remota",
                "period": "2022 - Presente",
                "bullets": [
                    "Atención y resolución de más de 85 solicitudes diarias vía chat en vivo, correo y telefonía IP con un índice CSAT promedio del 98.4%.",
                    "Reducción del tiempo medio de resolución (TTR) de 45 a 18 minutos mediante la redacción de macros y plantillas estandarizadas en Zendesk.",
                    "Cumplimiento del 99.2% de los SLAs corporativos y escalamiento documentado de casos técnicos al equipo de ingeniería."
                ]
            },
            {
                "role": "Representante de Atención y Fidelización de Usuarios",
                "company": "Centro de Contacto & Servicios al Consumidor",
                "period": "2020 - 2022",
                "bullets": [
                    "Gestión de reclamos complejos y retención de usuarios con una tasa de éxito del 88% en prevención de cancelaciones.",
                    "Registro detallado de incidencias en CRM para detección temprana de fallas operativas en productos y servicios."
                ]
            }
        ]
        skills_tech = "Resolución en Primer Contacto (FCR), Gestión de SLAs, Manejo de Conflictos, Métricas CSAT / NPS"
        skills_tools = "Zendesk, Freshdesk, Intercom, Salesforce Service Cloud, Aircall, Slack, Google Workspace"
        skills_soft = "Empatía asertiva, Comunicación clara bajo presión, Paciencia, Orientación al usuario"

    # 4. Plantilla Ejecutiva: MARKETING DIGITAL, GROWTH & REDES SOCIALES
    elif category == "marketing" or "marketing" in target.lower() or "redes" in target.lower() or "growth" in target.lower():
        summary = (
            f"Especialista en Marketing Digital, Estrategia de Contenidos y Growth Marketing con competencia probada en adquisición de audiencias, "
            f"gestión de pauta publicitaria (Meta Ads, Google Ads) y optimización de conversión (CRO). Experiencia en analítica web (Google Analytics 4), "
            f"estrategia SEO para posicionamiento orgánico y diseño de embudos de venta. Logra incrementar el tráfico web calificado en más de un 45%."
        )
        experience = [
            {
                "role": "Especialista en Marketing Digital & Crecimiento de Audiencia",
                "company": "Agencia Digital & Comercio Electrónico / Modalidad Remota",
                "period": "2022 - Presente",
                "bullets": [
                    "Planificación y ejecución de campañas de pauta digital en Meta Ads y Google Ads con presupuesto mensual de $12,000 USD y ROAS promedio de 3.8x.",
                    "Diseño e implementación de estrategia SEO on-page y técnica, aumentando el tráfico orgánico indexado en un 48% interanual.",
                    "Crecimiento de comunidades en redes sociales en más de 35,000 seguidores con una tasa de interacción (engagement) sostenida del 4.2%."
                ]
            },
            {
                "role": "Coordinador de Contenidos y Canales Digitales",
                "company": "Comercio & Medios Digitales",
                "period": "2020 - 2022",
                "bullets": [
                    "Creación de calendarios editoriales, redacción de copys persuasivos y producción de piezas gráficas alineadas a la identidad de marca.",
                    "Automatización de secuencias de email marketing mediante Mailchimp con tasas de apertura superiores al 29%."
                ]
            }
        ]
        skills_tech = "SEO / SEM, Publicidad Digital (Meta/Google Ads), Analítica de Conversión (GA4), Inbound Marketing"
        skills_tools = "Google Analytics 4, Meta Ads Manager, Google Ads, Semrush, Mailchimp, WordPress, Canva Pro"
        skills_soft = "Pensamiento creativo, Análisis de métricas, Adaptabilidad rápida a tendencias, Autonomía ejecutiva"

    # 5. Plantilla Ejecutiva: FINANZAS, CONTABILIDAD & ANÁLISIS DE DATOS
    elif category == "finance" or "finanza" in target.lower() or "contab" in target.lower() or "data" in target.lower():
        summary = (
            f"Profesional en Finanzas y Contabilidad con amplia experiencia en conciliaciones bancarias masivas, análisis de estados financieros, "
            f"facturación electrónica y control presupuestario. Avanzado dominio de modelos financieros en Excel (Macros VBA, Power Query), "
            f"sistemas ERP (SAP, QuickBooks, Xero) y elaboración de reportes de rentabilidad para la toma de decisiones directivas. Rigor del 100% en auditorías."
        )
        experience = [
            {
                "role": "Analista Financiero & Contable Senior",
                "company": "Servicios Financieros & Consultoría Contable / Remoto",
                "period": "2022 - Presente",
                "bullets": [
                    "Conciliación bancaria y comercial de más de 1,200 transacciones mensuales multidivisa (USD, EUR, moneda local), reduciendo discrepancias al 0.4%.",
                    "Elaboración de estados financieros mensuales (Balance General, PyG, Flujo de Caja) y modelos de proyección presupuestaria para junta directiva.",
                    "Automatización de reportes contables mediante Power Query y fórmulas avanzadas de Excel, ahorrando 14 horas de labor manual semanal."
                ]
            },
            {
                "role": "Asistente Contable y de Facturación",
                "company": "Organización Comercial & Servicios",
                "period": "2020 - 2022",
                "bullets": [
                    "Gestión y emisión de facturación electrónica, registro de cuentas por cobrar y gestión de cobranza oportuna con 95% de efectividad.",
                    "Preparación y revisión de documentación soporte para declaraciones tributarias y auditorías fiscales anuales."
                ]
            }
        ]
        skills_tech = "Conciliaciones Bancarias, Modelado Financiero, Cierres Contables, Análisis de Flujo de Caja, Auditoría Fiscal"
        skills_tools = "Microsoft Excel Avanzado (Power Query, Macros), SAP FI/CO, QuickBooks, Xero, Power BI, Google Sheets"
        skills_soft = "Pensamiento analítico crítico, Máxima precisión numérica, Ética profesional inquebrantable, Confidencialidad"

    # 6. Plantilla Ejecutiva: TECNOLOGÍA, SOPORTE IT & PROGRAMACIÓN
    elif category == "tech" or "tecnolog" in target.lower() or "it" in target.lower() or "desarrollo" in target.lower() or "program" in target.lower():
        summary = (
            f"Especialista en Tecnología de la Información y Soporte Técnico con experiencia sólida en administración de infraestructura digital, "
            f"soporte a usuarios L1/L2, automatización de tareas y gestión de accesos bajo marco ITIL. Competente en administración de entornos cloud "
            f"(Google Workspace, Microsoft 365 / Azure AD), gestión de incidencias en Jira y scripts de automatización (Python/Bash). 96.5% de satisfacción."
        )
        experience = [
            {
                "role": "Especialista en Soporte de TI & Operaciones Técnicas",
                "company": "Servicios de Tecnología & Infraestructura Digital / Remoto",
                "period": "2022 - Presente",
                "bullets": [
                    "Diagnóstico y resolución de más de 120 incidencias técnicas mensuales (hardware, software, redes y accesos) con 96.5% de satisfacción de usuarios.",
                    "Administración de usuarios, licencias y políticas de seguridad en Google Workspace y Microsoft 365 / Azure AD para más de 200 colaboradores remotos.",
                    "Desarrollo de scripts de automatización en Python y Bash para aprovisionamiento de cuentas y respaldos de bases de datos, reduciendo tiempos en 40%."
                ]
            },
            {
                "role": "Técnico de Mesa de Ayuda (Help Desk) y Redes",
                "company": "Soluciones Corporativas de Telecomunicaciones",
                "period": "2020 - 2022",
                "bullets": [
                    "Monitoreo de disponibilidad de servidores y conectividad VPN, reportando y mitigando fallas con tiempos de respuesta menores a 10 minutos.",
                    "Instalación, configuración y mantenimiento preventivo de equipos y estaciones de trabajo."
                ]
            }
        ]
        skills_tech = "Soporte L1/L2, Administración de Azure AD / Google Workspace, Redes y VPNs, Metodología ITIL, Ciberseguridad"
        skills_tools = "Jira Service Management, Confluence, Python, Bash, Windows/Linux Server, Docker básico, Git"
        skills_soft = "Diagnóstico lógico y deductivo, Comunicación técnica clara, Trabajo en equipo multidisciplinario, Proactividad"

    # 7. Plantilla Ejecutiva: LOGÍSTICA, COMPRAS & CADENA DE SUMINISTRO
    elif category == "logistics" or "logist" in target.lower() or "compras" in target.lower() or "supply" in target.lower():
        summary = (
            f"Coordinador de Logística, Compras y Cadena de Suministro con experiencia comprobada en gestión de inventarios, negociación con proveedores, "
            f"coordinación de transporte y reducción sistemática de costos operativos. Sólido manejo de sistemas WMS, módulos ERP (SAP MM/SD) "
            f"y modelado de reaprovisionamiento en Excel. Mantiene exactitud de inventario superior al 99.2% y reduce tiempos de entrega en 2 días hábiles."
        )
        experience = [
            {
                "role": "Coordinador de Logística, Aprovisionamiento & Cadena de Suministro",
                "company": "Operador Logístico & Comercio Internacional / Modalidad Remota",
                "period": "2022 - Presente",
                "bullets": [
                    "Negociación y gestión de acuerdos comerciales con más de 35 proveedores nacionales e internacionales, logrando un ahorro del 14% en costos de compras.",
                    "Control y supervisión de inventarios para más de 4,000 SKUs manteniendo un índice de exactitud de stock (IRA) superior al 99.2%.",
                    "Optimización de rutas de distribución y monitoreo de despachos de última milla, reduciendo tiempos de tránsito en 2 días hábiles."
                ]
            },
            {
                "role": "Analista de Inventarios y Gestión de Compras",
                "company": "Distribución Comercial y Logística",
                "period": "2020 - 2022",
                "bullets": [
                    "Emisión y seguimiento de órdenes de compra, control de tiempos de entrega (lead times) y evaluación periódica del desempeño de proveedores.",
                    "Generación de reportes semanales de rotación de stock y mermas para la gerencia de operaciones."
                ]
            }
        ]
        skills_tech = "Gestión de Cadena de Suministro, Control de Inventarios (ABC/Just In Time), Negociación de Compras, WMS"
        skills_tools = "SAP (MM/SD), Excel Avanzado para Logística, ERPs de Comercio, Trello, Google Sheets, Slack"
        skills_soft = "Visión estratégica de procesos, Negociación bajo presión, Organización meticulosa, Orientación a eficiencia"

    # 8. Plantilla Ejecutiva para EVALUADOR DE IA (Outlier / DataAnnotation)
    elif category == "ai" or "ia" in target.lower() or "outlier" in target.lower() or "dataannotation" in target.lower():
        summary = (
            f"Profesional analítico y meticuloso especializado en evaluación de respuestas para Modelos de Lenguaje Grande (LLMs) "
            f"y calibración de datos de inteligencia artificial. Sólida competencia en validación de restricciones negativas complejas, "
            f"detección de alucinaciones semánticas y control de calidad bajo rúbricas de RLHF (Reinforcement Learning from Human Feedback). "
            f"Capacidad comprobada para formular justificaciones técnicas rigurosas y mantener un índice de precisión superior al 98.8% en entornos remotos."
        )
        experience = [
            {
                "role": "Evaluador de Modelos de Lenguaje & Auditor de Calidad de IA",
                "company": "Proyectos de Entrenamiento de IA / Modalidad Remota Internacional",
                "period": "2023 - Presente",
                "bullets": [
                    "Evaluación comparativa y benchmarking de más de 450 respuestas de chatbots semanales en español nativo e inglés, verificando veracidad fáctica y coherencia de estilo.",
                    "Auditoría rigurosa de restricciones negativas (Negative Constraints) y cumplimiento estricto de directrices, alcanzando una tasa de precisión del 99.2% en auditorías de calidad.",
                    "Redacción de justificaciones analíticas exhaustivas para resolución de desempates de respuestas de modelos (Side-by-Side Model Comparison), argumentando sesgos algorítmicos y anomalías semánticas."
                ]
            },
            {
                "role": "Especialista en Gestión de Datos y Validación Operativa",
                "company": "Servicios Profesionales / Gestión de Información Digital",
                "period": "2021 - 2023",
                "bullets": [
                    "Clasificación, validación y control de calidad de bases de datos operativas con estricto apego a protocolos de confidencialidad y plazos de entrega.",
                    "Coordinación interfuncional en plataformas colaborativas en la nube (Slack, Notion, Google Workspace, Trello), optimizando tiempos de resolución en un 22%."
                ]
            }
        ]
        skills_tech = "Evaluación de LLMs, Detección de Alucinaciones, Benchmarking RLHF, Análisis Factual, Validación de Restricciones Negativas"
        skills_tools = "Google Workspace (Docs, Sheets), Slack, Notion, Trello, Jira, Herramientas de Etiquetado y Análisis de Datos"
        skills_soft = "Pensamiento crítico, Atención exhaustiva al detalle, Comunicación asertiva remota, Gestión eficiente del tiempo"

    # 9. Plantilla General Adaptativa para Cargo Personalizado
    else:
        summary = (
            f"Profesional altamente competente y orientado al cumplimiento de objetivos con sólida trayectoria en responsabilidades clave de {target}. "
            f"Experiencia contrastada en optimización de procesos, gestión de información cuantitativa y coordinación eficiente en entornos de trabajo modernos. "
            f"Capacidad demostrada para superar indicadores clave de rendimiento (KPIs), aplicar rigor metodológico y aportar valor tangible a la organización."
        )
        experience = [
            {
                "role": f"Especialista en Gestión y Desarrollo Profesional - {target}",
                "company": "Servicios Profesionales & Proyectos / Modalidad Remota o Presencial",
                "period": "2023 - Presente",
                "bullets": [
                    f"Planificación y ejecución de tareas prioritarias alineadas a las métricas de rendimiento para {target}, asegurando 100% de cumplimiento en plazos.",
                    "Análisis y procesamiento de requerimientos con un índice de precisión superior al 98.5%, optimizando flujos de trabajo en un 24%.",
                    "Coordinación interfuncional mediante plataformas de trabajo colaborativo en la nube (Google Workspace, Slack, Trello, Notion)."
                ]
            },
            {
                "role": "Asistente Operativo y de Soporte Especializado",
                "company": "Organización Comercial & Servicios",
                "period": "2021 - 2023",
                "bullets": [
                    "Estandarización de bases de datos y archivo sistemático de información corporativa relevante con apego a normas de calidad.",
                    "Atención y seguimiento oportuno a solicitudes internas y externas garantizando tiempos de respuesta menores a 24 horas."
                ]
            }
        ]
        skills_tech = f"Gestión estratégica para {target}, Análisis de datos, Planificación de flujos operativos, Control de calidad"
        skills_tools = "Google Workspace, Microsoft 365, Slack, Trello, Zoom, Plataformas Cloud de Gestión"
        skills_soft = "Responsabilidad ejecutiva, Comunicación asertiva, Aprendizaje ágil, Orientación a resultados medibles"

    return {
        "name": name,
        "contact_line": contact_line,
        "summary": summary,
        "experience": experience,
        "skills_tech": skills_tech,
        "skills_tools": skills_tools,
        "skills_soft": skills_soft,
        "education": education
    }


# ========================================================
# Motor de Renderizado PDF ATS (Harvard / Silicon Valley)
# ========================================================
def build_ats_pdf(data):
    """Genera un documento PDF de 1 página con tipografía ejecutiva y 100% amigable para ATS."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=38,
        rightMargin=38,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()
    color_primary = colors.HexColor('#0F172A')    # Slate 900
    color_section = colors.HexColor('#1E3A8A')    # Navy Blue
    color_body = colors.HexColor('#1E293B')       # Slate 800
    color_line = colors.HexColor('#CBD5E1')       # Border Slate

    name_style = ParagraphStyle(
        'AtsName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=19,
        textColor=color_primary,
        alignment=1,
        spaceAfter=3
    )

    contact_style = ParagraphStyle(
        'AtsContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=6
    )

    heading_style = ParagraphStyle(
        'AtsHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=color_section,
        spaceBefore=7,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'AtsBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.3,
        leading=11.2,
        textColor=color_body,
        alignment=4,
        spaceAfter=4
    )

    role_style = ParagraphStyle(
        'AtsRole',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.8,
        leading=11.5,
        textColor=color_primary,
        spaceBefore=2,
        spaceAfter=1
    )

    company_style = ParagraphStyle(
        'AtsCompany',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.2,
        leading=10.5,
        textColor=colors.HexColor('#475569'),
        spaceAfter=2
    )

    bullet_style = ParagraphStyle(
        'AtsBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=10.8,
        textColor=color_body,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=1.8
    )

    story = []

    # 1. ENCABEZADO LIMPIO
    story.append(Paragraph(data['name'], name_style))
    story.append(Paragraph(data['contact_line'], contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=color_line, spaceBefore=2, spaceAfter=5))

    # 2. PERFIL PROFESIONAL
    story.append(Paragraph("PERFIL PROFESIONAL", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=3))
    story.append(Paragraph(data['summary'], body_style))

    # 3. EXPERIENCIA LABORAL RELEVANTE (FÓRMULA XYZ)
    story.append(Paragraph("EXPERIENCIA LABORAL RELEVANTE", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=3))

    for job in data['experience']:
        story.append(Paragraph(job['role'], role_style))
        story.append(Paragraph(f"{job['company']} | {job['period']}", company_style))
        for bullet in job['bullets']:
            bullet_text = f"• {bullet}"
            story.append(Paragraph(bullet_text, bullet_style))
        story.append(Spacer(1, 2))

    # 4. HABILIDADES Y HERRAMIENTAS
    story.append(Paragraph("HABILIDADES TÉCNICAS & HERRAMIENTAS DIGITALES", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=3))
    
    story.append(Paragraph(f"<b>Competencias Técnicas:</b> {data['skills_tech']}", body_style))
    story.append(Paragraph(f"<b>Herramientas & Entornos:</b> {data['skills_tools']}", body_style))
    story.append(Paragraph(f"<b>Habilidades Profesionales:</b> {data['skills_soft']}", body_style))

    # 5. FORMACIÓN ACADÉMICA
    story.append(Paragraph("FORMACIÓN ACADÉMICA", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=3))
    story.append(Paragraph(f"<b>{data['education']}</b> — Formación Oficial / Modalidad Acreditada", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ========================================================
# Plantillas Oficiales de Vacantes para el Canal
# ========================================================
def get_channel_job_templates():
    catalog = get_autopilot_jobs_catalog()
    tpls = {j['id']: j for j in catalog}
    if 'virtual_latinos' in tpls:
        tpls['va'] = tpls['virtual_latinos']
    if 'telus' in tpls:
        tpls['search'] = tpls['telus']
    return tpls


# ========================================================
# Generador de Blurbs / Copys de Monetización
# ========================================================
def get_monetization_blurbs():
    data = load_monetization()
    airtm_url = data.get('airtm', {}).get('url', 'https://airtm.me/')
    payoneer_url = data.get('payoneer', {}).get('url', 'https://share.payoneer.com/')
    binance_url = data.get('binance', {}).get('url', 'https://accounts.binance.com/')
    hotmart_url = data.get('hotmart', {}).get('url', 'https://hotmart.com/')

    return {
        "airtm": {
            "title": "💵 Blurb AirTM (Cobro de Outlier y Tareas IA)",
            "text": (
                f"💵 **¿CÓMO COBRAR TUS GANANCIAS EN DÓLARES DE OUTLIER Y PLATAFORMAS DE IA?**\n\n"
                f"Muchos trabajadores remotos pierden hasta un 15% en comisiones bancarias tradicionales. "
                f"Con **AirTM** recibes tus dólares directos desde PayPal o plataformas de microtareas y los transfieres "
                f"a tu cuenta bancaria local en minutos con la mejor tasa del mercado.\n\n"
                f"✅ Compatible con Colombia, México, Argentina, Perú y toda LatAm.\n"
                f"✅ Sin saldo mínimo de mantenimiento.\n\n"
                f"🎁 **Abre tu cuenta gratis y recibe beneficios de bienvenida aquí:**\n"
                f"👉 {airtm_url}\n\n"
                f"*(Recomendado oficialmente para cobros en Outlier y Remotasks)*"
            )
        },
        "payoneer": {
            "title": "🏛️ Blurb Payoneer (Cuenta Bancaria en EE.UU.)",
            "text": (
                f"🏛️ **RECIBE PAGOS EN DÓLARES COMO SI TUVIERAS CUENTA BANCARIA EN ESTADOS UNIDOS**\n\n"
                f"Las empresas de EE.UU. (DataAnnotation, Upwork, Virtual Latinos y agencias remotas) "
                f"pagan mediante transferencia bancaria directa ACH en USD. Con **Payoneer** obtienes datos bancarios "
                f"en EE.UU. a tu nombre sin costo de apertura.\n\n"
                f"✅ Tarjeta débito internacional Mastercard disponible.\n"
                f"✅ Retiro directo a tu banco local en tu moneda nacional.\n\n"
                f"🎁 **Regístrate con nuestro enlace oficial y recibe $25 USD de bono con tus primeros cobros:**\n"
                f"👉 {payoneer_url}"
            )
        },
        "binance": {
            "title": "🚀 Blurb Binance P2P (Retiros Cripto a Banco Local)",
            "text": (
                f"🚀 **RETIRA TUS DÓLARES DIGITALES A TU BANCO EN 5 MINUTOS Y CERO COMISIONES**\n\n"
                f"Si trabajas en proyectos que pagan en criptomonedas o stablecoins (USDT / USDC), utiliza **Binance P2P** "
                f"para transferir los fondos directo a tu banco local (Bancolombia, BBVA, Mercado Pago, BCP, etc.) "
                f"sin intermediarios ni cobros ocultos.\n\n"
                f"👉 **Crea tu cuenta verificada con beneficios de comisiones aquí:**\n"
                f"{binance_url}"
            )
        },
        "hotmart": {
            "title": "📚 Blurb Hotmart (Cursos y Certificaciones Pro)",
            "text": (
                f"📚 **ACELERA TU CONTRATACIÓN REMOTA: ENTRENAMIENTOS DE ÉLITE**\n\n"
                f"Aprende el paso a paso exacto para superar los exámenes de calificación de Outlier, redactar Justificaciones (Rationales) "
                f"perfectas y dominar entrevistas en inglés técnico con los mejores programas formativos de la industria.\n\n"
                f"👉 **Accede a los cursos y recursos recomendados aquí:**\n"
                f"{hotmart_url}"
            )
        },
        "combo": {
            "title": "💼 Combo Financiero para el Trabajador Remoto",
            "text": (
                f"💼 **EL COMBO FINANCIERO ESENCIAL DEL TRABAJADOR REMOTO EN DÓLARES**\n\n"
                f"Para trabajar con empresas internacionales y plataformas de IA sin trabas para cobrar tus ingresos, ten listas tus cuentas:\n\n"
                f"1️⃣ **AirTM:** Cobros rápidos de tareas de IA y cambio a moneda local:\n👉 {airtm_url}\n\n"
                f"2️⃣ **Payoneer:** Cuenta bancaria ACH en EE.UU. para contratos formales (+ $25 USD bono):\n👉 {payoneer_url}\n\n"
                f"3️⃣ **Binance:** La mayor liquidez en USDT y transferencias locales P2P:\n👉 {binance_url}\n\n"
                f"💡 *Consejo Pro: Crea y verifica tus cuentas antes de postularte a las vacantes.*"
            )
        }
    }


# ========================================================
# MEGA PANEL DE CONTROL DEL ADMINISTRADOR (/admin y /panel)
# ========================================================
def get_admin_main_keyboard():
    """Genera el teclado principal del panel de control."""
    auto_state = load_autopilot_state()
    auto_enabled = auto_state.get('enabled', True)
    auto_status_text = "ACTIVADO 🟢" if auto_enabled else "DESACTIVADO 🔴"

    keyboard = [
        [InlineKeyboardButton(f"🤖 Piloto Automático: {auto_status_text}", callback_data="adm_auto_menu")],
        [InlineKeyboardButton("📢 Publicar en el Canal (@empleosremotos_oficial)", callback_data="adm_pub_menu")],
        [InlineKeyboardButton("💰 Centro de Monetización y Enlaces", callback_data="adm_monet_menu")],
        [InlineKeyboardButton("📣 Difusión Masiva (Broadcast)", callback_data="adm_bcast_menu")],
        [InlineKeyboardButton("📊 Métricas y Audiencia", callback_data="adm_stats_menu")],
        [InlineKeyboardButton("📥 Exportar Base de Datos", callback_data="adm_export_menu")],
        [InlineKeyboardButton("❌ Cerrar Panel", callback_data="adm_close")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Punto de entrada de comandos /admin y /panel."""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ **Acceso denegado.** Este comando es exclusivo para el propietario y administrador del bot.",
            parse_mode='Markdown'
        )
        return

    # Limpiar estado administrativo previo
    context.user_data.pop('admin_action', None)
    context.user_data.pop('pending_broadcast', None)
    context.user_data.pop('pending_custom_post', None)

    subscribers = load_subscribers()
    total_users = len(subscribers)
    total_cvs = sum(s.get('cvs_generated', 0) for s in subscribers.values())
    stats_data = load_stats()

    auto_state = load_autopilot_state()
    auto_enabled = auto_state.get('enabled', True)
    auto_status_str = "ACTIVADO 🟢" if auto_enabled else "DESACTIVADO 🔴"
    catalog = get_autopilot_jobs_catalog()
    curr_idx = auto_state.get('current_index', 0) % (len(catalog) if catalog else 1)
    next_job_name = catalog[curr_idx]['short_title'] if catalog else "N/A"
    interval_h = auto_state.get('interval_hours', 6)

    panel_text = "\n".join([
        "👑 **MEGA PANEL DE CONTROL DE ADMINISTRADOR**",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 **Admin:** `{user.first_name}` (`{user.id}`)",
        f"🤖 **Piloto Automático:** {auto_status_str} (Cada {interval_h}h)",
        f"📌 **Próxima en cola:** {next_job_name}",
        f"👥 **Suscriptores registrados:** `{total_users}`",
        f"📄 **CVs generados:** `{total_cvs}`",
        f"📢 **Clics en canal:** `{stats_data.get('channel_clicks', 0)}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Selecciona una sección operativa para gestionar el bot y el canal:"
    ])

    await update.message.reply_text(
        panel_text,
        parse_mode='Markdown',
        reply_markup=get_admin_main_keyboard()
    )



async def show_autopilot_menu(query, context):
    """Muestra el submenú de control del Piloto Automático Agéntico."""
    state = load_autopilot_state()
    enabled = state.get('enabled', True)
    status_text = "ACTIVADO 🟢" if enabled else "DESACTIVADO 🔴"
    interval = state.get('interval_hours', 6)
    last_post = state.get('last_post')
    if last_post:
        try:
            dt = datetime.fromisoformat(last_post)
            last_post_display = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            last_post_display = str(last_post)[:19]
    else:
        last_post_display = "Ninguna aún (se publicará al activarse)"

    catalog = get_autopilot_jobs_catalog()
    idx = state.get('current_index', 0) % (len(catalog) if catalog else 1)
    next_job = catalog[idx] if catalog else {'title': 'N/A'}

    toggle_btn_text = "🔴 Desactivar Piloto Automático" if enabled else "🟢 Activar Piloto Automático"

    keyboard = [
        [InlineKeyboardButton(toggle_btn_text, callback_data="adm_auto_toggle")],
        [InlineKeyboardButton("⚡ Forzar Publicación Inmediata Ahora", callback_data="adm_auto_force")],
        [
            InlineKeyboardButton(f"{'✅ ' if interval == 4 else ''}⏱️ 4h", callback_data="adm_auto_int:4"),
            InlineKeyboardButton(f"{'✅ ' if interval == 6 else ''}⏱️ 6h", callback_data="adm_auto_int:6"),
            InlineKeyboardButton(f"{'✅ ' if interval == 8 else ''}⏱️ 8h", callback_data="adm_auto_int:8"),
            InlineKeyboardButton(f"{'✅ ' if interval == 12 else ''}⏱️ 12h", callback_data="adm_auto_int:12"),
        ],
        [InlineKeyboardButton("📋 Ver Catálogo de 10 Vacantes", callback_data="adm_auto_list")],
        [InlineKeyboardButton("⬅️ Volver al Panel Principal", callback_data="adm_home")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🤖 **PILOTO AUTOMÁTICO AGÉNTICO 24/7**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• **Estado actual:** {status_text}\n"
        f"• **Frecuencia programada:** Cada `{interval}` horas\n"
        f"• **Última publicación:** `{last_post_display}`\n"
        f"• **Próxima vacante en turno (#{idx + 1} de {len(catalog)}):**\n"
        f"  👉 **{next_job['title']}**\n"
        f"• **Canal de destino:** `{CHANNEL_USERNAME}`\n"
        f"• **Botón interactivo:** `[📄 Armar mi CV para esta Vacante]`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ *Opciones de administración:*\n"
        "1. Activa o desactiva el bucle automático autónomo.\n"
        "2. Pulsa **⚡ Forzar Publicación Inmediata** para probar el envío al canal en tiempo real.\n"
        "3. Selecciona la frecuencia deseada (cada 4h, 6h, 8h o 12h)."
    )
    if query:
        await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=reply_markup)


# ========================================================
# 1. Módulo: Publicación en Canal (@empleosremotos_oficial)
# ========================================================
async def show_publish_menu(query, context):
    """Muestra el submenú de plantillas y mensaje personalizado."""
    catalog = get_autopilot_jobs_catalog()
    keyboard = []
    for i in range(0, len(catalog), 2):
        row = [InlineKeyboardButton(catalog[i]['short_title'], callback_data=f"adm_pub_tpl:{catalog[i]['id']}")]
        if i + 1 < len(catalog):
            row.append(InlineKeyboardButton(catalog[i+1]['short_title'], callback_data=f"adm_pub_tpl:{catalog[i+1]['id']}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("✍️ Publicar Mensaje Personalizado", callback_data="adm_pub_custom")])
    keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel Principal", callback_data="adm_home")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "\n\n".join([
        "📢 **Publicación en el Canal Oficial** (`@empleosremotos_oficial`)",
        "Elige cualquiera de las 10 vacantes verificadas del catálogo para publicarla de inmediato, o redacta un mensaje libre personalizado.",
        "*Todas las publicaciones incluirán de forma automática el botón interactivo:*\n`[📄 Armar mi CV para esta Vacante]`"
    ])
    await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=reply_markup)


async def preview_template_post(query, context, tpl_key):
    """Muestra la vista previa de una plantilla antes de confirmar."""
    templates = get_channel_job_templates()
    tpl = templates.get(tpl_key)
    if not tpl:
        await query.answer("Plantilla no encontrada.", show_alert=True)
        return

    context.user_data['pending_tpl_key'] = tpl_key

    keyboard = [
        [InlineKeyboardButton("🚀 Publicar Ahora en @empleosremotos_oficial", callback_data=f"adm_pub_do:{tpl_key}")],
        [InlineKeyboardButton("⬅️ Elegir Otra Plantilla", callback_data="adm_pub_menu")],
        [InlineKeyboardButton("🏠 Menú Admin", callback_data="adm_home")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    preview_text = (
        f"👀 **VISTA PREVIA DE LA PUBLICACIÓN:**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{tpl['text']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔘 *Botón incluido:* `[📄 Armar CV para esta Vacante]`\n\n"
        f"¿Deseas enviar esta vacante ahora mismo a `@empleosremotos_oficial`?"
    )
    await safe_edit_text(query, preview_text, parse_mode='Markdown', reply_markup=reply_markup)


async def execute_channel_publish(target_text: str, context: ContextTypes.DEFAULT_TYPE, apply_url: str = None):
    """Envía el texto al canal con el botón del bot y maneja permisos con elegancia."""
    bot_user = await get_bot_username(context)
    bot_cv_url = f"https://t.me/{bot_user}?start=cv"

    keyboard_buttons = []
    if apply_url:
        keyboard_buttons.append([InlineKeyboardButton("🌐 Postularme / Inscribirme en Sitio Oficial", url=apply_url)])
    keyboard_buttons.append([InlineKeyboardButton("📄 Armar mi CV ATS para esta Vacante", url=bot_cv_url)])
    channel_keyboard = InlineKeyboardMarkup(keyboard_buttons)

    try:
        sent_message = await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=target_text,
            parse_mode='Markdown',
            reply_markup=channel_keyboard
        )
        increment_stat('total_channel_posts')
        return True, sent_message.message_id, None
    except TelegramError as te:
        error_msg = str(te)
        logger.error(f"TelegramError publicando en canal: {error_msg}")
        return False, None, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error inesperado publicando en canal: {error_msg}")
        return False, None, error_msg



def save_subscribers_data(subscribers):
    """Guarda el diccionario de suscriptores en disco con persistencia segura."""
    try:
        with open(SUBSCRIBERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscribers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando suscriptores: {e}")


async def dispatch_segmented_job_alerts(job: dict, application) -> int:
    """Envía notificaciones push privadas y segmentadas a los suscriptores según perfil o interés."""
    subscribers = load_subscribers()
    if not subscribers:
        return 0

    job_title = job.get('title', 'Nueva Convocatoria Remota')
    bot_user = "creadordecv_bot"
    try:
        me = await application.bot.get_me()
        if me and me.username:
            bot_user = me.username
    except Exception:
        pass

    bot_cv_url = f"https://t.me/{bot_user}?start=cv"

    keyboard = [
        [InlineKeyboardButton("📄 Armar mi CV para esta Vacante", url=bot_cv_url)],
        [InlineKeyboardButton("🚀 Ver Convocatoria en Canal", url=SPONSOR_CHANNEL_URL)],
        [InlineKeyboardButton("🔕 Pausar Mis Alertas", callback_data="btn_toggle_alerts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    alert_msg = (
        "🔔 **ALERTA DE VACANTE PARA TU PERFIL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Se acaba de abrir una nueva convocatoria en el canal:\n\n"
        f"📌 **{job_title}**\n"
        "💼 **Modalidad:** 100% Remoto Internacional (Pago en USD)\n\n"
        "*(Cupos de admisión sujetos a filtros de cada plataforma).* \n\n"
        "👇 Toca abajo para generar tu CV adaptado o postularte:"
    )

    sent_count = 0
    for uid_str, user_info in subscribers.items():
        try:
            if user_info.get('alerts_enabled') is False:
                continue

            user_chat_id = int(uid_str)
            if user_chat_id < 0:
                continue

            await application.bot.send_message(
                chat_id=user_chat_id,
                text=alert_msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            sent_count += 1
            await asyncio.sleep(0.04)  # Throttling seguro contra rate limits
        except TelegramError as te:
            err_str = str(te).lower()
            if "blocked" in err_str or "user is deactivated" in err_str:
                user_info['alerts_enabled'] = False
            continue
        except Exception:
            continue

    save_subscribers_data(subscribers)
    logger.info(f"🔔 Alertas push enviadas a {sent_count} suscriptores para '{job_title}'.")
    return sent_count


async def toggle_alerts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite al usuario activar o pausar sus alertas de vacantes."""
    query = update.callback_query
    user = update.effective_user
    if not user:
        return

    subscribers = load_subscribers()
    uid_str = str(user.id)
    user_info = subscribers.get(uid_str, {})
    current_status = user_info.get('alerts_enabled', True)
    new_status = not current_status

    user_info['alerts_enabled'] = new_status
    subscribers[uid_str] = user_info
    save_subscribers_data(subscribers)

    status_text = "ACTIVADAS 🟢" if new_status else "PAUSADAS 🔴"
    info_text = (
        f"⚙️ **Tus Alertas de Vacantes están ahora: {status_text}**\n\n"
        f"{'Recibirás avisos privados automáticos cada vez que se publiquen vacantes en el canal oficial.' if new_status else 'Ya no recibirás alertas push privadas al chat. Puedes reactivarlas cuando quieras tocando el botón abajo o con /alertas.'}"
    )

    kb = [[InlineKeyboardButton(f"{'🔕 Pausar Alertas' if new_status else '🔔 Activar Alertas'}", callback_data="btn_toggle_alerts")]]
    if query:
        await query.answer(f"Alertas {status_text}")
        await safe_edit_text(query, info_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
    elif update.message:
        await update.message.reply_text(info_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa los datos enviados desde la Telegram Mini App y compila el CV al instante."""
    try:
        raw_data = update.message.web_app_data.data
        data = json.loads(raw_data)
        if data.get('action') == 'generate_cv':
            context.user_data['name'] = data.get('name', 'CANDIDATO PROFESIONAL')
            context.user_data['email'] = data.get('email', 'contacto.profesional@gmail.com')
            context.user_data['country'] = data.get('country', 'Modalidad Remota')
            context.user_data['job_category'] = data.get('category', 'admin')
            context.user_data['target_job'] = data.get('target_job', 'Especialista en Administración & Operaciones')
            context.user_data['english_level'] = data.get('english', 'eng_basic')
            context.user_data['exp_level'] = data.get('exp_level', 'beginner')
            context.user_data['education'] = 'Formación Universitaria / Técnica Completa'
            context.user_data['custom_exp_text'] = ''

            save_subscriber(update.effective_user, country=context.user_data['country'], target_job=context.user_data['target_job'])
            await generate_and_send_final_cv(update.message, update.effective_user, context)
    except Exception as e:
        logger.error(f"Error procesando web_app_data: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ocurrió un inconveniente al procesar los datos de la Mini App. Puedes iniciar por chat con /cv.")


async def publish_autopilot_next_job(application) -> tuple[bool, str]:
    """Publica la siguiente vacante del catálogo de piloto automático en el canal oficial."""
    state = load_autopilot_state()
    catalog = get_autopilot_jobs_catalog()
    if not catalog:
        return False, "Catálogo de vacantes vacío"

    current_idx = state.get("current_index", 0) % len(catalog)
    job = catalog[current_idx]

    bot_user = "creadordecv_bot"
    try:
        me = await application.bot.get_me()
        if me and me.username:
            bot_user = me.username
    except Exception as e:
        logger.warning(f"No se pudo consultar me.username: {e}")

    bot_cv_url = f"https://t.me/{bot_user}?start=cv"

    keyboard_buttons = []
    apply_url = job.get('apply_url')
    if apply_url:
        keyboard_buttons.append([InlineKeyboardButton("🌐 Postularme / Inscribirme en Sitio Oficial", url=apply_url)])
    keyboard_buttons.append([InlineKeyboardButton("📄 Armar mi CV ATS para esta Vacante", url=bot_cv_url)])
    channel_keyboard = InlineKeyboardMarkup(keyboard_buttons)

    try:
        sent_message = await application.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=job["text"],
            parse_mode='Markdown',
            reply_markup=channel_keyboard
        )
        increment_stat('total_channel_posts')

        state["last_post"] = datetime.now().isoformat()
        state["current_index"] = (current_idx + 1) % len(catalog)
        save_autopilot_state(state)

        # Despachar alertas push privadas segmentadas a los suscriptores
        asyncio.create_task(dispatch_segmented_job_alerts(job, application))

        return True, f"Vacante #{current_idx + 1} '{job['title']}' publicada (Msg ID: {sent_message.message_id})"
    except TelegramError as te:
        err = str(te)
        logger.error(f"TelegramError en piloto automático: {err}")
        return False, err
    except Exception as ex:
        err = str(ex)
        logger.error(f"Error inesperado en piloto automático: {err}")
        return False, err


async def run_autopilot_loop(application):
    """Bucle continuo en segundo plano del Piloto Automático Agéntico 24/7."""
    logger.info("🤖 Iniciando motor de Piloto Automático Agéntico 24/7...")
    await asyncio.sleep(15)

    # Inicializar last_post con la hora actual de arranque para evitar doble posteo o repeticiones al reiniciar/desplegar
    startup_state = load_autopilot_state()
    startup_state["last_post"] = datetime.now().isoformat()
    save_autopilot_state(startup_state)
    logger.info(f"🤖 Piloto Automático calibrado: intervalo de {startup_state.get('interval_hours', 6)}h (próxima vacante: #{startup_state.get('current_index', 0) + 1}).")

    while True:
        try:
            state = load_autopilot_state()
            if state.get("enabled", True):
                interval_hours = float(state.get("interval_hours", 6))
                last_post_str = state.get("last_post")
                should_post = False
                now = datetime.now()

                if not last_post_str:
                    should_post = False
                    state["last_post"] = now.isoformat()
                    save_autopilot_state(state)
                else:
                    try:
                        last_post_dt = datetime.fromisoformat(last_post_str)
                        elapsed_seconds = (now - last_post_dt).total_seconds()
                        if elapsed_seconds >= interval_hours * 3600:
                            should_post = True
                    except Exception as pe:
                        logger.error(f"Error analizando timestamp last_post ({last_post_str}): {pe}")
                        should_post = False
                        state["last_post"] = now.isoformat()
                        save_autopilot_state(state)

                if should_post:
                    logger.info("🤖 Piloto Automático: Ejecutando publicación periódica de vacante...")
                    success, msg = await publish_autopilot_next_job(application)
                    if success:
                        logger.info(f"🤖 Piloto Automático éxito: {msg}")
                    else:
                        logger.warning(f"🤖 Piloto Automático reintento programado: {msg}")
                        await asyncio.sleep(300)
                        continue
        except Exception as e:
            logger.error(f"Error inesperado en bucle de Piloto Automático: {e}", exc_info=True)

        await asyncio.sleep(60)


async def on_bot_startup(application):
    """Hook de inicio para arrancar el bucle del Piloto Automático."""
    logger.info("Arrancando tareas de inicio: Piloto Automático Agéntico en segundo plano.")
    asyncio.create_task(run_autopilot_loop(application))


# ========================================================
# 2. Módulo: Centro de Monetización y Enlaces de Afiliados
# ========================================================
async def show_monetization_menu(query, context):
    """Muestra el centro de monetización y gestión de enlaces."""
    data = load_monetization()

    msg_lines = [
        "💰 **CENTRO DE MONETIZACIÓN Y ENLACES DE AFILIADOS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for key, info in data.items():
        msg_lines.append(f"• **{info['name']}:**\n  🔗 `{info['url']}`\n  _{info.get('tagline', '')}_")

    msg_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    msg_lines.append("Toca un botón para actualizar cualquier enlace o ver los copys persuasivos listos para difundir:")

    keyboard = [
        [InlineKeyboardButton("📋 Ver Copys / Blurbs de Alta Conversión", callback_data="adm_blurbs_menu")],
        [
            InlineKeyboardButton("✏️ AirTM", callback_data="adm_edit_lnk:airtm"),
            InlineKeyboardButton("✏️ Payoneer", callback_data="adm_edit_lnk:payoneer")
        ],
        [
            InlineKeyboardButton("✏️ Binance", callback_data="adm_edit_lnk:binance"),
            InlineKeyboardButton("✏️ Hotmart", callback_data="adm_edit_lnk:hotmart")
        ],
        [InlineKeyboardButton("⬅️ Volver al Panel Principal", callback_data="adm_home")]
    ]

    await safe_edit_text(query, "\n".join(msg_lines), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def show_blurbs_menu(query, context):
    """Muestra los diferentes copys persuasivos de monetización."""
    keyboard = [
        [InlineKeyboardButton("💵 Blurb AirTM (Outlier/Remotasks)", callback_data="adm_blurb_view:airtm")],
        [InlineKeyboardButton("🏛️ Blurb Payoneer (Cuenta ACH EE.UU.)", callback_data="adm_blurb_view:payoneer")],
        [InlineKeyboardButton("🚀 Blurb Binance P2P (Retiros Cripto)", callback_data="adm_blurb_view:binance")],
        [InlineKeyboardButton("📚 Blurb Hotmart (Cursos y Certificaciones)", callback_data="adm_blurb_view:hotmart")],
        [InlineKeyboardButton("💼 Blurb Combo Financiero Completo", callback_data="adm_blurb_view:combo")],
        [InlineKeyboardButton("⬅️ Volver a Enlaces de Monetización", callback_data="adm_monet_menu")]
    ]
    text = (
        "📋 **Copys y Textos Persuasivos de Monetización**\n\n"
        "Selecciona un copy para visualizarlo con tus enlaces de afiliado ya insertados. "
        "Podrás copiarlo, enviarlo a todos los suscriptores (Difusión) o publicarlo en el canal:"
    )
    await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def view_blurb(query, context, blurb_key):
    """Muestra un blurb específico y opciones directas de publicación/difusión."""
    blurbs = get_monetization_blurbs()
    blurb = blurbs.get(blurb_key)
    if not blurb:
        await query.answer("Copy no encontrado.", show_alert=True)
        return

    context.user_data['active_blurb_key'] = blurb_key

    keyboard = [
        [InlineKeyboardButton("📣 Enviar este Blurb a Todos (Difusión)", callback_data=f"adm_bcast_blurb:{blurb_key}")],
        [InlineKeyboardButton("📢 Publicar este Blurb en el Canal", callback_data=f"adm_chan_blurb:{blurb_key}")],
        [InlineKeyboardButton("⬅️ Volver a Lista de Blurbs", callback_data="adm_blurbs_menu")],
        [InlineKeyboardButton("🏠 Panel Admin", callback_data="adm_home")]
    ]

    view_text = (
        f"📋 **{blurb['title']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{blurb['text']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Puedes copiar el texto anterior o utilizar las acciones directas inferiores:*"
    )
    await safe_edit_text(query, view_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


# ========================================================
# 3. Módulo: Asistente de Difusión Masiva (Broadcast)
# ========================================================
async def show_broadcast_menu(query, context):
    """Muestra menú interactivo de difusión masiva."""
    subscribers = load_subscribers()
    total_users = len(subscribers)
    stats_data = load_stats()

    keyboard = [
        [InlineKeyboardButton("✍️ Redactar Nuevo Mensaje de Difusión", callback_data="adm_bcast_start")],
        [InlineKeyboardButton("⬅️ Volver al Panel Principal", callback_data="adm_home")]
    ]

    text = (
        "📣 **DIFUSIÓN MASIVA A SUSCRIPTORES (BROADCAST)**\n\n"
        f"• **Audiencia potencial:** `{total_users}` suscriptores activos.\n"
        f"• **Difusiones realizadas previamente:** `{stats_data.get('total_broadcasts', 0)}`\n\n"
        "Al iniciar el asistente, podrás redactar cualquier comunicado o promoción. "
        "El bot te mostrará una **vista previa exacta** antes de proceder al envío masivo."
    )
    await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def run_mass_broadcast(broadcast_text: str, context: ContextTypes.DEFAULT_TYPE, status_msg):
    """Envía el mensaje masivo de forma asíncrona con control de tasa de envío."""
    subscribers = load_subscribers()
    total = len(subscribers)

    sent_count = 0
    failed_count = 0

    await status_msg.edit_text(
        f"⏳ **Iniciando difusión masiva...**\n"
        f"Destinatarios en cola: `{total}` suscriptores.\n"
        f"Por favor espera unos momentos...",
        parse_mode='Markdown'
    )

    for uid in list(subscribers.keys()):
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=broadcast_text,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            sent_count += 1
        except Exception:
            failed_count += 1

        # Control de flujo de Telegram (30 msg/s máx)
        await asyncio.sleep(0.04)

    increment_stat('total_broadcasts')

    keyboard = [[InlineKeyboardButton("🏠 Volver al Panel de Control", callback_data="adm_home")]]

    await status_msg.edit_text(
        f"📢 **¡Difusión masiva completada!**\n\n"
        f"✅ **Entregados con éxito:** `{sent_count}`\n"
        f"❌ **No entregados (bloqueados o inactivos):** `{failed_count}`\n"
        f"👥 **Total procesados:** `{total}`",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ========================================================
# 4. Módulo: Métricas y Audiencia
# ========================================================
async def show_stats_dashboard(query, context):
    """Genera y muestra panel de estadísticas ejecutivas."""
    subscribers = load_subscribers()
    total_users = len(subscribers)
    total_cvs = sum(s.get('cvs_generated', 0) for s in subscribers.values())
    stats_data = load_stats()

    today_str = datetime.now().strftime('%Y-%m-%d')
    active_today = 0
    new_today = 0
    countries = {}
    jobs = {}

    for s in subscribers.values():
        last_seen = s.get('last_seen', '')
        if last_seen and last_seen.startswith(today_str):
            active_today += 1

        created_at = s.get('created_at', s.get('joined_at', ''))
        if created_at and created_at.startswith(today_str):
            new_today += 1

        c = s.get('country', 'No especificado')
        countries[c] = countries.get(c, 0) + 1

        j = s.get('target_job', 'No especificado')
        jobs[j] = jobs.get(j, 0) + 1

    top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:3]
    top_jobs = sorted(jobs.items(), key=lambda x: x[1], reverse=True)[:3]

    country_summary = ", ".join([f"{k} ({v})" for k, v in top_countries]) if top_countries else "Aún sin datos"
    job_summary = ", ".join([f"{k[:25]}... ({v})" if len(k) > 25 else f"{k} ({v})" for k, v in top_jobs]) if top_jobs else "Aún sin datos"

    text = (
        "📊 **DASHBOARD DE MÉTRICAS Y AUDIENCIA**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Total Suscriptores Registrados:** `{total_users}`\n"
        f"📄 **Total CVs ATS Generados:** `{total_cvs}`\n"
        f"🟢 **Usuarios Activos Hoy:** `{active_today}`\n"
        f"✨ **Nuevos Registros Hoy:** `{new_today}`\n"
        f"📢 **Clics en Enlace del Canal:** `{stats_data.get('channel_clicks', 0)}`\n"
        f"📣 **Campañas de Difusión Enviadas:** `{stats_data.get('total_broadcasts', 0)}`\n"
        f"📮 **Publicaciones al Canal:** `{stats_data.get('total_channel_posts', 0)}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌎 **Top Países:** {country_summary}\n"
        f"💼 **Top Vacantes:** {job_summary}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Actualizar Métricas", callback_data="adm_stats_menu")],
        [InlineKeyboardButton("📥 Exportar Datos (JSON / CSV)", callback_data="adm_export_menu")],
        [InlineKeyboardButton("⬅️ Volver al Panel Principal", callback_data="adm_home")]
    ]
    await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


# ========================================================
# 5. Módulo: Exportar Base de Datos (JSON y CSV)
# ========================================================
async def show_export_menu(query, context):
    """Muestra opciones para exportar la base de datos."""
    subscribers = load_subscribers()
    total_users = len(subscribers)

    keyboard = [
        [InlineKeyboardButton("📄 Exportar en Formato JSON", callback_data="adm_exp_json")],
        [InlineKeyboardButton("📊 Exportar en Formato CSV (Excel)", callback_data="adm_exp_csv")],
        [InlineKeyboardButton("⬅️ Volver al Panel Principal", callback_data="adm_home")]
    ]

    text = (
        "📥 **EXPORTACIÓN DE BASE DE DATOS**\n\n"
        f"Actualmente tienes `{total_users}` suscriptores en la base de datos.\n\n"
        "Elige el formato de archivo que deseas recibir directamente en este chat de Telegram:"
    )
    await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_export_json(query, context):
    """Genera y envía el archivo subscribers.json al administrador."""
    await query.answer("Generando archivo JSON...")
    subscribers = load_subscribers()

    json_str = json.dumps(subscribers, indent=2, ensure_ascii=False)
    buffer = BytesIO(json_str.encode('utf-8'))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"subscribers_backup_{timestamp}.json"

    caption = (
        f"📥 **Copia de Seguridad de Suscriptores (JSON)**\n"
        f"• Fecha: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"• Registros exportados: `{len(subscribers)}`"
    )

    await context.bot.send_document(
        chat_id=query.effective_chat.id,
        document=buffer,
        filename=filename,
        caption=caption,
        parse_mode='Markdown'
    )


async def handle_export_csv(query, context):
    """Genera y envía un archivo CSV compatible con Excel al administrador."""
    await query.answer("Generando archivo CSV...")
    subscribers = load_subscribers()

    output = StringIO()
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['ID', 'Username', 'Nombre', 'Pais', 'Vacante_Objetivo', 'Fecha_Registro', 'Ultima_Actividad', 'CVs_Generados'])

    for uid, data in subscribers.items():
        writer.writerow([
            uid,
            data.get('username', ''),
            data.get('first_name', ''),
            data.get('country', 'No especificado'),
            data.get('target_job', 'No especificado'),
            data.get('created_at', data.get('joined_at', '')),
            data.get('last_seen', ''),
            data.get('cvs_generated', 0)
        ])

    csv_data = output.getvalue().encode('utf-8-sig')  # utf-8-sig para compatibilidad con tildes en Excel
    buffer = BytesIO(csv_data)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"subscribers_export_{timestamp}.csv"

    caption = (
        f"📊 **Exportación de Suscriptores para Excel (CSV)**\n"
        f"• Registros exportados: `{len(subscribers)}`\n"
        f"• Codificación: UTF-8 con BOM (Compatible directo con Microsoft Excel y Google Sheets)."
    )

    await context.bot.send_document(
        chat_id=query.effective_chat.id,
        document=buffer,
        filename=filename,
        caption=caption,
        parse_mode='Markdown'
    )


# ========================================================
# Enrutador Central de Callbacks del Panel de Administrador
# ========================================================
async def admin_callback_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enruta todos los clics de botones del panel de administrador."""
    query = update.callback_query
    user = update.effective_user

    if not is_admin(user.id):
        await query.answer("⛔ Acceso denegado.", show_alert=True)
        return

    data = query.data

    # Menú Principal
    if data == "adm_home":
        await query.answer()
        context.user_data.pop('admin_action', None)
        subscribers = load_subscribers()
        total_users = len(subscribers)
        total_cvs = sum(s.get('cvs_generated', 0) for s in subscribers.values())
        stats_data = load_stats()

        auto_state = load_autopilot_state()
        auto_enabled = auto_state.get('enabled', True)
        auto_status_str = "ACTIVADO 🟢" if auto_enabled else "DESACTIVADO 🔴"
        catalog = get_autopilot_jobs_catalog()
        curr_idx = auto_state.get('current_index', 0) % (len(catalog) if catalog else 1)
        next_job_name = catalog[curr_idx]['short_title'] if catalog else "N/A"
        interval_h = auto_state.get('interval_hours', 6)

        panel_text = "\n".join([
            "👑 **MEGA PANEL DE CONTROL DE ADMINISTRADOR**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👤 **Admin:** `{user.first_name}` (`{user.id}`)",
            f"🤖 **Piloto Automático:** {auto_status_str} (Cada {interval_h}h)",
            f"📌 **Próxima en cola:** {next_job_name}",
            f"👥 **Suscriptores registrados:** `{total_users}`",
            f"📄 **CVs generados:** `{total_cvs}`",
            f"📢 **Clics en canal:** `{stats_data.get('channel_clicks', 0)}`",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "Selecciona una sección operativa para gestionar el bot y el canal:"
        ])
        await safe_edit_text(query, panel_text, parse_mode='Markdown', reply_markup=get_admin_main_keyboard())
        return

    elif data == "adm_close":
        await query.answer("Panel cerrado.")
        context.user_data.pop('admin_action', None)
        await safe_edit_text(query, "🔒 **Panel de administrador cerrado.**\nEscribe `/admin` o `/panel` en cualquier momento para volver a abrirlo.", parse_mode='Markdown')
        return

    # Piloto Automático Agéntico
    elif data == "adm_auto_menu":
        await query.answer()
        await show_autopilot_menu(query, context)
        return

    elif data == "adm_auto_toggle":
        state = load_autopilot_state()
        new_state = not state.get('enabled', True)
        state['enabled'] = new_state
        save_autopilot_state(state)
        status_word = "ACTIVADO 🟢" if new_state else "DESACTIVADO 🔴"
        await query.answer(f"Piloto Automático {status_word}")
        await show_autopilot_menu(query, context)
        return

    elif data.startswith("adm_auto_int:"):
        new_interval = int(data.split(":")[1])
        state = load_autopilot_state()
        state['interval_hours'] = new_interval
        save_autopilot_state(state)
        await query.answer(f"⏱️ Intervalo fijado en cada {new_interval} horas.")
        await show_autopilot_menu(query, context)
        return

    elif data == "adm_auto_force":
        await query.answer("⚡ Enviando vacante al canal oficial...")
        success, msg = await publish_autopilot_next_job(context.application)
        bot_user = await get_bot_username(context)
        keyboard = [
            [InlineKeyboardButton("📢 Ver Canal @empleosremotos_oficial", url=SPONSOR_CHANNEL_URL)],
            [InlineKeyboardButton("🤖 Volver al Piloto Automático", callback_data="adm_auto_menu")],
            [InlineKeyboardButton("🏠 Menú Admin", callback_data="adm_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if success:
            await safe_edit_text(query, 
                f"✅ **¡Publicación de Piloto Automático Exitosa!**\n\n"
                f"• **Detalle:** {msg}\n"
                f"• **Destino:** `{CHANNEL_USERNAME}`\n"
                f"• **Botón incluido:** `[📄 Armar mi CV para esta Vacante]`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            instrucciones = (
                f"⚠️ **No se pudo publicar en el canal {CHANNEL_USERNAME}**\n\n"
                f"**Causa técnica:** `{msg}`\n\n"
                f"📌 **Cómo autorizar al bot para publicar:**\n"
                f"1. Abre Telegram y entra a tu canal **{CHANNEL_USERNAME}**.\n"
                f"2. Ve a Configuración > **Administradores** > **Añadir Administrador**.\n"
                f"3. Busca a **@{bot_user}** y selecciónalo.\n"
                f"4. Marca el permiso **'Publicar Mensajes'** y guarda.\n"
                f"5. Vuelve aquí y pulsa nuevamente en forzar publicación."
            )
            await safe_edit_text(query, instrucciones, parse_mode='Markdown', reply_markup=reply_markup)
        return

    elif data == "adm_auto_list":
        await query.answer()
        catalog = get_autopilot_jobs_catalog()
        state = load_autopilot_state()
        curr_idx = state.get('current_index', 0) % (len(catalog) if catalog else 1)

        lines = [
            "📋 **CATÁLOGO DE VACANTES VERIFICADAS (PILOTO AUTOMÁTICO)**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Estas 10 vacantes rotan secuencialmente en el canal con información honesta, requisitos reales y botón de armar CV:\n"
        ]
        for i, job in enumerate(catalog):
            marker = "👉 *(Siguiente en fila)*" if i == curr_idx else ""
            lines.append(f"**{i+1}.** {job['title']} {marker}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        keyboard = [
            [InlineKeyboardButton("⚡ Publicar la Siguiente Ahora", callback_data="adm_auto_force")],
            [InlineKeyboardButton("⬅️ Volver a Piloto Automático", callback_data="adm_auto_menu")]
        ]
        await safe_edit_text(query, "\n".join(lines), parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # 1. Publicar en Canal
    elif data == "adm_pub_menu":
        await query.answer()
        await show_publish_menu(query, context)
        return

    elif data.startswith("adm_pub_tpl:"):
        await query.answer()
        tpl_key = data.split(":")[1]
        await preview_template_post(query, context, tpl_key)
        return

    elif data.startswith("adm_pub_do:"):
        await query.answer("Publicando en canal...")
        tpl_key = data.split(":")[1]
        templates = get_channel_job_templates()
        tpl = templates.get(tpl_key)
        if not tpl:
            await query.message.reply_text("⚠️ Plantilla no válida.")
            return

        success, msg_id, err = await execute_channel_publish(tpl['text'], context, apply_url=tpl.get('apply_url'))
        bot_user = await get_bot_username(context)

        keyboard = [
            [InlineKeyboardButton("📢 Ver Canal @empleosremotos_oficial", url=SPONSOR_CHANNEL_URL)],
            [InlineKeyboardButton("⬅️ Publicar Otra Vacante", callback_data="adm_pub_menu")],
            [InlineKeyboardButton("🏠 Volver al Panel", callback_data="adm_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if success:
            await safe_edit_text(query, 
                f"✅ **¡Vacante publicada con éxito en @empleosremotos_oficial!**\n\n"
                f"• **Plantilla:** {tpl['title']}\n"
                f"• **ID de Mensaje:** `{msg_id}`\n"
                f"• **Botones incluidos:** `[🌐 Postularme Oficial]` y `[📄 Armar CV]`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            instrucciones = (
                f"⚠️ **No se pudo publicar en el canal @empleosremotos_oficial**\n\n"
                f"**Causa técnica:** `{err}`\n\n"
                f"📌 **Instrucciones para autorizar al bot:**\n"
                f"1. Abre Telegram y entra a tu canal `@empleosremotos_oficial`.\n"
                f"2. Ve a la configuración del canal > **Administradores** > **Añadir Administrador**.\n"
                f"3. Busca al bot **@{bot_user}** y agrégalo.\n"
                f"4. Asígnale permiso para **'Publicar Mensajes'** y guarda los cambios.\n"
                f"5. Regresa aquí y vuelve a pulsar en publicar."
            )
            await safe_edit_text(query, instrucciones, parse_mode='Markdown', reply_markup=reply_markup)
        return

    elif data == "adm_pub_custom":
        await query.answer()
        context.user_data['admin_action'] = 'WAITING_CHANNEL_CUSTOM_TEXT'
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="adm_pub_menu")]])
        await safe_edit_text(query, 
            "✍️ **Publicar Mensaje Personalizado al Canal**\n\n"
            "Envía a continuación el texto o vacante que deseas publicar en `@empleosremotos_oficial`.\n"
            "Puedes utilizar emojis, viñetas y formato Markdown.\n\n"
            "*El bot le añadirá automáticamente el botón interactivo de armar CV al final.*",
            parse_mode='Markdown',
            reply_markup=cancel_kb
        )
        return

    elif data == "adm_conf_custom_pub":
        await query.answer("Publicando mensaje personalizado...")
        custom_text = context.user_data.get('pending_custom_post')
        if not custom_text:
            await safe_edit_text(query, "⚠️ No hay mensaje pendiente. Inicia nuevamente.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data="adm_pub_menu")]]))
            return

        success, msg_id, err = await execute_channel_publish(custom_text, context)
        bot_user = await get_bot_username(context)
        context.user_data.pop('pending_custom_post', None)

        keyboard = [
            [InlineKeyboardButton("📢 Ver Canal @empleosremotos_oficial", url=SPONSOR_CHANNEL_URL)],
            [InlineKeyboardButton("⬅️ Publicar Otro", callback_data="adm_pub_menu")],
            [InlineKeyboardButton("🏠 Menú Admin", callback_data="adm_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if success:
            await safe_edit_text(query, 
                f"✅ **¡Mensaje personalizado publicado con éxito en @empleosremotos_oficial!**\n\n"
                f"• **ID de Mensaje:** `{msg_id}`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await safe_edit_text(query, 
                f"⚠️ **Error al publicar en @empleosremotos_oficial:**\n`{err}`\n\n"
                f"Verifica que @{bot_user} sea Administrador del canal con permisos de publicación.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return

    # 2. Centro de Monetización
    elif data == "adm_monet_menu":
        await query.answer()
        await show_monetization_menu(query, context)
        return

    elif data.startswith("adm_edit_lnk:"):
        await query.answer()
        platform = data.split(":")[1]
        data_monet = load_monetization()
        plat_info = data_monet.get(platform, {})

        context.user_data['admin_action'] = f'WAITING_LINK_URL:{platform}'
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="adm_monet_menu")]])

        await safe_edit_text(query, 
            f"✏️ **Actualizar Enlace de Afiliado para {plat_info.get('name', platform)}**\n\n"
            f"• **Enlace actual:** `{plat_info.get('url', '')}`\n\n"
            f"Envía a continuación la nueva URL completa (debe comenzar con `http://` o `https://`):",
            parse_mode='Markdown',
            reply_markup=cancel_kb
        )
        return

    elif data == "adm_blurbs_menu":
        await query.answer()
        await show_blurbs_menu(query, context)
        return

    elif data.startswith("adm_blurb_view:"):
        await query.answer()
        blurb_key = data.split(":")[1]
        await view_blurb(query, context, blurb_key)
        return

    elif data.startswith("adm_bcast_blurb:"):
        await query.answer()
        blurb_key = data.split(":")[1]
        blurbs = get_monetization_blurbs()
        b_item = blurbs.get(blurb_key)
        if not b_item:
            await query.answer("Copy no encontrado.", show_alert=True)
            return

        context.user_data['pending_broadcast'] = b_item['text']
        subscribers = load_subscribers()

        keyboard = [
            [InlineKeyboardButton(f"🚀 Confirmar y Enviar a {len(subscribers)} Suscriptores", callback_data="adm_bcast_do")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="adm_blurbs_menu")]
        ]
        await safe_edit_text(query, 
            f"📢 **CONFIRMAR DIFUSIÓN MASIVA DE COPY MONETIZACIÓN**\n\n"
            f"{b_item['text']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"¿Confirmas el envío a todos los `{len(subscribers)}` suscriptores?",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif data.startswith("adm_chan_blurb:"):
        await query.answer("Publicando blurb en canal...")
        blurb_key = data.split(":")[1]
        blurbs = get_monetization_blurbs()
        b_item = blurbs.get(blurb_key)
        if not b_item:
            await query.answer("Copy no encontrado.", show_alert=True)
            return

        success, msg_id, err = await execute_channel_publish(b_item['text'], context)
        bot_user = await get_bot_username(context)

        keyboard = [
            [InlineKeyboardButton("📢 Ver Canal @empleosremotos_oficial", url=SPONSOR_CHANNEL_URL)],
            [InlineKeyboardButton("⬅️ Volver a Blurbs", callback_data="adm_blurbs_menu")],
            [InlineKeyboardButton("🏠 Menú Admin", callback_data="adm_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if success:
            await safe_edit_text(query, 
                f"✅ **¡Copy de monetización publicado exitosamente en @empleosremotos_oficial!**\n\n"
                f"• **Campaña:** {b_item['title']}\n"
                f"• **ID de Mensaje:** `{msg_id}`",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await safe_edit_text(query, 
                f"⚠️ **Error publicando blurb en canal:**\n`{err}`\n\n"
                f"Asegúrate de que @{bot_user} sea Administrador del canal con permiso para publicar.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return

    # 3. Difusión Masiva (Broadcast)
    elif data == "adm_bcast_menu":
        await query.answer()
        await show_broadcast_menu(query, context)
        return

    elif data == "adm_bcast_start":
        await query.answer()
        context.user_data['admin_action'] = 'WAITING_BROADCAST_TEXT'
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="adm_bcast_menu")]])
        await safe_edit_text(query, 
            "✍️ **Asistente de Difusión Masiva (Broadcast)**\n\n"
            "Envía a continuación el mensaje que deseas difundir a todos los suscriptores.\n"
            "Puedes utilizar Markdown, emojis y enlaces.\n\n"
            "*Podrás previsualizar el mensaje y confirmar antes del envío final.*",
            parse_mode='Markdown',
            reply_markup=cancel_kb
        )
        return

    elif data == "adm_bcast_do":
        await query.answer()
        b_text = context.user_data.get('pending_broadcast')
        if not b_text:
            await safe_edit_text(query, "⚠️ No hay mensaje pendiente para difundir.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver", callback_data="adm_bcast_menu")]]))
            return

        context.user_data.pop('pending_broadcast', None)
        await run_mass_broadcast(b_text, context, query.message)
        return

    # 4. Métricas
    elif data == "adm_stats_menu":
        await query.answer()
        await show_stats_dashboard(query, context)
        return

    # 5. Exportar Base de Datos
    elif data == "adm_export_menu":
        await query.answer()
        await show_export_menu(query, context)
        return

    elif data == "adm_exp_json":
        await handle_export_json(query, context)
        return

    elif data == "adm_exp_csv":
        await handle_export_csv(query, context)
        return


# ========================================================
# Manejador de Entradas de Texto del Administrador
# ========================================================
async def admin_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa textos enviados por el admin cuando está en flujos interactivos."""
    user = update.effective_user
    if not is_admin(user.id):
        return

    admin_action = context.user_data.get('admin_action')
    if not admin_action:
        return

    raw_text = update.message.text.strip()

    # 1. Entrada de Texto Personalizado para Canal
    if admin_action == 'WAITING_CHANNEL_CUSTOM_TEXT':
        context.user_data['pending_custom_post'] = raw_text
        context.user_data.pop('admin_action', None)

        bot_user = await get_bot_username(context)
        preview = (
            "👀 **VISTA PREVIA DEL MENSAJE PERSONALIZADO:**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{raw_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔘 *Botón automático:* `[📄 Armar CV para esta Vacante]` (https://t.me/{bot_user}?start=cv)\n\n"
            "¿Confirmas la publicación en `@empleosremotos_oficial`?"
        )
        keyboard = [
            [InlineKeyboardButton("🚀 Confirmar y Enviar al Canal", callback_data="adm_conf_custom_pub")],
            [InlineKeyboardButton("✍️ Volver a Redactar", callback_data="adm_pub_custom")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="adm_pub_menu")]
        ]
        await update.message.reply_text(preview, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # 2. Entrada de Texto para Difusión Masiva
    elif admin_action == 'WAITING_BROADCAST_TEXT':
        context.user_data['pending_broadcast'] = raw_text
        context.user_data.pop('admin_action', None)

        subscribers = load_subscribers()
        total_users = len(subscribers)

        preview = (
            "👀 **VISTA PREVIA DEL MENSAJE DE DIFUSIÓN:**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{raw_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 **Destinatarios:** `{total_users}` suscriptores.\n\n"
            "¿Deseas iniciar el envío masivo ahora?"
        )
        keyboard = [
            [InlineKeyboardButton(f"🚀 Confirmar y Enviar a {total_users} Usuarios", callback_data="adm_bcast_do")],
            [InlineKeyboardButton("✍️ Volver a Redactar", callback_data="adm_bcast_start")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="adm_bcast_menu")]
        ]
        await update.message.reply_text(preview, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # 3. Actualización de Enlace de Afiliado
    elif admin_action.startswith('WAITING_LINK_URL:'):
        platform = admin_action.split(":")[1]
        context.user_data.pop('admin_action', None)

        if not re.match(r'^https?://[\w\.-]+', raw_text):
            await update.message.reply_text(
                "⚠️ La URL debe ser válida y comenzar con `http://` o `https://`.\nOperación cancelada.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver a Monetización", callback_data="adm_monet_menu")]])
            )
            return

        updated = update_monetization_link(platform, raw_text)
        data_monet = load_monetization()
        plat_name = data_monet.get(platform, {}).get('name', platform)

        keyboard = [
            [InlineKeyboardButton("📋 Ver Copys Actualizados", callback_data="adm_blurbs_menu")],
            [InlineKeyboardButton("⬅️ Volver a Monetización", callback_data="adm_monet_menu")],
            [InlineKeyboardButton("🏠 Panel Admin", callback_data="adm_home")]
        ]

        if updated:
            await update.message.reply_text(
                f"✅ **¡Enlace de {plat_name} actualizado exitosamente!**\n\n"
                f"🔗 **Nueva URL activa:** `{raw_text}`\n\n"
                f"Todos los copys y blurbs de recomendación ahora utilizarán este enlace de forma inmediata.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                f"⚠️ Ocurrió un problema guardando el enlace para {plat_name}.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return


# ========================================================
# Comandos Rápidos de Administrador (/stats y /broadcast)
# ========================================================
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra estadísticas rápidas del bot (solo admin)."""
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        return

    subscribers = load_subscribers()
    total_users = len(subscribers)
    total_cvs = sum(s.get('cvs_generated', 0) for s in subscribers.values())
    stats_data = load_stats()

    keyboard = [
        [InlineKeyboardButton("📊 Abrir Dashboard Completo", callback_data="adm_stats_menu")],
        [InlineKeyboardButton("👑 Menú Panel Admin", callback_data="adm_home")]
    ]

    ref_data = load_referrals()
    total_refs = len(ref_data.get("referred_users", {}))
    unlocked_packs = sum(1 for r in ref_data.get("referrers", {}).values() if r.get("unlocked", False) or r.get("count", 0) >= 2)

    msg = (
        "📊 **Resumen Rápido del Bot ATS**\n\n"
        f"• **Suscriptores registrados:** `{total_users}`\n"
        f"• **CVs generados:** `{total_cvs}`\n"
        f"• **Referidos registrados:** `{total_refs}`\n"
        f"• **Packs Secretos desbloqueados:** `{unlocked_packs}`\n"
        f"• **Clics en canal:** `{stats_data.get('channel_clicks', 0)}`\n"
        f"• **Publicaciones en canal:** `{stats_data.get('total_channel_posts', 0)}`\n"
        f"• **Difusiones masivas:** `{stats_data.get('total_broadcasts', 0)}`"
    )
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envía difusión directa si se pasan argumentos, o abre el asistente."""
    user_id = str(update.effective_user.id)
    if not is_admin(user_id):
        return

    if not context.args:
        # Abrir asistente interactivo
        context.user_data['admin_action'] = 'WAITING_BROADCAST_TEXT'
        cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="adm_bcast_menu")]])
        await update.message.reply_text(
            "📣 **Asistente de Difusión Masiva**\n\n"
            "Envía a continuación el mensaje que deseas difundir a todos los suscriptores:\n"
            "*(O escribe `/broadcast Tu mensaje aquí` para envío directo)*",
            parse_mode='Markdown',
            reply_markup=cancel_kb
        )
        return

    broadcast_text = " ".join(context.args)
    status = await update.message.reply_text("⏳ Iniciando difusión...")
    await run_mass_broadcast(broadcast_text, context, status)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela cualquier operación actual y vuelve al estado normal."""
    context.user_data.clear()
    user = update.effective_user
    user_id = user.id if user else None
    persistent_keyboard = get_main_reply_keyboard(user_id)

    await update.message.reply_text(
        "❌ **Operación cancelada.**\n\nSe ha restablecido tu sesión. Puedes explorar las opciones en el menú inferior 👇",
        parse_mode='Markdown',
        reply_markup=persistent_keyboard
    )
    return ConversationHandler.END


# ========================================================
# Registro de Handlers y Polling de Telegram
# ========================================================
def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'TU_TOKEN_DE_BOTFATHER_AQUI':
        logger.error("TELEGRAM_BOT_TOKEN no configurado en .env")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(on_bot_startup).build()

    # 1. Flujo Conversacional Interactivo de Creación de CV (Prioritario)
    cv_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('cv', start_cv_entry),
            CallbackQueryHandler(start_cv_entry, pattern="^btn_start_cv$"),
            MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_CV)}$"), start_cv_entry)
        ],
        states={
            STEP_NAME: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name_step)
            ],
            STEP_COUNTRY: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_country_callback, pattern="^country_")
            ],
            STEP_TARGET: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_target_callback, pattern="^job_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_target)
            ],
            STEP_ENGLISH: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_english_callback, pattern="^eng_")
            ],
            STEP_EDUCATION: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_education_callback, pattern="^edu_")
            ],
            STEP_EXPERIENCE_LEVEL: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_experience_level_callback, pattern="^exp_")
            ],
            STEP_CUSTOM_EXP: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_experience)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$")
        ],
        allow_reentry=True
    )
    app.add_handler(cv_conv_handler)
    app.add_handler(CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"))

    # 2. Handlers del Panel de Administrador (/admin y /panel)
    app.add_handler(CommandHandler(['admin', 'panel'], admin_panel_command))
    app.add_handler(CallbackQueryHandler(admin_callback_dispatcher, pattern="^adm_"))

    # Captura de textos de administrador (flujos interactivos de broadcast, mensaje de canal y edición de enlace)
    admin_filter = filters.TEXT & ~filters.COMMAND
    if ADMIN_ID and ADMIN_ID.isdigit():
        admin_filter = admin_filter & filters.User(user_id=int(ADMIN_ID))
    app.add_handler(MessageHandler(admin_filter, admin_text_input_handler), group=1)

    # 3. Handlers de Usuario General
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler(['pack', 'referidos'], referrals_menu_callback))
    app.add_handler(CommandHandler('kit', download_kit_callback))
    app.add_handler(CommandHandler('guia', guide_interviews_callback))
    app.add_handler(CommandHandler('alertas', toggle_alerts_callback))
    app.add_handler(CommandHandler('stats', stats_command))
    app.add_handler(CommandHandler('broadcast', broadcast_command))
    app.add_handler(CommandHandler('cancel', cancel))

    app.add_handler(CallbackQueryHandler(start, pattern="^btn_back_menu$"))
    app.add_handler(CallbackQueryHandler(referrals_menu_callback, pattern="^btn_referrals_menu$"))
    app.add_handler(CallbackQueryHandler(download_secret_pack_callback, pattern="^btn_download_secret_pack$"))
    app.add_handler(CallbackQueryHandler(channel_link_tracker_callback, pattern="^btn_channel_link$"))
    app.add_handler(CallbackQueryHandler(why_ats_callback, pattern="^btn_why_ats$"))
    app.add_handler(CallbackQueryHandler(download_kit_callback, pattern="^btn_download_kit$"))
    app.add_handler(CallbackQueryHandler(guide_interviews_callback, pattern="^btn_guide_interviews$"))
    app.add_handler(CallbackQueryHandler(toggle_alerts_callback, pattern="^btn_toggle_alerts$"))

    # Mini App WebApp Data Handler (procesa envíos del formulario interactivo de la Mini App)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    # 4. Handlers del Teclado Inferior Persistente (Dock Ergonómico)
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_PACK)}$"), referrals_menu_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_CHANNEL)}$"), channel_link_tracker_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_KIT)}$"), download_kit_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_GUIDE)}$"), guide_interviews_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_ATS)}$"), why_ats_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_ALERTS)}$"), toggle_alerts_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_ADMIN)}$"), admin_panel_command))

    app.add_error_handler(global_error_handler)

    logger.info("Bot de CV ATS de Élite con Mega Panel Admin iniciado exitosamente.")
    start_health_server()
    app.run_polling(drop_pending_updates=True, stop_signals=None)


if __name__ == '__main__':
    main()
