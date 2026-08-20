"""
Clasificador + resumidor de correo institucional.

Flujo:
1. Lee los correos nuevos de Gmail desde la última vez que corrió (usa STATE_FILE).
2. Le pide a Gemini que los clasifique y resuma en un solo llamado (barato y rápido).
3. Manda el reporte por Telegram.
4. Actualiza STATE_FILE con la hora de este run.

Variables de entorno necesarias (se configuran como Secrets en GitHub):
- GMAIL_TOKEN_JSON      -> contenido completo de token.json (ver get_gmail_token.py)
- GEMINI_API_KEY        -> de aistudio.google.com/apikey
- TELEGRAM_BOT_TOKEN    -> de @BotFather
- TELEGRAM_CHAT_ID      -> tu chat id
"""

import os
import json
import base64
import time
from datetime import datetime, timedelta, timezone

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.generativeai as genai

STATE_FILE = "last_check.txt"
MAX_EMAILS_PER_RUN = 30  # límite de seguridad para no gastar cuota de golpe


# ---------- Gmail ----------

def get_gmail_service():
    token_json = os.environ["GMAIL_TOKEN_JSON"]
    creds = Credentials.from_authorized_user_info(json.loads(token_json))

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)


def get_last_check_timestamp() -> int:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return int(f.read().strip())
    # primera vez: mira solo las últimas 24h para no traer el historial completo
    return int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())


def save_last_check_timestamp(ts: int):
    with open(STATE_FILE, "w") as f:
        f.write(str(ts))


def fetch_new_emails(service, since_ts: int):
    query = f"after:{since_ts}"
    resp = service.users().messages().list(
        userId="me", q=query, maxResults=MAX_EMAILS_PER_RUN
    ).execute()

    message_ids = resp.get("messages", [])
    emails = []

    for m in message_ids:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        emails.append({
            "id": m["id"],
            "subject": headers.get("Subject", "(sin asunto)"),
            "from": headers.get("From", "desconocido"),
            "snippet": msg.get("snippet", ""),
        })

    return emails


# ---------- Gemini ----------

def classify_and_summarize(emails: list) -> list:
    if not emails:
        return []

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash-lite")

    prompt = f"""
Eres un asistente que clasifica correos de un estudiante universitario.
Para cada correo de la lista de abajo, devuelve un objeto JSON con:
- "id": el mismo id que te di
- "categoria": una de ["Universidad", "Servicios", "Personal", "Promocional"]
- "resumen": una frase muy corta (máx 15 palabras) de qué trata, en español
- "urgente": true/false (true solo si parece requerir acción pronto: fechas límite,
  pagos, citaciones, notas importantes)

Responde SOLO con un array JSON válido, nada de texto extra ni markdown.

Correos:
{json.dumps(emails, ensure_ascii=False, indent=2)}
"""

    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )

    try:
        results = json.loads(response.text)
    except (json.JSONDecodeError, AttributeError):
        # si Gemini no devolvió JSON limpio, no tumbamos el run entero
        return []

    # cruzamos con los datos originales (asunto/remitente) para armar el mensaje
    by_id = {e["id"]: e for e in emails}
    for r in results:
        original = by_id.get(r.get("id"), {})
        r["subject"] = original.get("subject", "")
        r["from"] = original.get("from", "")

    return results


# ---------- Telegram ----------

def format_message(results: list) -> str:
    if not results:
        return "📭 No llegaron correos nuevos desde el último chequeo."

    categorias = {}
    for r in results:
        categorias.setdefault(r.get("categoria", "Otro"), []).append(r)

    lines = [f"📬 *Resumen de correo* — {len(results)} nuevo(s)\n"]

    orden = ["Universidad", "Servicios", "Personal", "Promocional"]
    for cat in orden:
        items = categorias.get(cat)
        if not items:
            continue
        lines.append(f"\n*{cat}*")
        for r in items:
            marca = "🔴" if r.get("urgente") else "•"
            remitente = r.get("from", "").split("<")[0].strip()
            lines.append(f"{marca} {remitente}: {r.get('resumen', '')}")

    return "\n".join(lines)


def send_telegram(message: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram limita a 4096 caracteres por mensaje
    for i in range(0, len(message), 4000):
        chunk = message[i:i + 4000]
        r = requests.post(url, data={
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
        })
        r.raise_for_status()
        time.sleep(0.5)


# ---------- Main ----------

def main():
    service = get_gmail_service()
    since_ts = get_last_check_timestamp()
    run_ts = int(datetime.now(timezone.utc).timestamp())

    emails = fetch_new_emails(service, since_ts)
    print(f"Correos nuevos encontrados: {len(emails)}")

    if not emails:
        # nada nuevo: no molestamos por Telegram, solo actualizamos el checkpoint
        save_last_check_timestamp(run_ts)
        print("Nada nuevo, no se envía mensaje.")
        return

    results = classify_and_summarize(emails)
    message = format_message(results)

    send_telegram(message)
    save_last_check_timestamp(run_ts)

    print("Listo. Reporte enviado.")


if __name__ == "__main__":
    main()
