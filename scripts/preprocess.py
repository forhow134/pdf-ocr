import os
import numpy as np
from PIL import Image, ImageEnhance


def enhance_image(image: Image.Image, contrast: float = 1.5, sharpness: float = 2.0) -> Image.Image:
    img = ImageEnhance.Contrast(image).enhance(contrast)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def remove_red_stamp(image: Image.Image, fade_strength: float = 0.85) -> Image.Image:
    arr = np.array(image.convert("RGB")).astype(np.float32)

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mask = (r > 150) & (g < 100) & (b < 100)
    mask = mask | ((r > 180) & (g < 120) & (b < 120) & (r > g * 1.5) & (r > b * 1.5))

    white = np.full_like(arr, 255.0)
    blend = np.where(mask[:, :, np.newaxis], arr * (1 - fade_strength) + white * fade_strength, arr)
    blend = np.clip(blend, 0, 255).astype(np.uint8)

    return Image.fromarray(blend)


def preprocess_page(
    image_path: str,
    enhance: bool = True,
    stamp_mask: bool = False,
    output_dir: str | None = None,
) -> dict[str, str]:
    img = Image.open(image_path).convert("RGB")
    base_name = os.path.splitext(os.path.basename(image_path))[0]

    if output_dir is None:
        output_dir = os.path.dirname(image_path)

    results = {"original": image_path}

    if enhance:
        enhanced = enhance_image(img)
        if stamp_mask:
            enhanced = remove_red_stamp(enhanced)
        enhanced_path = os.path.join(output_dir, f"{base_name}_enhanced.png")
        enhanced.save(enhanced_path, "PNG")
        results["enhanced"] = enhanced_path
    elif stamp_mask:
        masked = remove_red_stamp(img)
        masked_path = os.path.join(output_dir, f"{base_name}_masked.png")
        masked.save(masked_path, "PNG")
        results["masked"] = masked_path

    return results
