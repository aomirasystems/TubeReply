"""Ejecuta esto UNA sola vez para conectar tu canal de YouTube."""
import glob
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

# Busca el archivo de credenciales con cualquier nombre
matches = glob.glob('client_secret*.json') + glob.glob('client_secrets.json')
if not matches:
    print("ERROR: No se encontró el archivo client_secrets.json en esta carpeta.")
    input("Presiona Enter para salir...")
    exit(1)
secrets_file = matches[0]

print("\n🦕 PaleoRealms Bot — Conexión con YouTube")
print("Se abrirá el navegador para que apruebes el acceso.\n")

flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
creds = flow.run_local_server(port=0)

with open('token.json', 'w') as f:
    f.write(creds.to_json())

print("✅ ¡Conectado! Ya puedes usar el bot.")
