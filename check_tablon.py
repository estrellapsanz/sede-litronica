import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os

BASE_URL = "https://sede.urjc.es"
TABLON_URL = BASE_URL + "/tablon-oficial/categoria/PAS/"
LAST_SEEN_FILE = "last_seen.txt"

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

    body = f"""¡Nuevo enlace en la sede electrónica de la URJC!

Anuncio: {title}
Enlace: {link}

¡Saluditos!
"""
    msg.set_content(body)

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

    r = requests.get(TABLON_URL)
    soup = BeautifulSoup(r.text, "html.parser")

    anuncio = soup.select_one("article a")
    link = BASE_URL + anuncio["href"]
    title = anuncio.get_text(strip=True)

    if link == last_seen:
        print("No hay anuncios nuevos")
        return

    r = requests.get(link)
    soup = BeautifulSoup(r.text, "html.parser")

    pdfs = []
    for a in soup.select("a[href$='.pdf']"):
        pdf_url = BASE_URL + a["href"]
        pdf_name = pdf_url.split("/")[-1]
        pdf_content = requests.get(pdf_url).content
        pdfs.append((pdf_name, pdf_content))

    send_email(title, link, pdfs)
    save_last_seen(link)

if __name__ == "__main__":
    main()
