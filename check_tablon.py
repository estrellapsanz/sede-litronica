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

    # Descargar PDFs de la sección de anexos
    pdfs = []
    # Usamos un User-Agent para que la web no rechace la petición del script
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text().lower()
        
        # Ampliamos el filtro: que contenga .pdf en el link O que el texto del enlace mencione "pdf" o "anexo"
        if ".pdf" in href.lower() or "pdf" in text or "anexo" in text:
            pdf_url = href if href.startswith("http") else BASE_URL + href
            print(prf_url)
            # Limpiar el nombre del archivo para que no tenga caracteres raros
            pdf_name = href.split("/")[-1].split("?")[0]
            if not pdf_name.lower().endswith(".pdf"):
                pdf_name += ".pdf"

            try:
                # Añadimos headers y permitimos redirecciones (allow_redirects=True)
                r_pdf = requests.get(pdf_url, headers=headers, timeout=30, allow_redirects=True)
                r_pdf.raise_for_status()
                
                # Verificamos que realmente sea un PDF por el Content-Type
                if "application/pdf" in r_pdf.headers.get("Content-Type", "").lower():
                    pdfs.append((pdf_name, r_pdf.content))
                    print(f"PDF descargado con éxito: {pdf_name}")
                else:
                    print(f"El enlace {pdf_url} no parece un PDF real.")
                    
            except Exception as e:
                print(f"Error descargando {pdf_url}: {e}")

    # Enviar correo con PDFs adjuntos
    send_email(title, link, pdfs)

    # Guardar último anuncio visto
    save_last_seen(link)

if __name__ == "__main__":
    main()
