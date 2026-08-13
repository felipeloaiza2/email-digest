# Resumidor de correo institucional → Telegram

Lee tus correos nuevos, los clasifica (Universidad / Servicios / Personal / Promocional),
detecta cuáles parecen urgentes, y te manda un resumen por Telegram. No mueve, borra
ni responde nada — solo lee y reporta.

## 1. Google Cloud + Gmail API

1. Ve a https://console.cloud.google.com y crea un proyecto nuevo.
2. En **APIs y servicios → Biblioteca**, busca "Gmail API" y actívala.
3. En **APIs y servicios → Pantalla de consentimiento OAuth**, elige "Externo",
   completa lo básico (nombre de la app, tu correo) y agrégate a ti mismo como
   "usuario de prueba".
4. En **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**,
   tipo de aplicación **"Aplicación de escritorio"**.
5. Descarga el JSON resultante, ponlo en esta carpeta como `credentials.json`.

## 2. Bot de Telegram

1. En Telegram, busca `@BotFather` → `/newbot` → sigue las instrucciones.
2. Guarda el **token** que te da.
3. Escríbele un mensaje cualquiera a tu bot nuevo (para que sepa quién eres).
4. Visita en el navegador:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
   Busca `"chat":{"id": ...}` — ese número es tu `TELEGRAM_CHAT_ID`.

## 3. API key de Gemini (gratis)

1. Ve a https://aistudio.google.com/apikey con tu cuenta de Google.
2. Genera una API key. No pide tarjeta.

## 4. Generar el token de Gmail (local, una sola vez)

```bash
pip install -r requirements.txt
python get_gmail_token.py
```

Esto abre el navegador, autorizas el acceso de solo lectura, y se crea `token.json`.
Abre ese archivo y copia todo su contenido (es una sola línea de JSON).

## 5. Probar localmente (opcional pero recomendado)

```bash
export GMAIL_TOKEN_JSON="$(cat token.json)"
export GEMINI_API_KEY="tu_api_key"
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"

python main.py
```

Si todo salió bien, te debería llegar un mensaje de Telegram.

## 6. Subir a GitHub y automatizar

```bash
git init
git add .
git commit -m "Setup inicial"
gh repo create email-digest --private --source=. --push
# o crea el repo desde github.com y haz git remote add + push
```

**Importante:** `credentials.json` y `token.json` NUNCA deben subirse al repo
(agrégalos a un `.gitignore`). Lo que sí necesitas es guardar sus contenidos como
Secrets del repo:

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**,
crea estos 4:

| Secret               | Valor                                  |
|----------------------|-----------------------------------------|
| `GMAIL_TOKEN_JSON`   | contenido completo de `token.json`      |
| `GEMINI_API_KEY`     | tu API key de Gemini                    |
| `TELEGRAM_BOT_TOKEN` | el token de BotFather                   |
| `TELEGRAM_CHAT_ID`   | tu chat id                              |

El workflow ya está en `.github/workflows/digest.yml`, corre todas las mañanas
(ajusta la hora del cron si quieres) y también lo puedes disparar manualmente
desde la pestaña **Actions → Resumen diario de correo → Run workflow**.

## Notas

- El tier gratis de Gemini Flash te alcanza de sobra para el volumen de correo
  de una persona (revisa límites actuales en ai.google.dev/pricing, cambian de vez en cuando).
  Si algún día lo notas lento o corto, cambia `"gemini-2.5-flash"` por
  `"gemini-2.5-flash-lite"` en `main.py`.
- GitHub Actions es gratis para repos privados dentro de un límite mensual de minutos;
  este script corre en segundos, así que no hay riesgo de gastarlo.
- Cuando quieras dar el siguiente paso (etiquetas automáticas en Gmail), solo hay
  que cambiar el scope de `gmail.readonly` a `gmail.modify` y agregar la llamada
  a la API para aplicar labels — el resto de la arquitectura se queda igual.
