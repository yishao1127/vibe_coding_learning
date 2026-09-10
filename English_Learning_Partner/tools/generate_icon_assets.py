"""Generate transparent application icons from the supplied leaf artwork."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "assets" / "icon-source" / "leaf.jpg"
PNG_PATH = ROOT / "resources" / "app_icon.png"
ICO_PATH = ROOT / "resources" / "app_icon.ico"
ICON_SIZE = 512
WHITE_START = 228
WHITE_END = 250


def remove_white_background(image: Image.Image) -> Image.Image:
    """Turn the JPEG's white backdrop and white cut-outs transparent smoothly."""
    rgb = image.convert("RGB")
    pixels = rgb.load()
    rgba = Image.new("RGBA", rgb.size)
    output = rgba.load()

    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = pixels[x, y]
            brightness = min(red, green, blue)
            alpha = max(0, min(255, round((WHITE_END - brightness) * 255 / (WHITE_END - WHITE_START))))
            if alpha:
                # Undo white matte blending at anti-aliased edges before storing alpha.
                output[x, y] = (
                    max(0, min(255, round((red - (255 - alpha)) * 255 / alpha))),
                    max(0, min(255, round((green - (255 - alpha)) * 255 / alpha))),
                    max(0, min(255, round((blue - (255 - alpha)) * 255 / alpha))),
                    alpha,
                )
            else:
                output[x, y] = (0, 0, 0, 0)

    alpha_channel = rgba.getchannel("A").filter(ImageFilter.GaussianBlur(radius=0.35))
    rgba.putalpha(alpha_channel)
    return rgba


def crop_to_visible_artwork(image: Image.Image) -> Image.Image:
    """Crop transparent margins while retaining anti-aliased leaf edges."""
    alpha = image.getchannel("A")
    visible_mask = alpha.point(lambda value: 255 if value >= 48 else 0)
    bounds = visible_mask.getbbox()
    if bounds is None:
        raise ValueError("The source image has no visible artwork.")
    left, top, right, bottom = bounds
    padding = 3
    bounds = (
        max(0, left - padding),
        max(0, top - padding),
        min(image.width, right + padding),
        min(image.height, bottom + padding),
    )
    return image.crop(bounds)


def generate() -> None:
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Source image not found: {SOURCE_PATH}")
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    transparent = remove_white_background(Image.open(SOURCE_PATH))
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    artwork = crop_to_visible_artwork(transparent)
    maximum_size = ICON_SIZE - 16
    scale = maximum_size / max(artwork.size)
    artwork = artwork.resize(
        (round(artwork.width * scale), round(artwork.height * scale)),
        Image.Resampling.LANCZOS,
    )
    offset = ((ICON_SIZE - artwork.width) // 2, (ICON_SIZE - artwork.height) // 2)
    canvas.alpha_composite(artwork, offset)
    canvas.save(PNG_PATH)
    canvas.save(ICO_PATH, format="ICO", sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Generated {PNG_PATH.relative_to(ROOT)} and {ICO_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    generate()
