import base64
import os
from openai import OpenAI


DEFAULT_MODEL = "gpt-5.4"

MARKDOWN_PROMPT = (
    "You are an expert OCR assistant. Analyze the provided document image and extract all text content.\n"
    "Output in Markdown format, preserving headings, tables, lists, and paragraph structure.\n"
    "The document may have red stamps/seals covering text — try your best to recognize the text underneath.\n"
    "If a previous local OCR attempt is provided as reference, use it to improve your output but do not blindly copy errors.\n"
    "Output the recognized content directly, without any preamble or explanation."
)

JSON_PROMPT = (
    "You are an expert OCR assistant. Analyze the provided document image and extract all text content.\n"
    "Output as a JSON object with the following structure:\n"
    '{"content_markdown": "...", "tables": [{"headers": [...], "rows": [[...]]}], "metadata": {"title": "...", "date": "...", "parties": [...]}}\n'
    "The document may have red stamps/seals covering text — try your best to recognize the text underneath.\n"
    "If a previous local OCR attempt is provided as reference, use it to improve your output but do not blindly copy errors.\n"
    "Output valid JSON only, without any preamble or explanation."
)


def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _detect_mime(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext.lstrip("."), "image/png")


def fallback_ocr(
    image_path: str,
    local_ocr_text: str = "",
    output_format: str = "markdown",
    model: str | None = None,
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    model = model or DEFAULT_MODEL
    client = OpenAI(api_key=api_key)

    b64 = _image_to_base64(image_path)
    mime = _detect_mime(image_path)
    image_url = f"data:{mime};base64,{b64}"

    system_prompt = MARKDOWN_PROMPT if output_format == "markdown" else JSON_PROMPT

    user_content = []
    user_content.append({
        "type": "image_url",
        "image_url": {"url": image_url},
    })

    text_instruction = "Please perform OCR on this document image."
    if local_ocr_text:
        text_instruction += (
            "\n\nFor reference, here is a previous local OCR attempt (may contain errors):\n"
            f"```\n{local_ocr_text[:3000]}\n```"
        )
    user_content.append({"type": "text", "text": text_instruction})

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=16000,
        temperature=0.1,
    )

    return response.choices[0].message.content or ""
