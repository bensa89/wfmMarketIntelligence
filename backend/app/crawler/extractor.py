import hashlib
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup
from markdownify import markdownify


@dataclass
class ExtractionResult:
    title: Optional[str]
    markdown: str
    content_hash: str


def extract_content(html: str, url: str = "") -> ExtractionResult:
    soup = BeautifulSoup(html, "html.parser")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body") or soup

    markdown = markdownify(str(main), heading_style="ATX", strip=["a"]).strip()
    markdown = "\n".join(line for line in markdown.splitlines() if line.strip())

    content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    return ExtractionResult(title=title, markdown=markdown, content_hash=content_hash)
