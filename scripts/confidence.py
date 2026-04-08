import re
import unicodedata


def _is_cjk(ch: str) -> bool:
    try:
        name = unicodedata.name(ch, "")
    except ValueError:
        return False
    return "CJK" in name or "HANGUL" in name or "HIRAGANA" in name or "KATAKANA" in name


def _is_normal_char(ch: str) -> bool:
    if ch.isascii():
        return True
    if _is_cjk(ch):
        return True
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S") or cat.startswith("Z"):
        return True
    return False


def evaluate_confidence(
    text: str,
    image_width: int = 0,
    image_height: int = 0,
) -> dict:
    reasons: list[str] = []

    text_length = len(text.strip())
    if text_length == 0:
        return {"score": 0.0, "reasons": ["empty text"]}

    length_score = 1.0
    if text_length < 50:
        length_score = text_length / 50.0
        reasons.append(f"text too short ({text_length} chars)")

    chars = [ch for ch in text if not ch.isspace()]
    if chars:
        abnormal = sum(1 for ch in chars if not _is_normal_char(ch))
        abnormal_ratio = abnormal / len(chars)
    else:
        abnormal_ratio = 1.0
    garble_score = max(0.0, 1.0 - abnormal_ratio * 5)
    if abnormal_ratio > 0.2:
        reasons.append(f"garbled chars {abnormal_ratio:.0%}")

    density_score = 1.0
    if image_width > 0 and image_height > 0:
        area = image_width * image_height
        density = text_length / (area / 10000)
        if density < 0.5:
            density_score = density / 0.5
            reasons.append(f"low text density ({density:.2f})")

    structure_score = 0.0
    structure_markers = {
        "heading": r"^#{1,6}\s",
        "table": r"\|.*\|",
        "list": r"^[-*]\s",
        "bold": r"\*\*.+?\*\*",
    }
    found = 0
    for name, pattern in structure_markers.items():
        if re.search(pattern, text, re.MULTILINE):
            found += 1
    structure_score = min(1.0, found / 2.0)
    if found == 0:
        reasons.append("no markdown structure detected")

    cjk_count = sum(1 for ch in text if _is_cjk(ch))
    ascii_count = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    total_alpha = cjk_count + ascii_count
    if total_alpha > 0:
        lang_consistency = 1.0
    else:
        lang_consistency = 0.5
        reasons.append("no recognizable language chars")

    weights = {
        "length": 0.30,
        "garble": 0.25,
        "density": 0.20,
        "structure": 0.15,
        "language": 0.10,
    }
    score = (
        weights["length"] * length_score
        + weights["garble"] * garble_score
        + weights["density"] * density_score
        + weights["structure"] * structure_score
        + weights["language"] * lang_consistency
    )
    score = round(max(0.0, min(1.0, score)), 3)

    return {"score": score, "reasons": reasons}
