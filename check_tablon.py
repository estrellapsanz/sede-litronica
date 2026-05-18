import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os

BASE_URL = "https://sede.urjc.es"
TABLON_URL = BASE_URL + "/tablon-oficial/categoria/PAS/"
LAST_SEEN_FILE = "last_seen.txt"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"].split(",")  # "a@x.com,b@y.com"
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
    msg["To"] = ", ".join(EMAIL_TO)
    msg.set_content(f"¡Nuevo enlace en la sede electrónica de la URJC!\n\nAnuncio: {title}\nEnlace: {link}\n\n¡Saluditos!\n")

    for name, content in pdfs:
        msg.add_attachment(content, maintype="application", subtype="pdf", filename=name)

    
    with smtplib.SMTP("smtp-relay.brevo.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

def main():
    last_seen = load_last_seen()

    r = requests.get(TABLON_URL, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    enlaces = [a for a in soup.find_all("a", href=True) if a["href"].startswith("/tablon-oficial/anuncio/")]
    if not enlaces:
        print("No se han encontrado anuncios")
        return

    enlace = enlaces[0]
    link = BASE_URL + enlace["href"]
    title = enlace.get_text(strip=True)

    if link == last_seen:
        print("No hay anuncios nuevos")
        return

    r = requests.get(link, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    pdfs = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text().lower()
        if ".pdf" in href.lower() or "pdf" in text or "anexo" in text:
            pdf_url = href if href.startswith("http") else BASE_URL + href
            print(pdf_url)
            pdf_name = href.split("/")[-1].split("?")[0]
            if not pdf_name.lower().endswith(".pdf"):
                pdf_name += ".pdf"
            try:
                r_pdf = requests.get(pdf_url, headers=headers, timeout=30, allow_redirects=True)
                r_pdf.raise_for_status()
                if "application/pdf" in r_pdf.headers.get("Content-Type", "").lower():
                    pdfs.append((pdf_name, r_pdf.content))
                    print(f"PDF descargado: {pdf_name}")
                else:
                    print(f"No es PDF real: {pdf_url}")
            except Exception as e:
                print(f"Error descargando {pdf_url}: {e}")

    send_email(title, link, pdfs)
    save_last_seen(link)
    print(f"Correo enviado para: {title}")

if __name__ == "__main__":
    main()
