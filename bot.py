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
    KeyboardButton,
    WebAppInfo
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from autopilot_catalog import (
    AUTOPILOT_FILE,
    load_autopilot_state,
    save_autopilot_state,
    get_autopilot_jobs_catalog
)

from vacancy_booster import (
    VACANCY_BOOSTERS,
    get_vacancy_booster,
    analyze_job_offer
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://telegram-cv-bot-oqr6.onrender.com/app')
MINI_APP_HTML_PATH = os.path.join(BASE_DIR, 'mini_app.html')

SUBSCRIBERS_FILE = os.path.join(BASE_DIR, 'subscribers.json')
STATS_FILE = os.path.join(BASE_DIR, 'stats.json')
MONETIZATION_FILE = os.path.join(BASE_DIR, 'monetization.json')
REFERRALS_FILE = os.path.join(BASE_DIR, 'referrals.json')

# Kit Maestro PDF Path
KIT_MAESTRO_PDF_PATH = os.path.join(BASE_DIR, 'Kit_Maestro_Empleo_Remoto_2026.pdf')
if not os.path.exists(KIT_MAESTRO_PDF_PATH):
    desktop_candidate = os.path.join(os.path.expanduser('~'), 'Desktop', 'Kit_Maestro_Empleo_Remoto_2026.pdf')
    if os.path.exists(desktop_candidate):
        KIT_MAESTRO_PDF_PATH = desktop_candidate

PACK_SECRETO_PDF_PATH = os.path.join(os.path.dirname(__file__), 'Pack_Secreto_Admision_Remota_2026.pdf')
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
BTN_BOTTOM_BOOST = "🎯 Hacks de Vacante (Boost)"
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
        [KeyboardButton(BTN_BOTTOM_BOOST), KeyboardButton(BTN_BOTTOM_PACK)],
        [KeyboardButton(BTN_BOTTOM_CHANNEL), KeyboardButton(BTN_BOTTOM_KIT)],
        [KeyboardButton(BTN_BOTTOM_GUIDE), KeyboardButton(BTN_BOTTOM_ATS)],
        [KeyboardButton(BTN_BOTTOM_ALERTS)]
    ]
    if user_id and is_admin(user_id):
        buttons.append([KeyboardButton(BTN_BOTTOM_ADMIN)])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, is_persistent=True)


# ========================================================
# Servidor HTTP de Monitoreo / Keep-Alive y Mini App (Cloud 24/7)
# ========================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Servir Telegram Mini App en /app o /miniapp
            if self.path.startswith('/app') or self.path.startswith('/miniapp'):
                if os.path.exists(MINI_APP_HTML_PATH):
                    with open(MINI_APP_HTML_PATH, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(content)
                    return
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b"mini_app.html not found on server")
                    return

            # Healthcheck padrão para Render
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'{"status":"ok","service":"telegram-cv-bot","autopilot":"running"}')
        except Exception as e:
            logger.error(f"Error en servidor HTTP: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass

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

    # Soporte para deep-linking: /start cv, /start boost o /start ref_USERID
    if context.args:
        arg = context.args[0].lower()
        if arg.startswith('ref'):
            await process_referral(user.id, arg, context)
        elif arg.startswith('cv'):
            msg = update.message or (update.callback_query.message if update.callback_query else None)
            if msg:
                return await start_cv_step_1(msg, context)
        elif arg.startswith('boost') or arg.startswith('hack'):
            return await boost_menu_callback(update, context)

    first_name = user.first_name or "colega"

    welcome_text = (
        f"🏛️ **SISTEMA DE EMPLEABILIDAD & CV ATS DE ÉLITE**\n"
        f"───────────────────────────────────\n"
        f"Hola, **{first_name}**. Bienvenido a la plataforma de optimización laboral y contratación.\n\n"
        f"▸ **El 85% de los CVs son descartados** por filtros ATS antes de que los lea una persona.\n"
        f"▸ Este bot compila tu CV bajo **estándares Harvard** (1 columna, fórmulas XYZ cuantitativas y palabras clave indexables) "
        f"o en formato **Hoja de Vida Formal** en cajas para comercios y empresas tradicionales.\n"
        f"▸ 🎯 **Optimizador según Vacante:** Usa **/boost** o el botón '🎯 Hacks de Vacante' para obtener las palabras clave exactas y logros probados según el trabajo al que aspiras.\n\n"
        f"👇 **Toca una opción del menú inferior para comenzar:**"
    )

    persistent_keyboard = get_main_reply_keyboard(user.id)

    inline_welcome = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Adaptar CV a mi Vacante (Hack de Contratación / Palabras Clave)", callback_data="btn_boost_menu")],
        [InlineKeyboardButton("📄 Crear mi CV ATS Directo", callback_data="btn_start_cv"), InlineKeyboardButton("🌐 Abrir Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])

    if update.callback_query:
        await safe_edit_text(update.callback_query, welcome_text, parse_mode='Markdown', reply_markup=inline_welcome)
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


# ========================================================
# Asistente Inteligente de Hacks de Contratación & Booster según Vacante
# ========================================================

async def boost_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú inteligente de Hacks de Contratación & Optimizador según Vacante."""
    query = update.callback_query
    if query:
        await query.answer("Cargando Optimizador de Vacantes...")

    context.user_data['awaiting_job_offer'] = False

    text = (
        "🎯 **OPTIMIZADOR SEGÚN VACANTE • HACKS DE CONTRATACIÓN ATS**\n"
        "───────────────────────────────────\n"
        "¿Sabías que el **85% de los currículums son descartados en 6 segundos** porque no contienen las "
        "palabras clave técnicas exactas que busca el software ATS o el seleccionador?\n\n"
        "Este asistente es tu **'trampa legítima de contratación'**:\n"
        "▸ Inyecta **palabras clave ATS obligatorias** para superar los filtros.\n"
        "▸ Fórmulas cuantitativas Harvard XYZ (*'Logré X medido por Y ejecutando Z'*).\n"
        "▸ Adaptado a empleos tradicionales (Comercio, Bodega, Operarios) y remotos en USD (IA, Asistente).\n\n"
        "👇 **Selecciona tu área laboral o pega una oferta de empleo para adaptarlo:**"
    )

    keyboard = [
        [
            InlineKeyboardButton("🛒 Ventas & Caja", callback_data="boost_role_ventas"),
            InlineKeyboardButton("📁 Aux. Administrativo", callback_data="boost_role_admin")
        ],
        [
            InlineKeyboardButton("📦 Bodega & Logística", callback_data="boost_role_bodega"),
            InlineKeyboardButton("🎧 Atención al Cliente", callback_data="boost_role_servicio")
        ],
        [
            InlineKeyboardButton("🛡️ Guarda de Seguridad", callback_data="boost_role_seguridad"),
            InlineKeyboardButton("🚗 Conductor & Reparto", callback_data="boost_role_transporte")
        ],
        [
            InlineKeyboardButton("⚙️ Operario de Planta", callback_data="boost_role_operario"),
            InlineKeyboardButton("🍽️ Cocina & Mesero", callback_data="boost_role_hosteleria")
        ],
        [
            InlineKeyboardButton("🌱 Primer Empleo (Sin exp.)", callback_data="boost_role_primer_empleo"),
            InlineKeyboardButton("🤖 Evaluador IA (USD)", callback_data="boost_role_outlier_ai")
        ],
        [
            InlineKeyboardButton("💼 Asistente Virtual USD", callback_data="boost_role_virtual_assistant"),
            InlineKeyboardButton("🔍 Evaluador de Datos USD", callback_data="boost_role_data_evaluator")
        ],
        [
            InlineKeyboardButton("🎧 Soporte Remoto (Zendesk)", callback_data="boost_role_customer_support_remote"),
            InlineKeyboardButton("🛡️ Moderador de Contenido (USD)", callback_data="boost_role_content_moderator")
        ],
        [
            InlineKeyboardButton("📋 Pegar Oferta de Empleo / Vacante", callback_data="boost_custom_prompt")
        ],
        [
            InlineKeyboardButton("🌐 Abrir Optimizador en Mini App", web_app=WebAppInfo(url=MINI_APP_URL))
        ],
        [
            InlineKeyboardButton("🏠 Volver al Menú Principal", callback_data="btn_back_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await safe_edit_text(query, text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await safe_reply_text(update.message, text, parse_mode='Markdown', reply_markup=reply_markup)


async def boost_role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el Cheat-Sheet completo y Hacks de Contratación para el rol seleccionado."""
    query = update.callback_query
    if query:
        await query.answer()

    role_id = query.data.replace("boost_role_", "")
    booster = get_vacancy_booster(role_id)
    if not booster:
        await boost_menu_callback(update, context)
        return

    context.user_data['booster_data'] = booster
    context.user_data['target_job'] = booster['title']
    context.user_data['job_category'] = booster['id']
    context.user_data['cv_type'] = booster.get('mode', 'formal_boxed')

    keywords_sample = ", ".join(booster['keywords'][:7])
    bullets_formatted = "\n".join([f"• {b}" for b in booster['bullets']])

    detail_text = (
        f"🎯 **HACK DE CONTRATACIÓN: {booster['title'].upper()}**\n"
        f"`[Compatibilidad ATS: {booster.get('ats_match_score', 98)}% Verificada]`\n"
        f"───────────────────────────────────\n"
        f"🏷️ **PALABRAS CLAVE ATS INDISPENSABLES:**\n"
        f"`{keywords_sample}`\n\n"
        f"⚡ **PERFIL PROFESIONAL RECOMENDADO (Summary):**\n"
        f"\"{booster['summary']}\"\n\n"
        f"🏆 **LOGROS CUANTITATIVOS (Fórmula Harvard XYZ):**\n"
        f"{bullets_formatted}\n\n"
        f"🛠️ **HABILIDADES TÉCNICAS & HERRAMIENTAS:**\n"
        f"▸ *Técnicas:* {booster['skills_tech']}\n"
        f"▸ *Herramientas:* {booster['skills_tools']}\n\n"
        f"{booster['recruiter_hack']}\n\n"
        f"👇 **¿Deseas aplicar este perfil optimizado a tu CV con 1 clic?**"
    )

    keyboard = [
        [InlineKeyboardButton("⚡ Generar mi CV con este Hack", callback_data=f"boost_apply_{booster['id']}")],
        [InlineKeyboardButton("🌐 Usar en Mini App (Autollenado)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("🔍 Ver otro cargo", callback_data="btn_boost_menu")],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="btn_back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_text(query, detail_text, parse_mode='Markdown', reply_markup=reply_markup)


async def boost_prompt_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Solicita al usuario que pegue el texto o cargo de la vacante deseada."""
    query = update.callback_query
    if query:
        await query.answer()

    context.user_data['awaiting_job_offer'] = True

    prompt_text = (
        "📋 **PEGA LA OFERTA DE EMPLEO O EL CARGO AL QUE ASPIRAS**\n"
        "───────────────────────────────────\n"
        "Envía en un mensaje de texto la descripción de la vacante, los requisitos o el título del empleo "
        "(ejemplo: copiado de Computrabajo, Indeed, LinkedIn, El Empleo o WhatsApp).\n\n"
        "🤖 **Nuestro optimizador analizará el texto al instante y extraerá:**\n"
        "▸ Palabras clave indexables que exige esa vacante específica.\n"
        "▸ Resumen profesional a medida.\n"
        "▸ Fórmulas cuantitativas Harvard XYZ para asegurar llamadas a entrevista.\n"
        "▸ El hack de contratación para destacar sobre otros postulantes.\n\n"
        "👇 *Pega o escribe el texto aquí abajo:*"
    )

    keyboard = [
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_boost_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await safe_edit_text(query, prompt_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await safe_reply_text(update.message, prompt_text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_pasted_job_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa el texto de la vacante pegada y muestra el análisis optimizado."""
    context.user_data['awaiting_job_offer'] = False
    raw_text = update.message.text.strip()
    if not raw_text:
        await update.message.reply_text("⚠️ No se recibió texto. Pulsa /boost para reintentar.")
        return

    status_msg = await update.message.reply_text(
        "🔍 **ANALIZANDO VACANTE CON MOTOR HEURÍSTICO ATS...**\n"
        "▸ Extrayendo requerimientos técnicos y verbos de acción...\n"
        "▸ Cruzando con base de datos de palabras clave indexables...",
        parse_mode='Markdown'
    )

    booster = analyze_job_offer(raw_text)
    context.user_data['booster_data'] = booster
    context.user_data['target_job'] = booster['title']
    context.user_data['job_category'] = booster['id']
    context.user_data['cv_type'] = booster.get('mode', 'formal_boxed')

    keywords_sample = ", ".join(booster['keywords'][:8])
    bullets_formatted = "\n".join([f"• {b}" for b in booster['bullets']])

    detail_text = (
        f"🎯 **OPTIMIZACIÓN PARA TU VACANTE: {booster['title'].upper()}**\n"
        f"`[Score de Compatibilidad ATS: {booster.get('ats_match_score', 96)}%]`\n"
        f"───────────────────────────────────\n"
        f"🏷️ **PALABRAS CLAVE DETECTADAS PARA ESTA VACANTE:**\n"
        f"`{keywords_sample}`\n\n"
        f"⚡ **PERFIL PROFESIONAL RECOMENDADO:**\n"
        f"\"{booster['summary']}\"\n\n"
        f"🏆 **LOGROS CON FÓRMULA HARVARD XYZ:**\n"
        f"{bullets_formatted}\n\n"
        f"🛠️ **HABILIDADES TÉCNICAS REQUERIDAS:**\n"
        f"▸ {booster['skills_tech']}\n\n"
        f"{booster['recruiter_hack']}\n\n"
        f"👇 **Toca para generar tu CV optimizado con estos datos:**"
    )

    keyboard = [
        [InlineKeyboardButton("⚡ Generar mi CV con esta Vacante", callback_data=f"boost_apply_{booster['id']}")],
        [InlineKeyboardButton("🌐 Abrir en Mini App", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("📋 Pegar otra vacante", callback_data="boost_custom_prompt")],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="btn_back_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await status_msg.delete()
    except Exception:
        pass

    await safe_reply_text(update.message, detail_text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección interactiva de modalidad (Formal vs Remoto ATS) en el Paso 1."""
    query = update.callback_query
    if query:
        await query.answer()
        mode = query.data.replace("mode_", "")
        context.user_data['cv_type'] = "remote_ats" if mode == "remote" else "formal_boxed"
        mode_label = "🚀 CV Remoto en Dólares (Harvard ATS)" if mode == "remote" else "📄 Hoja de Vida Formal Clásica"
        
        if context.user_data.get('name'):
            return await receive_name_step(update, context)

        await query.message.reply_text(
            f"✅ Modalidad seleccionada: **{mode_label}**\n\n"
            "✍️ Ahora escribe en un mensaje tu **Nombre Completo y Celular o Correo** para continuar:\n"
            "*(Ej: Carlos Pérez, 3001234567)*",
            parse_mode='Markdown'
        )
    return STEP_NAME


async def boost_apply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aplica los datos optimizados del booster y procede a compilar el CV o avanzar en el flujo."""
    query = update.callback_query
    if query:
        await query.answer("Aplicando Hacks de Contratación...")

    booster_id = query.data.replace("boost_apply_", "")
    booster = context.user_data.get('booster_data')
    if not booster or booster.get('id') != booster_id:
        booster = get_vacancy_booster(booster_id)
        if booster:
            context.user_data['booster_data'] = booster

    if booster:
        context.user_data['target_job'] = booster['title']
        context.user_data['job_category'] = booster['id']
        context.user_data['cv_type'] = booster.get('mode', 'formal_boxed')

    user = update.effective_user
    msg = query.message if query else update.message

    # Si el usuario ya tiene su perfil completo registrado en user_data
    if context.user_data.get('name') and (context.user_data.get('city') or context.user_data.get('country')) and context.user_data.get('education'):
        await generate_and_send_final_cv(msg, user, context)
        return ConversationHandler.END

    # Si ya tiene nombre y país pero faltaba el resto (p. ej. vino desde STEP_TARGET)
    if context.user_data.get('name') and (context.user_data.get('city') or context.user_data.get('country')):
        await safe_reply_text(
            msg,
            f"🎯 **PERFIL OPTIMIZADO FIJADO: {booster['title'] if booster else 'Perfil Adaptado'}**\n"
            "───────────────────────────────────\n"
            "✅ Palabras clave ATS cargadas al 100%.\n"
            "✅ Fórmulas cuantitativas Harvard XYZ listas.\n\n"
            "Avanzando a la confirmación de idiomas...",
            parse_mode='Markdown'
        )
        return await ask_english_step(msg, context)

    # Si aún no tiene datos personales, iniciamos el flujo guiado rápido de CV con el cargo ya seleccionado
    await safe_reply_text(
        msg,
        f"🎯 **PERFIL OPTIMIZADO: {booster['title'] if booster else 'Perfil Adaptado'}**\n"
        "───────────────────────────────────\n"
        "✅ Palabras clave ATS cargadas al 100%.\n"
        "✅ Fórmulas cuantitativas Harvard XYZ listas.\n\n"
        "Solo necesitamos tus datos de contacto para estampar tu CV oficial listo para enviar 👇",
        parse_mode='Markdown'
    )
    return await start_cv_step_1(msg, context)


async def user_text_input_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto de usuarios fuera de conversaciones activas."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Si está esperando el texto de una oferta de empleo para optimizarla
    if context.user_data.get('awaiting_job_offer'):
        await handle_pasted_job_offer(update, context)
        return

    # Si presionó el botón de Boost en el dock inferior
    if text == BTN_BOTTOM_BOOST:
        await boost_menu_callback(update, context)
        return

    # Detección inteligente de ofertas de empleo pegadas directamente en el chat
    lower = text.lower()
    job_indicators = ["buscamos", "requerimos", "oferta", "vacante", "experiencia", "salario", "perfil", "funciones", "requisitos", "contratacion"]
    if len(text) > 50 and any(k in lower for k in job_indicators):
        await handle_pasted_job_offer(update, context)
        return

    # Fallback informativo para guiar al usuario
    keyboard = [
        [InlineKeyboardButton("🎯 Adaptar CV a mi Vacante (Hack de Contratación / Palabras Clave)", callback_data="btn_boost_menu")],
        [InlineKeyboardButton("📄 Crear mi CV ATS Directo", callback_data="btn_start_cv"), InlineKeyboardButton("🌐 Abrir Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    await update.message.reply_text(
        "👋 ¡Hola! Soy tu asistente de Empleabilidad y CV ATS de Élite.\n\n"
        "▸ Pulsa **/boost** o el botón inferior para optimizar tu CV con palabras clave indexables según la vacante a la que aspiras.\n"
        "▸ Pulsa **/cv** para crear tu Hoja de Vida formal o CV Remoto en USD paso a paso.\n"
        "▸ O pega directamente aquí la oferta de empleo para analizarla al instante.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



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
    dock_buttons = [BTN_BOTTOM_CV, BTN_BOTTOM_BOOST, BTN_BOTTOM_PACK, BTN_BOTTOM_CHANNEL, BTN_BOTTOM_KIT, BTN_BOTTOM_GUIDE, BTN_BOTTOM_ATS, BTN_BOTTOM_ALERTS, BTN_BOTTOM_ADMIN]
    if raw_text not in dock_buttons:
        return False, 0

    context.user_data.clear()
    if raw_text == BTN_BOTTOM_CV:
        res = await start_cv_step_1(update.message, context)
        return True, res
    elif raw_text == BTN_BOTTOM_BOOST:
        await boost_menu_callback(update, context)
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
    elif raw_text == BTN_BOTTOM_ALERTS:
        await toggle_alerts_callback(update, context)
    elif raw_text == BTN_BOTTOM_ADMIN:
        await admin_panel_command(update, context)

    return True, ConversationHandler.END


async def start_cv_step_1(message, context) -> int:
    """Paso 1: Selección de modalidad y datos de contacto."""
    cancel_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Diseñar en Mini App (Visual e In-App)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("📄 Hoja de Vida Formal (Normal)", callback_data="mode_formal"), InlineKeyboardButton("🚀 CV Remoto USD (Outlier)", callback_data="mode_remote")],
        [InlineKeyboardButton("❌ Cancelar y Volver al Menú", callback_data="btn_cancel_cv")]
    ])
    prompt = (
        "📋 **CREACIÓN DE CURRÍCULUM • SELECCIONA TU MODALIDAD**\n"
        "`[██░░░░░░░░] 16% completado`\n"
        "───────────────────────────────────\n"
        "¿Qué tipo de currículum necesitas?\n\n"
        "1️⃣ **📄 Hoja de Vida Formal:** Para empresas locales y empleos tradicionales (Ventas, Administración, Bodega, Operarios, Primaria y Secundaria con años).\n\n"
        "2️⃣ **🚀 CV Remoto en Dólares:** Formato Harvard ATS optimizado para vacantes en USD (Outlier AI, Asistente Virtual, Remoto Global).\n\n"
        "✍️ Escribe en un mensaje tu **Nombre Completo y Celular o Correo** para continuar:\n"
        "*(Ej: Carlos Pérez, 3001234567)*"
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

    if context.user_data.get('booster_data'):
        booster = context.user_data['booster_data']
        await query.message.reply_text(
            f"📍 País confirmado: **{country_val}**\n"
            f"🎯 Perfil Optimizado fijado: **{booster['title']}**\n\n"
            "Avanzando a la confirmación de idiomas...",
            parse_mode='Markdown'
        )
        return await ask_english_step(query.message, context)

    keyboard = [
        [InlineKeyboardButton("🛒 Ventas & Comercio", callback_data="job_ventas"), InlineKeyboardButton("📁 Auxiliar Administrativo", callback_data="job_admin")],
        [InlineKeyboardButton("📦 Almacén & Bodega", callback_data="job_bodega"), InlineKeyboardButton("🎧 Atención al Cliente", callback_data="job_servicio")],
        [InlineKeyboardButton("⚙️ Operario de Planta", callback_data="job_operario"), InlineKeyboardButton("🛡️ Vigilancia & Mant.", callback_data="job_seguridad")],
        [InlineKeyboardButton("🍽️ Hostelería & Cocina", callback_data="job_hosteleria"), InlineKeyboardButton("🚗 Conductor & Reparto", callback_data="job_transporte")],
        [InlineKeyboardButton("🌱 Primer Empleo (Sin exp.)", callback_data="job_primer_empleo"), InlineKeyboardButton("✍️ Escribir otro cargo", callback_data="job_custom")],
        [InlineKeyboardButton("🎯 Hacks de Vacante / Pegar Oferta (Boost)", callback_data="boost_custom_prompt")],
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
        "ventas": "Asesor Comercial, Ventas & Cajero",
        "admin": "Auxiliar Administrativo & Recepción",
        "bodega": "Auxiliar de Almacén, Bodega & Logística",
        "servicio": "Agente de Servicio al Cliente & Call Center",
        "operario": "Operario de Producción & Planta Industrial",
        "seguridad": "Guarda de Seguridad & Control de Accesos",
        "hosteleria": "Auxiliar de Cocina, Mesero & Hostelería",
        "transporte": "Conductor, Repartidor & Mensajería",
        "primer_empleo": "Candidato Primer Empleo (Sin Experiencia Previa)",
        "sales": "Asesor Comercial & Ventas",
        "support": "Servicio al Cliente & Soporte",
        "ai": "Evaluador de Modelos de IA"
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
    booster = get_vacancy_booster(job_code)
    if booster:
        context.user_data['booster_data'] = booster
    save_subscriber(update.effective_user, target_job=target_title)

    return await ask_english_step(query.message, context)


async def receive_custom_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe cargo escrito a mano o texto de vacante y extrae sus palabras clave."""
    interrupted, next_state = await check_dock_interrupt(update, context)
    if interrupted:
        return next_state

    raw_text = update.message.text.strip()

    # Si estaba esperando pegar la oferta o si el usuario pegó una vacante completa (> 50 caracteres)
    lower = raw_text.lower()
    job_indicators = ["buscamos", "requerimos", "oferta", "vacante", "experiencia", "salario", "perfil", "funciones", "requisitos"]
    if context.user_data.get('awaiting_job_offer') or (len(raw_text) > 50 and any(k in lower for k in job_indicators)):
        await handle_pasted_job_offer(update, context)
        return STEP_TARGET

    booster = analyze_job_offer(raw_text)
    clean_target = booster.get('custom_title') or booster.get('title') or raw_text
    context.user_data['target_job'] = clean_target
    context.user_data['job_category'] = booster.get('id', 'custom')
    context.user_data['booster_data'] = booster
    save_subscriber(update.effective_user, target_job=clean_target)
    return await ask_english_step(update.message, context)


async def ask_english_step(message, context) -> int:
    """Muestra botones de idiomas con opción de Solo Español (100% opcional)."""
    keyboard = [
        [InlineKeyboardButton("✅ Solo Español (Nativo)", callback_data="eng_none")],
        [InlineKeyboardButton("🟡 Inglés Básico / Técnico", callback_data="eng_basic")],
        [InlineKeyboardButton("🔵 Inglés Intermedio Conversacional", callback_data="eng_intermediate")],
        [InlineKeyboardButton("⭐ Bilingüe Fluido (C1-C2)", callback_data="eng_advanced")],
        [InlineKeyboardButton("❌ Cancelar y Volver", callback_data="btn_cancel_cv")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"🎯 Cargo seleccionado: **{context.user_data['target_job']}**\n\n"
        "📋 **PASO 4 DE 6 • IDIOMAS (100% OPCIONAL)**\n"
        "`[████████░░] 66% completado`\n"
        "───────────────────────────────────\n"
        "Para empleos normales solo se requiere Español. Si no manejas otro idioma, toca **'Solo Español'**:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return STEP_ENGLISH


async def handle_english_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda nivel de idioma y pregunta por educación."""
    query = update.callback_query
    await query.answer()

    if query.data == "eng_none":
        context.user_data['english_level'] = "Español Nativo"
        context.user_data['language_text'] = "Español (Nativo)"
    else:
        eng_map = {
            "eng_basic": "Inglés Básico / Técnico",
            "eng_intermediate": "Inglés Intermedio Conversacional (B2)",
            "eng_advanced": "Inglés Fluido / Avanzado (C1-C2)"
        }
        context.user_data['english_level'] = eng_map.get(query.data, "Español Nativo")
        context.user_data['language_text'] = eng_map.get(query.data, "Español Nativo")

    keyboard = [
        [InlineKeyboardButton("🏫 Secundaria / Bachiller Completo & Primaria", callback_data="edu_highschool")],
        [InlineKeyboardButton("🎓 Técnico / Tecnológico (SENA o Instituto)", callback_data="edu_technician")],
        [InlineKeyboardButton("📚 Universitario (En curso o graduado)", callback_data="edu_university")],
        [InlineKeyboardButton("📝 Primaria Completa", callback_data="edu_primaria")],
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
        "edu_highschool": {
            "secundaria": {"colegio": "Colegio de Educación Secundaria", "ano": "Bachiller Académico Graduado", "estado": "Completo"},
            "primaria": {"colegio": "Escuela Básica Primaria", "ano": "Años Cursados Completos", "estado": "Completa"}
        },
        "edu_technician": {
            "secundaria": {"colegio": "Colegio de Educación Secundaria", "ano": "Bachiller Graduado", "estado": "Completo"},
            "primaria": {"colegio": "Escuela Básica Primaria", "ano": "Completa", "estado": "Completa"},
            "extra": "Formación Técnica / Tecnológica (SENA o Instituto Acreditado)"
        },
        "edu_university": {
            "secundaria": {"colegio": "Colegio de Educación Secundaria", "ano": "Bachiller Graduado", "estado": "Completo"},
            "primaria": {"colegio": "Escuela Básica Primaria", "ano": "Completa", "estado": "Completa"},
            "extra": "Estudios Superiores Universitarios"
        },
        "edu_primaria": {
            "secundaria": {"colegio": "Colegio de Educación Secundaria", "ano": "En Curso / Por Culminar", "estado": "En Curso"},
            "primaria": {"colegio": "Escuela Básica Primaria", "ano": "Primaria Completa", "estado": "Completa"}
        }
    }
    context.user_data['education'] = edu_map.get(query.data, "Formación Académica Completa")

    keyboard = [
        [InlineKeyboardButton("🌱 Primer Empleo (Sin experiencia laboral previa)", callback_data="exp_beginner")],
        [InlineKeyboardButton("💼 1 a 2 años de experiencia laboral", callback_data="exp_mid")],
        [InlineKeyboardButton("🏆 Más de 3 años de trayectoria laboral", callback_data="exp_senior")],
        [InlineKeyboardButton("✍️ Escribir mi empresa y funciones", callback_data="exp_custom")],
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
        cv_mode = context.user_data.get('cv_type', 'formal_boxed')
        if cv_mode == 'remote_ats':
            pdf_bytes = build_ats_pdf(cv_payload)
        else:
            pdf_bytes = build_formal_boxed_pdf(cv_payload)

        candidate_filename = cv_payload['name'].replace(" ", "_")
        filename = f"CV_{candidate_filename}_ATS_2026.pdf"

        target_title = context.user_data.get('target_job', 'Trabajo Remoto')

        if cv_mode == 'remote_ats':
            caption = (
                "🚀 **CV REMOTO EN DÓLARES (ATS) GENERADO CON ÉXITO**\n"
                "───────────────────────────────────\n"
                f"👤 **Candidato:** {cv_payload['name']}\n"
                f"💼 **Target Role:** {target_title}\n"
                "📐 **Formato:** Harvard ATS Estándar Internacional (1 Columna)\n"
                "🎓 **Educación & Certificaciones:** Enfoque Global en USD\n"
                "🚀 **Fórmulas XYZ:** Métricas cuantitativas y palabras clave indexadas\n\n"
                "📥 *Tu archivo PDF listo para enviar a plataformas internacionales está adjunto arriba.*"
            )
        else:
            caption = (
                "📄 **HOJA DE VIDA FORMAL GENERADA CON ÉXITO**\n"
                "───────────────────────────────────\n"
                f"👤 **Candidato:** {cv_payload['name']}\n"
                f"💼 **Perfil / Oficio:** {target_title}\n"
                "📐 **Formato:** Clásico Formal Ejecutivo en Cajas (1 Página)\n"
                "🎓 **Formación:** Secundaria y Primaria detalladas con años\n"
                "🏢 **Experiencia:** Redacción formal orientada al cumplimiento\n\n"
                "📥 *Tu archivo PDF listo para imprimir o enviar por WhatsApp/Correo está adjunto arriba.*"
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
# ========================================================
# Generador de Contenido para Hoja de Vida / CV Formal
# ========================================================
def generate_elite_cv_data(user_data):
    """Genera datos de currículum formal para todo tipo de empleos con redacción sobria y profesional."""
    name = user_data.get('name', 'CANDIDATO PROFESIONAL').upper()
    email = user_data.get('email', '')
    phone = user_data.get('phone', '')
    city = user_data.get('city') or user_data.get('country', 'Modalidad Presencial / Remota')
    target = user_data.get('target_job', 'Asesor Comercial & Ventas')
    category = user_data.get('job_category', 'ventas')
    has_exp = user_data.get('has_experience', True)
    custom_exp_data = user_data.get('experience_data')
    custom_text = user_data.get('custom_exp_text', '')
    raw_edu = user_data.get('education')
    language = user_data.get('language', '')
    language_text = user_data.get('language_text') or user_data.get('english_level', 'Español Nativo')

    # Línea de contacto formal
    contact_parts = []
    if city: contact_parts.append(city)
    if phone: contact_parts.append(f"Tel/WhatsApp: {phone}")
    if email and "@" in email: contact_parts.append(email)
    contact_parts.append("Disponibilidad Inmediata")
    contact_line = " • ".join(contact_parts)

    # Idiomas opcional
    is_native_only = (
        language == 'native_only' or 
        'solo' in language_text.lower() or 
        language_text.strip().lower() == 'español nativo' or 
        not language_text
    )
    languages_line = "" if is_native_only else f"Español (Nativo) • {language_text}"

    # Booster Inteligente de Vacantes & Hacks de Contratación
    booster = user_data.get('booster_data') or get_vacancy_booster(category) or analyze_job_offer(target)

    # Formación Académica estructurada (Secundaria + Primaria)
    if isinstance(raw_edu, dict):
        education_dict = raw_edu
    else:
        # Fallback predeterminado formal
        education_dict = {
            "secundaria": {"colegio": "Colegio de Educación Secundaria", "ano": "Bachiller Académico Graduado", "estado": "Completo"},
            "primaria": {"colegio": "Escuela de Educación Primaria", "ano": "Años Cursados Completos", "estado": "Completa"}
        }

    # Experiencia Laboral personalizada si el usuario escribió sus datos
    user_experience = None
    if custom_exp_data and isinstance(custom_exp_data, dict) and custom_exp_data.get('empresa'):
        emp = custom_exp_data.get('empresa', 'Empresa Comercial')
        car = custom_exp_data.get('cargo', target)
        per = custom_exp_data.get('periodo', '2 años')
        fun = custom_exp_data.get('funciones', '')
        bullets = []
        if fun and len(fun.strip()) > 8:
            bullets.append(f"Responsable de {fun.strip().rstrip('.')}.")
            if booster and booster.get('bullets'):
                bullets.extend(booster['bullets'][:2])
            else:
                bullets.append("Atención respetuosa y cumplimiento de los procedimientos operativos y directrices de la empresa.")
                bullets.append("Puntualidad estricta y colaboración continua con el equipo de trabajo en las metas diarias.")
        elif booster and booster.get('bullets'):
            bullets = booster['bullets'][:3]
        else:
            bullets = [
                "Atención respetuosa y cumplimiento de los procedimientos operativos y directrices de la empresa.",
                "Puntualidad estricta y colaboración continua con el equipo de trabajo en las metas diarias.",
                "Manejo adecuado de recursos, herramientas asignadas y orden en el puesto de trabajo."
            ]
        user_experience = [{
            "role": car,
            "company": f"{emp} | Modalidad Formal" if "formal" not in emp.lower() and "remote" not in emp.lower() else emp,
            "period": per,
            "bullets": bullets[:3]
        }]
    elif custom_text and len(custom_text.strip()) > 5:
        bullets = [f"Desempeño directo en: {custom_text.strip().rstrip()}."]
        if booster and booster.get('bullets'):
            bullets.extend(booster['bullets'][:2])
        else:
            bullets.append("Cumplimiento sistemático de las tareas asignadas y reporte periódico de novedades a supervisión.")
            bullets.append("Excelente disposición para el trabajo en equipo, puntualidad y honestidad en las labores cotidianas.")
        user_experience = [{
            "role": target,
            "company": "Experiencia Laboral Previa Comprobable",
            "period": "Trayectoria Reciente",
            "bullets": bullets[:3]
        }]

    # Si es modalidad PRIMER EMPLEO (Sin experiencia laboral previa)
    if category == "primer_empleo" or has_exp is False or user_data.get('exp_level') == 'beginner':
        summary = (
            f"Bachiller con sólida formación académica, principios éticos de honestidad, puntualidad y disciplina, con alta "
            f"motivación para iniciar su vida laboral y aportar con entusiasmo en {target}. Caracterizado por rápida capacidad de aprendizaje, "
            f"excelentes relaciones interpersonales, acatamiento respetuoso de instrucciones y total disponibilidad horaria inmediata."
        )
        experience = [
            {
                "role": "Participante en Proyectos Académicos, Apoyo Formativo & Comunitario",
                "company": "Etapa Formativa y Escolar Reciente",
                "period": "Periodo de Formación",
                "bullets": [
                    "Demostró puntualidad estricta, disciplina y cumplimiento oportuno en la entrega de tareas y proyectos escolares.",
                    "Participación activa en actividades grupales y trabajo en equipo, demostrando compañerismo y respeto.",
                    "Facilidad para aprender rápidamente nuevos métodos de trabajo, herramientas básicas y normas de la empresa.",
                    "Disponibilidad horaria total e inmediata y máximo compromiso para desempeñarse con excelencia."
                ]
            }
        ]
        skills_tech = "Facilidad de aprendizaje, Capacidad de concentración, Respeto y seguimiento de normas operativas"
        skills_tools = "Manejo básico de herramientas informáticas (Word, Excel básico), Teléfono móvil, Mensajería digital"
        skills_soft = "Puntualidad rigurosa, Honradez comprobada, Responsabilidad, Dinamismo, Excelente actitud de servicio"

    # 1. VENTAS & COMERCIO / CAJERO
    elif category in ["ventas", "sales"] or "venta" in target.lower() or "cajero" in target.lower() or "comercio" in target.lower():
        summary = (
            f"Asesor Comercial y de Ventas con experiencia en atención presencial al cliente, cobro y manejo de caja, surtido de mercancía "
            f"y cumplimiento de objetivos comerciales. Destacado por excelente actitud de servicio, cordialidad, honestidad en el manejo "
            f"de valores y capacidad para asesorar oportunamente a los clientes generando confianza y fidelización."
        )
        experience = user_experience or [
            {
                "role": "Asesor Comercial & Cajero de Mostrador",
                "company": "Establecimiento Comercial & Distribución de Productos",
                "period": "2021 - 2024",
                "bullets": [
                    "Atención y asesoría personalizada a más de 65 clientes diarios en punto de venta, garantizando un trato cordial y respetuoso.",
                    "Cobro de mercancía en efectivo, tarjetas y pagos digitales mediante terminales POS, con arqueos y cierres de caja cuadran al 100%.",
                    "Recepción, etiquetado, exhibición y control de inventarios de mercancía en estantería manteniendo el orden y disponibilidad.",
                    "Cumplimiento sistemático de las metas de venta asignadas por la administración del negocio."
                ]
            }
        ]
        skills_tech = "Atención al cliente y ventas, Facturación y arqueo de caja (POS), Control de existencias e inventarios, Surtido y exhibición"
        skills_tools = "Datafonos/POS, Sistemas de facturación básica, Calculadora comercial, Manejo de efectivo y comprobantes"
        skills_soft = "Puntualidad estricta, Honestidad comprobada, Amabilidad en el trato, Trabajo bajo metas, Facilidad de comunicación"

    # 2. AUXILIAR ADMINISTRATIVO & RECEPCIÓN
    elif category == "admin" or "admin" in target.lower() or "recep" in target.lower() or "asistente" in target.lower():
        summary = (
            f"Auxiliar Administrativo y de Oficina con experiencia en atención presencial y telefónica, gestión documental, radicación de "
            f"correspondencia, digitación y archivo organizado físico y digital. Comprometido con el orden, la puntualidad, la confidencialidad "
            f"de la información institucional y la agilidad en la gestión de trámites cotidianos."
        )
        experience = user_experience or [
            {
                "role": "Auxiliar Administrativo & Atención en Recepción",
                "company": "Empresa de Servicios y Gestión Administrativa",
                "period": "2021 - 2024",
                "bullets": [
                    "Recepción, radicación y distribución oportuna de facturas, correspondencia y solicitudes a las áreas encargadas.",
                    "Atención cordial de llamadas en conmutador y recepción presencial de visitantes, proveedores y usuarios.",
                    "Digitación de planillas, elaboración de oficios formales y archivo sistemático de expedientes físicos y electrónicos.",
                    "Control de inventario de papelería, suministros y apoyo logístico en reuniones de oficina."
                ]
            }
        ]
        skills_tech = "Gestión documental y archivo, Digitación ágil, Radicación y control de correspondencia, Redacción de actas y cartas"
        skills_tools = "Microsoft Office (Excel, Word básico), Correo electrónico, Fotocopiadoras, Escáneres, Conmutador telefónico"
        skills_soft = "Organización metódica, Discreción y ética profesional, Puntualidad intachable, Excelente presentación personal"

    # 3. ALMACÉN, BODEGA & LOGÍSTICA
    elif category in ["bodega", "logistics"] or "bodega" in target.lower() or "almacen" in target.lower() or "logist" in target.lower():
        summary = (
            f"Auxiliar de Bodega y Almacén con amplia experiencia en recepción, almacenamiento, clasificación, control de inventario, "
            f"alistamiento de pedidos (picking/packing) y despacho de mercancías. Con formación en normas de seguridad y salud en el trabajo, "
            f"resistencia física, orden y excelente manejo de la carga."
        )
        experience = user_experience or [
            {
                "role": "Auxiliar de Almacén, Bodega & Despacho",
                "company": "Centro de Distribución y Almacenamiento de Mercancías",
                "period": "2021 - 2024",
                "bullets": [
                    "Descargue, verificación física y cotejo de remisiones contra mercancía recibida de transportadores y proveedores.",
                    "Acomodación, rotulado y almacenamiento de productos en estanterías bajo método PEPS (primeras en entrar, primeras en salir).",
                    "Alistamiento, empaque seguro y rotulado de pedidos para entrega puntual a clientes y rutas de distribución.",
                    "Participación activa en inventarios físicos periódicos y mantenimiento del orden y aseo en las zonas de bodega."
                ]
            }
        ]
        skills_tech = "Recepción y despacho de mercancías, Control y conteo de inventarios, Picking y packing, Rotulado y embalaje de carga"
        skills_tools = "Carretillas manuales, Estibadores hidráulicos, Lector de código de barras, Formatos de remisión"
        skills_soft = "Fuerza y resistencia física, Disciplina operativa, Puntualidad rigurosa, Cuidado y protección del producto"

    # 4. ATENCIÓN AL CLIENTE & CALL CENTER
    elif category in ["servicio", "support"] or "cliente" in target.lower() or "soporte" in target.lower() or "call" in target.lower():
        summary = (
            f"Agente de Servicio al Cliente con vocación de servicio, empatía, excelente escucha activa y habilidad para brindar soluciones "
            f"ágiles a peticiones, quejas y reclamos (PQR). Enfocado en generar una experiencia positiva en el usuario, mantener la calma bajo "
            f"situaciones exigentes y asegurar la satisfacción y lealtad del cliente."
        )
        experience = user_experience or [
            {
                "role": "Asesor de Servicio al Cliente & Canales de Atención",
                "company": "Centro de Atención y Servicios Comerciales",
                "period": "2021 - 2024",
                "bullets": [
                    "Atención cálida y respetuosa a usuarios vía telefónica y presencial, resolviendo consultas y dudas sobre servicios.",
                    "Registro, tipificación y seguimiento de solicitudes en el sistema de gestión interna garantizando tiempos de respuesta oportunos.",
                    "Orientación precisa sobre trámites, productos, horarios y procedimientos de la empresa.",
                    "Transformación de inconformidades en experiencias positivas mediante diálogo empático y soluciones prácticas."
                ]
            }
        ]
        skills_tech = "Resolución de peticiones y reclamos (PQR), Protocolos de servicio al cliente, Escucha activa y comunicación asertiva"
        skills_tools = "Sistemas de tickets o radicación básica, Conmutadores, Diademas telefónicas, Chat y correo de atención"
        skills_soft = "Paciencia y tolerancia a la frustración, Dicción clara, Empatía natural, Trabajo en equipo, Responsabilidad"

    # 5. OPERARIO DE PRODUCCIÓN & PLANTA
    elif category == "operario" or "planta" in target.lower() or "fabrica" in target.lower() or "produccion" in target.lower():
        summary = (
            f"Operario de Producción y Planta con experiencia en líneas continuas de ensamble, envasado, empaque, manipulación de materias "
            f"primas y cumplimiento de estándares de calidad e higiene. Riguroso en el uso de Elementos de Protección Personal (EPP) y comprometido "
            f"con alcanzar las metas diarias fijadas por la jefatura de planta."
        )
        experience = user_experience or [
            {
                "role": "Operario de Producción & Línea de Ensamble",
                "company": "Planta de Producción y Manufactura Industrial",
                "period": "2021 - 2024",
                "bullets": [
                    "Operación en línea de ensamble y empaque cumpliendo estrictamente con las especificaciones de calidad y presentación.",
                    "Inspección visual continua del producto terminado para apartar unidades defectuosas antes del embalaje final.",
                    "Cumplimiento cabal de las normas de seguridad y salud en el trabajo (SST) y mantenimiento del orden y aseo (5S).",
                    "Aporte sostenido para superar el 100% de la cuota diaria de producción asignada a la cuadrilla de trabajo."
                ]
            }
        ]
        skills_tech = "Operación de línea de producción, Empaque y sellado, Inspección de calidad visual, Normas de seguridad industrial"
        skills_tools = "Herramientas manuales de ensamble, Selladoras, Básculas de pesado, Elementos de protección personal (EPP)"
        skills_soft = "Destreza y agilidad manual, Resistencia física, Atención meticulosa al detalle, Acatamiento estricto de órdenes"

    # 6. SEGURIDAD, VIGILANCIA & MANTENIMIENTO
    elif category == "seguridad" or "vigil" in target.lower() or "seguridad" in target.lower() or "conserje" in target.lower():
        summary = (
            f"Guarda de Seguridad y Vigilancia con experiencia en control de acceso de personas y vehículos, rondas de supervisión perimetral, "
            f"diligenciamiento de minutas y custodia responsable de instalaciones. Destacado por su alta disciplina, honradez intachable, "
            f"sentido de alerta constante y trato respetuoso con visitantes y residentes."
        )
        experience = user_experience or [
            {
                "role": "Guarda de Seguridad & Control de Accesos",
                "company": "Conjunto Residencial / Empresa de Seguridad Privada",
                "period": "2021 - 2024",
                "bullets": [
                    "Control y registro de ingresos y salidas de personas, contratistas y vehículos en el libro de minuta de seguridad.",
                    "Realización periódica de rondas de inspección física por el perímetro, puntos vulnerables y accesos del recinto.",
                    "Monitoreo de pantallas de circuito cerrado de televisión (CCTV) y reporte oportuno de cualquier anomalía.",
                    "Atención respetuosa y oportuna de situaciones imprevistas velando siempre por la tranquilidad de los usuarios."
                ]
            }
        ]
        skills_tech = "Control de accesos y registro vehicular, Rondas de inspección perimetral, Diligenciamiento de minutas, Monitoreo básico de cámaras"
        skills_tools = "Minuta de guardia, Radioteléfonos de comunicación, Sistemas de citofonía, Detectores de metales"
        skills_soft = "Honradez absoluta, Disciplina y firmeza respetuosa, Sentido de alerta constante, Puntualidad estricta"

    # 7. HOSTELERÍA, COCINA & MESERO
    elif category == "hosteleria" or "cocina" in target.lower() or "mesero" in target.lower() or "restaurante" in target.lower():
        summary = (
            f"Auxiliar de Servicio, Mesero y Cocina con experiencia en atención cordial de comensales a la mesa, toma de comandas, alistamiento "
            f"de materias primas (mise en place), higiene de áreas de trabajo y manipulación segura de alimentos. Dinámico, rápido, con vocación "
            f"de servicio y capacidad para trabajar en equipo en horas de alta demanda."
        )
        experience = user_experience or [
            {
                "role": "Mesero & Auxiliar de Servicio Gastronómico",
                "company": "Restaurante y Servicios Gastronómicos",
                "period": "2021 - 2024",
                "bullets": [
                    "Atención de mesas con alta calidez y rapidez, tomando pedidos y sirviendo platos y bebidas conforme a los estándares del local.",
                    "Apoyo en el alistamiento previo de insumos (mise en place), lavado, desinfección y porcionado de ingredientes.",
                    "Mantenimiento continuo de la higiene en salón, vajilla, cristalería y cocina cumpliendo normas sanitarias.",
                    "Cobro de cuentas y entrega de comprobantes a clientes garantizando la satisfacción del servicio."
                ]
            }
        ]
        skills_tech = "Servicio cordial a la mesa, Manipulación higiénica de alimentos, Toma y despacho de comandas, Aseo y desinfección"
        skills_tools = "Bandejas de servicio, Utensilios de cocina y porcionado, Puntos de cobro y comandas electrónicas"
        skills_soft = "Rapidez y agilidad física, Amabilidad permanente, Trabajo en equipo bajo presión, Compromiso y pulcritud"

    # 8. CONDUCTOR, REPARTO & MENSAJERÍA
    elif category == "transporte" or "conductor" in target.lower() or "reparto" in target.lower() or "mensajer" in target.lower():
        summary = (
            f"Conductor y Repartidor con amplia experiencia en transporte y distribución urbana de mercancías y encomiendas, manejo "
            f"defensivo, puntualidad en entregas y conocimiento de nomenclatura y rutas. Comprometido con el cuidado preventivo del vehículo, "
            f"la entrega íntegra de paquetes y la atención amable al cliente destinatario."
        )
        experience = user_experience or [
            {
                "role": "Conductor & Auxiliar de Reparto Urbano",
                "company": "Empresa de Logística, Reparto & Mensajería",
                "period": "2021 - 2024",
                "bullets": [
                    "Planificación y cumplimiento diario de rutas de entrega garantizando puntualidad y optimización de tiempos.",
                    "Cargue, estiba y aseguramiento cuidadoso de paquetes en el vehículo para prevenir roturas o pérdidas en tránsito.",
                    "Entrega directa a destinatarios, verificación de identidad, recaudo de pagos y firma de guías de recibido.",
                    "Inspección diaria del estado mecánico y preventivo del vehículo (frenos, aceite, llantas) manteniéndolo en óptimas condiciones."
                ]
            }
        ]
        skills_tech = "Manejo defensivo y normatividad de tránsito, Nomenclatura y optimización de rutas urbanas, Control de remisiones y guías"
        skills_tools = "Dispositivos GPS/Waze, Aplicaciones de entrega móvil, Formatos de planilla de reparto"
        skills_soft = "Puntualidad rigurosa, Responsabilidad en la vía, Honestidad y cuidado con la mercancía, Buen trato con el cliente"

    # 9. OTRO OFICIO / CARGO PERSONALIZADO
    else:
        summary = (
            f"Trabajador formal y responsable en el área de {target}, con experiencia comprobable en el cumplimiento de tareas operativas, "
            f"atención respetuosa al público y cuidado de los recursos asignados. Caracterizado por su puntualidad, dedicación, honestidad "
            f"y capacidad para integrarse con éxito a equipos de trabajo."
        )
        experience = user_experience or [
            {
                "role": target,
                "company": "Empresa Comercial y de Servicios",
                "period": "2021 - 2024",
                "bullets": [
                    f"Desempeño riguroso de las funciones y responsabilidades del puesto de {target}.",
                    "Cumplimiento puntual de las metas, directrices y normativas internas de la empresa.",
                    "Atención respetuosa y constructiva con clientes, compañeros y directivos.",
                    "Compromiso constante con la mejora continua, el orden y la seguridad en el trabajo."
                ]
            }
        ]
        skills_tech = f"Conocimientos prácticos en {target}, Ejecución de tareas operativas, Cumplimiento de procedimientos"
        skills_tools = "Herramientas y equipos propios del oficio, Elementos de trabajo asignados"
        skills_soft = "Puntualidad estricta, Honestidad comprobada, Disciplina laboral, Excelente disposición para el trabajo en equipo"

    # Enriquecimiento final con booster si no fue sobreescrito por el usuario
    if booster and not booster.get('skills_tech'):
        db_booster = get_vacancy_booster(booster.get('id') or category)
        if db_booster:
            for k in ['skills_tech', 'skills_tools', 'skills_soft']:
                if not booster.get(k):
                    booster[k] = db_booster.get(k)

    if user_data.get('custom_summary'):
        summary = user_data['custom_summary']
    elif booster and booster.get('summary') and category not in ["primer_empleo"]:
        summary = booster['summary']

    if user_data.get('custom_skills_tech'):
        skills_tech = user_data['custom_skills_tech']
    elif booster and booster.get('skills_tech'):
        skills_tech = booster['skills_tech']

    if user_data.get('custom_skills_tools'):
        skills_tools = user_data['custom_skills_tools']
    elif booster and booster.get('skills_tools'):
        skills_tools = booster['skills_tools']

    if user_data.get('custom_skills_soft'):
        skills_soft = user_data['custom_skills_soft']
    elif booster and booster.get('skills_soft'):
        skills_soft = booster['skills_soft']

    return {
        "name": name,
        "contact_line": contact_line,
        "summary": summary,
        "experience": experience,
        "skills_tech": skills_tech,
        "skills_tools": skills_tools,
        "skills_soft": skills_soft,
        "education": education_dict,
        "languages": languages_line
    }


# ========================================================
# Motor de Renderizado PDF para Hoja de Vida / CV Formal
# ========================================================

def build_formal_boxed_pdf(data):
    """Genera documento PDF en Cajas/Tarjetas ejecutivas idéntico a la estructura de referencia visual."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=26,
        rightMargin=26,
        topMargin=22,
        bottomMargin=22
    )
    styles = getSampleStyleSheet()

    c_banner_bg = colors.HexColor('#EBF3FA')
    c_card_bg = colors.HexColor('#FFFFFF')
    c_border = colors.HexColor('#D1DCE5')
    c_title = colors.HexColor('#1E3A8A')
    c_sec_title = colors.HexColor('#1D4ED8')
    c_text = colors.HexColor('#1E293B')
    c_muted = colors.HexColor('#64748B')
    c_line = colors.HexColor('#E2E8F0')

    page_width = letter[0] - 52  # 560 pt

    name_style = ParagraphStyle('BName', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=c_title, alignment=1)
    sub_style = ParagraphStyle('BSub', fontName='Helvetica', fontSize=8, leading=10.5, textColor=c_muted, alignment=1)
    sec_style = ParagraphStyle('BSec', fontName='Helvetica-Bold', fontSize=8.5, leading=10, textColor=c_sec_title, spaceAfter=3)
    body_style = ParagraphStyle('BBody', fontName='Helvetica', fontSize=7.5, leading=10, textColor=c_text)
    job_role = ParagraphStyle('BRole', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=c_title)
    job_meta = ParagraphStyle('BMeta', fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, textColor=c_muted, alignment=2)
    bullet_style = ParagraphStyle('BBullet', fontName='Helvetica', fontSize=7.3, leading=9.5, textColor=c_text, leftIndent=8, firstLineIndent=-6, spaceAfter=1)
    footer_style = ParagraphStyle('BFoot', fontName='Helvetica', fontSize=7.3, leading=9, textColor=c_muted, alignment=1)

    story = []

    # 1. HEADER BANNER
    candidate_name = data.get('name', 'CANDIDATO PROFESIONAL').upper()
    contact_line = data.get('contact_line')
    if not contact_line:
        parts = [p for p in [data.get('city'), data.get('phone'), data.get('email')] if p]
        contact_line = " &nbsp;•&nbsp; ".join(parts) if parts else "Contacto Disponible"

    h_content = [
        [Paragraph(candidate_name, name_style)],
        [Paragraph(contact_line, sub_style)]
    ]
    t_header = Table(h_content, colWidths=[page_width])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_banner_bg),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 6))

    # 2. PERFIL LABORAL
    prof_summary = data.get('summary', 'Profesional responsable y comprometido, con vocación de servicio y rápida adaptabilidad.')
    p_content = [
        [Paragraph('• PERFIL LABORAL / PROFESIONAL', sec_style)],
        [Paragraph(prof_summary, body_style)]
    ]
    t_perfil = Table(p_content, colWidths=[page_width])
    t_perfil.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_perfil)
    story.append(Spacer(1, 6))

    # 3. EXPERIENCIA LABORAL
    exp_inner = []
    exp_inner.append([Paragraph('• EXPERIENCIA LABORAL', sec_style)])
    
    for idx, job in enumerate(data['experience'][:2]):
        jh = [
            [Paragraph(f"{job['role']} — {job['company']}", job_role), Paragraph(job['period'], job_meta)]
        ]
        t_jh = Table(jh, colWidths=[page_width - 120, 100])
        t_jh.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2)
        ]))
        exp_inner.append([t_jh])
        b_paras = [Paragraph(f"• {b}", bullet_style) for b in job['bullets'][:3]]
        exp_inner.append([b_paras])
        if idx == 0 and len(data['experience']) > 1:
            exp_inner.append([HRFlowable(width='100%', thickness=0.5, color=c_line, spaceBefore=3, spaceAfter=3)])

    t_exp = Table(exp_inner, colWidths=[page_width])
    t_exp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_exp)
    story.append(Spacer(1, 6))

    # 4. EDUCACIÓN Y FORMACIÓN (Secundaria y Primaria con años)
    edu_inner = [[Paragraph('• EDUCACIÓN Y FORMACIÓN ACADÉMICA', sec_style)]]
    edu_data = data.get('education')
    if isinstance(edu_data, dict):
        sec = edu_data.get('secundaria')
        if sec and isinstance(sec, dict):
            sec_col = sec.get('colegio', 'Colegio de Educación Secundaria')
            sec_ano = sec.get('ano', '')
            sec_est = sec.get('estado', 'Bachiller Académico')
            sec_text = f"• <b>Educación Secundaria / Bachillerato:</b> {sec_col}"
            if sec_ano: sec_text += f" | Año: {sec_ano}"
            if sec_est: sec_text += f" — <i>{sec_est}</i>"
            edu_inner.append([Paragraph(sec_text, body_style)])
        pri = edu_data.get('primaria')
        if pri and isinstance(pri, dict):
            pri_col = pri.get('colegio', 'Escuela de Educación Primaria')
            pri_ano = pri.get('ano', '')
            pri_est = pri.get('estado', 'Primaria Completa')
            pri_text = f"• <b>Educación Básica Primaria:</b> {pri_col}"
            if pri_ano: pri_text += f" | Años: {pri_ano}"
            if pri_est: pri_text += f" — <i>{pri_est}</i>"
            edu_inner.append([Paragraph(pri_text, body_style)])
        extra = edu_data.get('extra')
        if extra and str(extra).strip():
            edu_inner.append([Paragraph(f"• <b>Cursos / Capacitaciones:</b> {extra}", body_style)])
    else:
        edu_inner.append([Paragraph('• <b>Educación Secundaria:</b> Colegio de Educación Secundaria — <i>Bachiller Graduado</i>', body_style)])
        edu_inner.append([Paragraph('• <b>Educación Básica Primaria:</b> Escuela de Educación Primaria — <i>Primaria Completa</i>', body_style)])

    t_edu = Table(edu_inner, colWidths=[page_width])
    t_edu.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_edu)
    story.append(Spacer(1, 6))

    # 5. DOS COLUMNAS AL PIE (HABILIDADES Y VALORES)
    col_w = (page_width - 8) / 2
    
    skills_raw = data.get('skills_tech', '')
    s_items = [s.strip() for s in skills_raw.split(',') if s.strip()][:4]
    if not s_items: s_items = ['Atención al cliente', 'Manejo de caja y cobro POS', 'Control de stock y pedidos', 'Orden en el puesto']
    left_content = [[Paragraph('• HABILIDADES DEL OFICIO', sec_style)]]
    for s in s_items: left_content.append([Paragraph(f"• {s}", bullet_style)])
    t_left = Table(left_content, colWidths=[col_w])
    t_left.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))

    soft_raw = data.get('skills_soft', '')
    v_items = [v.strip() for v in soft_raw.split(',') if v.strip()][:4]
    if not v_items: v_items = ['Puntualidad rigurosa', 'Honradez comprobada', 'Trabajo en equipo', 'Rápido aprendizaje']
    right_content = [[Paragraph('• VALORES Y APTITUDES', sec_style)]]
    for v in v_items: right_content.append([Paragraph(f"• {v}", bullet_style)])
    t_right = Table(right_content, colWidths=[col_w])
    t_right.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))

    t_cols = Table([[t_left, t_right]], colWidths=[col_w, col_w])
    t_cols.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('RIGHTPADDING', (0,0), (0,0), 4),
        ('LEFTPADDING', (1,0), (1,0), 4),
    ]))
    story.append(t_cols)
    story.append(Spacer(1, 6))

    # 6. FOOTER BANNER
    foot_content = [
        [Paragraph('Disponibilidad Horaria Inmediata &nbsp;•&nbsp; Referencias Laborales y Personales Disponibles a Solicitud', footer_style)]
    ]
    t_foot = Table(foot_content, colWidths=[page_width])
    t_foot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_banner_bg),
        ('BOX', (0,0), (-1,-1), 0.75, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(t_foot)

    doc.build(story)
    buffer.seek(0)
    return buffer


def build_ats_pdf(data):
    """Genera un documento PDF formal de 1 página, sobrio, elegante y 100% legible."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()
    color_primary = colors.HexColor('#0F172A')    # Slate 900
    color_section = colors.HexColor('#1E3A8A')    # Navy Blue formal
    color_body = colors.HexColor('#1E293B')       # Slate 800
    color_line = colors.HexColor('#CBD5E1')       # Borde sutil

    name_style = ParagraphStyle(
        'FormalName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=color_primary,
        alignment=1,
        spaceAfter=2
    )

    contact_style = ParagraphStyle(
        'FormalContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=10.5,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=5
    )

    heading_style = ParagraphStyle(
        'FormalHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11.5,
        textColor=color_section,
        spaceBefore=6,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'FormalBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=color_body,
        alignment=4,
        spaceAfter=3
    )

    role_style = ParagraphStyle(
        'FormalRole',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=color_primary,
        spaceBefore=2,
        spaceAfter=1
    )

    company_style = ParagraphStyle(
        'FormalCompany',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.8,
        leading=9.8,
        textColor=colors.HexColor('#475569'),
        spaceAfter=2
    )

    bullet_style = ParagraphStyle(
        'FormalBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.2,
        textColor=color_body,
        leftIndent=10,
        firstLineIndent=-7,
        spaceAfter=1.5
    )

    story = []

    # 1. ENCABEZADO FORMAL
    candidate_name = data.get('name', 'CANDIDATO PROFESIONAL').upper()
    contact_line = data.get('contact_line')
    if not contact_line:
        parts = [p for p in [data.get('city'), data.get('phone'), data.get('email')] if p]
        contact_line = " &nbsp;•&nbsp; ".join(parts) if parts else "Contacto Disponible"

    story.append(Paragraph(candidate_name, name_style))
    story.append(Paragraph(contact_line, contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=color_line, spaceBefore=2, spaceAfter=4))

    # 2. PERFIL LABORAL
    story.append(Paragraph("PERFIL LABORAL / PROFESIONAL", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=2))
    prof_summary = data.get('summary', 'Profesional con sólida experiencia y orientación a resultados.')
    story.append(Paragraph(prof_summary, body_style))

    # 3. EXPERIENCIA LABORAL
    story.append(Paragraph("EXPERIENCIA LABORAL", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=2))

    for job in data['experience']:
        story.append(Paragraph(job['role'], role_style))
        story.append(Paragraph(f"{job['company']} | {job['period']}", company_style))
        for bullet in job['bullets']:
            bullet_text = f"• {bullet}"
            story.append(Paragraph(bullet_text, bullet_style))
        story.append(Spacer(1, 2))

    # 4. FORMACIÓN ACADÉMICA (SECUNDARIA Y PRIMARIA DETALLADAS)
    story.append(Paragraph("FORMACIÓN ACADÉMICA", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=2))

    edu_data = data.get('education')
    if isinstance(edu_data, list):
        for item in edu_data:
            deg = item.get('degree', 'Estudios Superiores')
            sch = item.get('school', 'Universidad / Institución')
            per = item.get('period', '')
            txt = f"• <b>{deg}</b> — {sch}" + (f" ({per})" if per else "")
            story.append(Paragraph(txt, body_style))
    elif isinstance(edu_data, dict):
        # Modo remoto: universidad y certificaciones
        uni = edu_data.get('universidad')
        if uni and isinstance(uni, dict):
            uni_inst = uni.get('institucion', 'Universidad / Instituto Superior')
            uni_deg = uni.get('titulo', 'Estudios Profesionales')
            uni_yr = uni.get('ano', '')
            u_txt = f"• <b>{uni_deg}</b> — {uni_inst}" + (f" ({uni_yr})" if uni_yr else "")
            story.append(Paragraph(u_txt, body_style))
        certs = edu_data.get('certificaciones')
        if certs and str(certs).strip():
            story.append(Paragraph(f"• <b>Certificaciones:</b> {certs}", body_style))
        # Modo tradicional: secundaria y primaria
        sec = edu_data.get('secundaria')
        if sec and isinstance(sec, dict):
            sec_col = sec.get('colegio', 'Colegio de Educación Secundaria')
            sec_ano = sec.get('ano', '')
            sec_est = sec.get('estado', 'Bachiller Académico')
            sec_text = f"• <b>Educación Secundaria / Bachillerato:</b> {sec_col}"
            if sec_ano: sec_text += f" | {sec_ano}"
            if sec_est: sec_text += f" — <i>{sec_est}</i>"
            story.append(Paragraph(sec_text, body_style))
        pri = edu_data.get('primaria')
        if pri and isinstance(pri, dict):
            pri_col = pri.get('colegio', 'Escuela de Educación Primaria')
            pri_ano = pri.get('ano', '')
            pri_est = pri.get('estado', 'Primaria Completa')
            pri_text = f"• <b>Educación Básica Primaria:</b> {pri_col}"
            if pri_ano: pri_text += f" | {pri_ano}"
            if pri_est: pri_text += f" — <i>{pri_est}</i>"
            story.append(Paragraph(pri_text, body_style))
        extra = edu_data.get('extra')
        if extra and str(extra).strip():
            story.append(Paragraph(f"• <b>Otros Estudios / Cursos:</b> {extra}", body_style))
    elif isinstance(edu_data, str) and edu_data.strip():
        story.append(Paragraph(f"• {edu_data}", body_style))
    else:
        story.append(Paragraph("• <b>Educación Superior / Formación Continua:</b> Formación académica completa y verificable", body_style))

    # 5. COMPETENCIAS Y HABILIDADES
    story.append(Paragraph("COMPETENCIAS LABORALES & HABILIDADES", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=2))
    hard_skills = data.get('skills_tech') or data.get('skills_hard') or 'Competencias técnicas y operativas del cargo'
    soft_skills = data.get('skills_soft') or 'Puntualidad, Trabajo en Equipo, Honestidad, Adaptabilidad'
    story.append(Paragraph(f"<b>Competencias Principales:</b> {hard_skills}", body_style))
    story.append(Paragraph(f"<b>Valores & Aptitudes:</b> {soft_skills}", body_style))

    # 6. IDIOMAS (100% Opcional)
    lang_line = data.get('languages', '')
    if lang_line and 'solo' not in lang_line.lower() and 'native_only' not in lang_line.lower():
        story.append(Paragraph("IDIOMAS", heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=2))
        story.append(Paragraph(f"• {lang_line}", body_style))

    # 7. REFERENCIAS LABORALES Y PERSONALES
    story.append(Paragraph("REFERENCIAS LABORALES Y PERSONALES", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=color_line, spaceBefore=1, spaceAfter=2))
    story.append(Paragraph("Disponibles inmediatamente a solicitud del empleador con sus respectivos contactos de verificación.", body_style))

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
        msg = update.effective_message or update.message
        if not msg or not hasattr(msg, 'web_app_data') or not msg.web_app_data:
            return
        raw_data = msg.web_app_data.data
        data = json.loads(raw_data)
        if data.get('action') == 'generate_cv':
            context.user_data['cv_type'] = data.get('cv_type', 'formal_boxed')
            context.user_data['name'] = data.get('name', 'CANDIDATO PROFESIONAL')
            context.user_data['phone'] = data.get('phone', '')
            context.user_data['city'] = data.get('city', '')
            context.user_data['email'] = data.get('email', '')
            context.user_data['country'] = data.get('city', 'Modalidad Presencial / Remota')
            context.user_data['job_category'] = data.get('category', 'ventas')
            context.user_data['target_job'] = data.get('target_role', 'Asesor Comercial & Ventas')
            context.user_data['has_experience'] = data.get('has_experience', True)
            context.user_data['experience_data'] = data.get('experience_data')
            context.user_data['education'] = data.get('education')
            context.user_data['language'] = data.get('language', 'native_only')
            context.user_data['language_text'] = data.get('language_text', 'Español (Nativo)')
            context.user_data['exp_level'] = 'mid' if data.get('has_experience') else 'beginner'
            context.user_data['custom_exp_text'] = ''
            if data.get('booster_data'):
                context.user_data['booster_data'] = data.get('booster_data')
            if data.get('boosted_summary'):
                context.user_data['custom_summary'] = data.get('boosted_summary')

            save_subscriber(update.effective_user, country=context.user_data['country'], target_job=context.user_data['target_job'])
            await generate_and_send_final_cv(msg, update.effective_user, context)
    except Exception as e:
        logger.error(f"Error procesando web_app_data: {e}", exc_info=True)
        if update.effective_message:
            await update.effective_message.reply_text("⚠️ Ocurrió un inconveniente al procesar los datos de la Mini App. Puedes iniciar por chat con /cv.")


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
            CallbackQueryHandler(boost_apply_callback, pattern="^boost_apply_"),
            MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_CV)}$"), start_cv_entry)
        ],
        states={
            STEP_NAME: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_mode_callback, pattern="^mode_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name_step)
            ],
            STEP_COUNTRY: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(handle_country_callback, pattern="^country_")
            ],
            STEP_TARGET: [
                CallbackQueryHandler(cancel_cv_callback, pattern="^btn_cancel_cv$"),
                CallbackQueryHandler(boost_prompt_custom_callback, pattern="^boost_custom_prompt$"),
                CallbackQueryHandler(boost_apply_callback, pattern="^boost_apply_"),
                CallbackQueryHandler(boost_menu_callback, pattern="^btn_boost_menu$"),
                CallbackQueryHandler(boost_role_callback, pattern="^boost_role_"),
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
    app.add_handler(CommandHandler(['boost', 'hacks', 'trampa', 'optimizar', 'cheat'], boost_menu_callback))
    app.add_handler(CommandHandler(['pack', 'referidos'], referrals_menu_callback))
    app.add_handler(CommandHandler('kit', download_kit_callback))
    app.add_handler(CommandHandler('guia', guide_interviews_callback))
    app.add_handler(CommandHandler('alertas', toggle_alerts_callback))
    app.add_handler(CommandHandler('stats', stats_command))
    app.add_handler(CommandHandler('broadcast', broadcast_command))
    app.add_handler(CommandHandler('cancel', cancel))

    app.add_handler(CallbackQueryHandler(start, pattern="^btn_back_menu$"))
    app.add_handler(CallbackQueryHandler(boost_menu_callback, pattern="^btn_boost_menu$"))
    app.add_handler(CallbackQueryHandler(boost_role_callback, pattern="^boost_role_"))
    app.add_handler(CallbackQueryHandler(boost_prompt_custom_callback, pattern="^boost_custom_prompt$"))
    app.add_handler(CallbackQueryHandler(boost_apply_callback, pattern="^boost_apply_"))
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
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_BOOST)}$"), boost_menu_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_PACK)}$"), referrals_menu_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_CHANNEL)}$"), channel_link_tracker_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_KIT)}$"), download_kit_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_GUIDE)}$"), guide_interviews_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_ATS)}$"), why_ats_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_ALERTS)}$"), toggle_alerts_callback))
    app.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BOTTOM_ADMIN)}$"), admin_panel_command))

    # Captura de textos de usuario fuera de la conversación (pegar vacante / booster / dock)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_text_input_dispatcher))

    app.add_error_handler(global_error_handler)

    logger.info("Bot de CV ATS de Élite con Mega Panel Admin iniciado exitosamente.")
    start_health_server()
    app.run_polling(drop_pending_updates=True, stop_signals=None)


if __name__ == '__main__':
    main()
