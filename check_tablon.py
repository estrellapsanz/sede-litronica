import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os

BASE_URL = "https://sede.urjc.es"
TABLON_URL = BASE_URL + "/tablon-oficial/categoria/PAS/"
LAST_SEEN_FILE = "last_seen.txt"

# Variables de entorno para Gmail
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

def load_last_seen():
    if not os.path.exists(LAST_SEEN_FILE):
        return None
    with open(LAST_SEEN_FILE) as f:
        return f.read().strip()

def save_last_seen(url):
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(url)

def send_email(title, link, pdfs):
    msg = EmailMessage()
    msg["Subject"] = "¡Nuevo enlace en la sede electrónica de la URJC!"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    msg.set_content(f"""¡Nuevo enlace en la sede electrónica de la URJC!

Anuncio: {title}
Enlace: {link}

¡Saluditos!
""")

    for name, content in pdfs:
        msg.add_attachment(
            content,
            maintype="application",
            subtype="pdf",
            filename=name
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

def main():
    last_seen = load_last_seen()

    r = requests.get(TABLON_URL, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    # Buscar todos los enlaces a anuncios
    enlaces = [a for a in soup.find_all("a", href=True) if a["href"].startswith("/tablon-oficial/anuncio/")]
    if not enlaces:
        print("No se han encontrado anuncios")
        return

    # Tomamos el primer anuncio (el más reciente)
    enlace = enlaces[0]
    link = BASE_URL + enlace["href"]
    title = enlace.get_text(strip=True)

    if link == last_seen:
        print("No hay anuncios nuevos")
        return

    # Descargar página del anuncio
    r = requests.get(link, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    # Descargar todos los PDFs del anuncio
    pdfs = []
    for a in soup.find_all("a"_
