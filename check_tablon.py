import requests
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
import os

BASE_URL = "https://sede.urjc.es"
TABLON_URL = BASE_URL + "/tablon-oficial/categoria/PAS/"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"].split(",")
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]

GH_API = f"https://api.github.com/repos/{GITHUB_REPO}/actions/variables/LAST_SEEN_URL"
GH_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def load_last_seen():
    r = requests.get(GH_API, headers=GH_HEADERS)
    if r.status_code == 200:
        return r.json().get("value")
    return None

def save_last_seen(url):
    r = requests.patch(GH_API, headers=GH_HEADERS, json={"name": "LAST_SEEN_URL", "value": url})
    if r.status_code == 404:
        requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/variables",
            headers=GH_HEADERS,
            json={"name": "LAST_SEEN_URL", "value": url}
        )

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
