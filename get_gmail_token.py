"""
Corre este script UNA SOLA VEZ, en tu computador (no en GitHub Actions).
Te va a abrir el navegador para que autorices el acceso de solo-lectura a tu Gmail.
Al terminar, va a crear un archivo token.json en esta misma carpeta.

Requisitos antes de correrlo:
1. Haber descargado credentials.json desde Google Cloud Console (paso 1 de la guía)
   y ponerlo en esta misma carpeta.
2. pip install -r requirements.txt
"""

from google_auth_oauthlib.flow import InstalledAppFlow

# Solo pedimos permiso de LECTURA, nunca de enviar/borrar correos.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("\n✅ Listo. Se creó token.json")
    print("Abre ese archivo y copia todo su contenido: lo vas a pegar como el secret")
    print("GMAIL_TOKEN_JSON en GitHub (paso 6 de la guía).")

if __name__ == "__main__":
    main()
