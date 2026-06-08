from bs4 import BeautifulSoup

from mailcleaner.services.encoding import decode_base64


def extract_readable_text(base64_html_content: str) -> str:
    decoded_content = decode_base64(base64_html_content)
    soup = BeautifulSoup(decoded_content, "html.parser")

    for tag in soup(["script", "style", "head", "noscript"]):
        tag.decompose()

    clean_content = soup.get_text(separator=" ", strip=True)
    if not clean_content:
        raise ValueError("empty cleaned content")

    return clean_content
