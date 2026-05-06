import html
import re


LINK_RE = re.compile(
    r'<a\s+href=(["\'])(https?://[^"\']+)\1>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def prepare_html_text(text: str) -> str:
    """
    Экранирует опасный HTML, но разрешает:
    <b>, <i>, <a href="https://...">
    """
    links = []

    def save_link(match: re.Match) -> str:
        url = match.group(2)
        label = match.group(3)

        safe_url = html.escape(url, quote=True)
        safe_label = html.escape(strip_html_formatting(label), quote=False)

        placeholder = f"__SAFE_LINK_{len(links)}__"
        links.append(f'<a href="{safe_url}">{safe_label}</a>')
        return placeholder

    text_with_placeholders = LINK_RE.sub(save_link, text)

    escaped_text = html.escape(text_with_placeholders, quote=False)

    allowed_replacements = {
        "&lt;b&gt;": "<b>",
        "&lt;/b&gt;": "</b>",
        "&lt;i&gt;": "<i>",
        "&lt;/i&gt;": "</i>",
    }

    for escaped_tag, real_tag in allowed_replacements.items():
        escaped_text = escaped_text.replace(escaped_tag, real_tag)

    for index, link in enumerate(links):
        escaped_text = escaped_text.replace(f"__SAFE_LINK_{index}__", link)

    return escaped_text


def strip_html_formatting(text: str) -> str:
    """
    Убирает HTML для VK.
    Ссылки превращает в: текст (url), чтобы URL не потерялся.
    """
    def replace_link(match: re.Match) -> str:
        url = html.unescape(match.group(2))
        label = html.unescape(re.sub(r"<[^>]+>", "", match.group(3))).strip()

        if not label or label == url:
            return url

        return f"{label} ({url})"

    text = LINK_RE.sub(replace_link, text)
    text = re.sub(r"</?(b|i)>", "", text)
    text = re.sub(r"<[^>]+>", "", text)

    return html.unescape(text)