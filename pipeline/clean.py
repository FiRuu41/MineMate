import trafilatura


def html_to_markdown(html: str) -> str:
    text = trafilatura.extract(html, output_format="markdown", favor_recall=True) or ""
    return text.strip()
