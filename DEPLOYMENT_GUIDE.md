# 🚀 Guía de Despliegue 24/7 Gratuito en la Nube (Cloud Hosting)

Esta guía explica cómo mantener tu **Bot de Telegram con Piloto Automático Agéntico** activo las 24 horas del día, los 7 días de la semana de forma 100% gratuita y sin necesidad de mantener encendida tu computadora.

---

## 🛠️ Archivos Clave de Configuración Ya Creados
1. Procfile: Indica al servidor en la nube cómo iniciar el proceso de fondo (worker: python bot.py).
2. 
untime.txt: Fija la versión de Python (python-3.12.0).
3. 
equirements.txt: Lista de dependencias del bot.
4. 
ender.yaml: Blueprint declarativo para Render.com.
5. utopilot.json: Estado persistente del bucle autónomo.

---

## Option 1: Despliegue en Render.com (Recomendado)

Render permite vincular tu repositorio de GitHub y levantar el bot automáticamente:

### Pasos:
1. **Subir el proyecto a GitHub**:
   - Crea un repositorio privado o público en [GitHub](https://github.com/new).
   - Sube los archivos de este directorio (	elegram-cv-bot).
   *(Nota: Asegúrate de NO subir tu archivo .env personal al repositorio público).*

2. **Crear cuenta en Render**:
   - Entra en [Render.com](https://render.com) e inicia sesión con tu cuenta de GitHub.

3. **Crear un nuevo servicio**:
   - Pulsa **New +** > **Background Worker** (o **Web Service**).
   - Selecciona el repositorio de GitHub de tu bot.
   - Configura:
     - **Name**: 	elegram-cv-bot
     - **Region**: Oregon (US West) o Frankfurt
     - **Branch**: main
     - **Build Command**: pip install -r requirements.txt
     - **Start Command**: python bot.py
     - **Plan**: Free

4. **Variables de Entorno (Environment Variables)**:
   En la pestaña **Environment**, añade:
   - TELEGRAM_BOT_TOKEN = (Tu token del bot de @BotFather)
   - ADMIN_ID = 8295054958
   - SPONSOR_CHANNEL_URL = https://t.me/empleosremotos_oficial
   - PYTHON_VERSION = 3.12.0

5. **Deploy**:
   - Pulsa **Deploy**. Render instalará las dependencias y arrancará ot.py.
   - En la pestaña **Logs** verás: Bot de CV ATS de Élite con Mega Panel Admin iniciado exitosamente y Iniciando bucle de Piloto Automático Agéntico 24/7....

---

## Option 2: Despliegue en Railway.app (Alternativa Rápida)

Railway detecta automáticamente el Procfile y arranca workers sin configuración adicional:

### Pasos:
1. Entra a [Railway.app](https://railway.app/) y logueate con GitHub.
2. Pulsa **New Project** > **Deploy from GitHub repo**.
3. Selecciona tu repositorio.
4. Ve a la pestaña **Variables** y agrega:
   - TELEGRAM_BOT_TOKEN
   - ADMIN_ID
   - SPONSOR_CHANNEL_URL
5. Railway detectará el Procfile y pondrá en ejecución el worker en cuestión de segundos.

---

## ⚡ Verificación del Piloto Automático en la Nube
Una vez desplegado:
1. Abre tu Telegram y envía /admin a tu bot.
2. Comprueba que el botón [🤖 Piloto Automático: ACTIVADO 🟢] está presente.
3. Puedes probar la publicación inmediata tocando [⚡ Forzar Publicación Inmediata Ahora].
4. ¡El bot continuará publicando automáticamente cada 6 horas según el ciclo programado!
