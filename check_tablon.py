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

    # Adjuntar todos los PDFs descargados
    for name, content in pdfs:
        msg.add_attachment(
            content,
            maintype="application",
            subtype="pdf",
            filename=name
        )

    # Enviar correo via Gmail
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

def main():
    last_seen = load_last_seen()

    # Descargar página principal del tablón
    r = requests.get(TABLON_URL, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    # Buscar enlaces a anuncios
    enlaces = [a for a in soup.find_all("a", href=True) if a["href"].startswith("/tablon-oficial/anuncio/")]
    if not enlaces:
        print("No se han encontrado anuncios")
        return

    # Tomamos el anuncio más reciente
    enlace = enlaces[0]
    link = BASE_URL + enlace["href"]
    title = enlace.get_text(strip=True)

    if link == last_seen:
        print("No hay anuncios nuevos")
        return

    # Descargar página del anuncio
    r = requests.get(link, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    # Descargar PDFs de la sección de anexos (incluso si tienen parámetros)
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" not in href.lower():  # ✅ antes solo filtrábamos por .endswith
            continue
        pdf_url = href if href.startswith("http") else BASE_URL + href
        pdf_name = pdf_url.split("/")[-1].split("?")[0]  # limpiar parámetros

        try:
            r_pdf = requests.get(pdf_url, timeout=30)
            r_pdf.raise_for_status()
            pdfs.append((pdf_name, r_pdf.content))
            print(f"PDF descargado: {pdf_name}")
        except Exception as e:
            print(f"No se pudo descargar {pdf_url}: {e}")

    # Enviar correo con PDFs adjuntos
    send_email(title, link, pdfs)

    # Guardar último anuncio visto
    save_last_seen(link)

if __name__ == "__main__":
    main()
