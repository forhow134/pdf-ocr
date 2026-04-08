import base64
import re
import time
import os
import requests
from PIL import Image
from io import BytesIO

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "glm-ocr"
MAX_IMAGE_PIXELS = 1536

OCR_PROMPT = (
    "请对这张文档图片进行完整的OCR识别，输出Markdown格式。"
    "保留文档的标题层级、表格结构、段落划分。"
    "注意：文档上可能有印章覆盖文字，请尽量识别被覆盖的文字内容。"
)

SPECIAL_TOKEN_RE = re.compile(r"<\|[^|]+\|>")


def _image_to_base64(image_path: str, max_dim: int = MAX_IMAGE_PIXELS) -> str:
    img = Image.open(image_path)
    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _clean_output(text: str) -> str:
    text = SPECIAL_TOKEN_RE.sub("", text)
    text = re.sub(r"<table>\s*(<tr>\s*(<td>\s*</td>)+\s*</tr>\s*)+</table>", "", text)
    return text.strip()


def _call_ollama(image_base64: str, prompt: str, host: str, model: str) -> str:
    url = f"{host}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4096,
        },
    }
    resp = requests.post(url, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    raw = data.get("response", "")
    return _clean_output(raw)


def _count_markdown_features(text: str) -> int:
    score = 0
    for marker in ["#", "|", "- ", "**", "```"]:
        if marker in text:
            score += 1
    return score


def ocr_page(
    image_paths: dict[str, str],
    host: str | None = None,
    model: str | None = None,
) -> dict:
    host = host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    model = model or DEFAULT_MODEL

    start = time.time()
    best_text = ""
    best_score = -1

    for variant, path in image_paths.items():
        try:
            b64 = _image_to_base64(path)
            text = _call_ollama(b64, OCR_PROMPT, host, model)
            score = len(text) + _count_markdown_features(text) * 50
            if score > best_score:
                best_score = score
                best_text = text
        except Exception:
            continue

    elapsed = time.time() - start

    return {
        "text": best_text,
        "engine": model,
        "elapsed_seconds": round(elapsed, 2),
    }
