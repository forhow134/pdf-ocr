import tempfile
import os
from pathlib import Path
from pdf2image import convert_from_path


def pdf_to_images(pdf_path: str, dpi: int = 300, output_dir: str | None = None) -> list[str]:
    pdf_path = str(Path(pdf_path).resolve())
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="pdf_ocr_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    images = convert_from_path(pdf_path, dpi=dpi, fmt="png", output_folder=output_dir)

    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(output_dir, f"page_{i + 1:04d}.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths
