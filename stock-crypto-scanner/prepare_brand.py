"""Create web-sized branding assets from the supplied original logo (requires Pillow locally)."""
import argparse
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw


def prepare(source, destination):
    image = Image.open(source).convert('RGBA')
    if image.getchannel('A').getextrema() == (255, 255):
        # Remove only the connected black background, retaining interior shading.
        r, g, b, alpha = image.split()
        mask = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v <= 10 else 0)
        for corner in [(0, 0), (image.width-1, 0), (0, image.height-1), (image.width-1, image.height-1)]:
            if mask.getpixel(corner) == 255:
                ImageDraw.floodfill(mask, corner, 128)
        image.putalpha(ImageChops.multiply(alpha, mask.point(lambda v: 0 if v == 128 else 255)))
    r, g, b, alpha = image.split()
    visible = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > 25 else 0)
    bounds = ImageChops.multiply(alpha, visible).getbbox()
    if not bounds:
        raise ValueError('Logo is empty')
    bounds = (max(0,bounds[0]-3),max(0,bounds[1]-3),min(image.width,bounds[2]+3),min(image.height,bounds[3]+3))
    image = image.crop(bounds)
    logo = image.copy()
    logo.thumbnail((1000, 400), Image.Resampling.LANCZOS)
    logo.save(destination/'marketscope-logo.png', optimize=True)
    icon = image.crop((0, 0, round(image.width*.30), image.height))
    icon = icon.crop(icon.getchannel('A').getbbox())
    for filename, size in [('marketscope-icon.png', 256), ('favicon.png', 64)]:
        canvas = Image.new('RGBA', (size, size))
        scaled = icon.copy()
        scaled.thumbnail((round(size*.92), round(size*.92)), Image.Resampling.LANCZOS)
        canvas.alpha_composite(scaled, ((size-scaled.width)//2, (size-scaled.height)//2))
        canvas.save(destination/filename, optimize=True)
    print(f'Prepared logo {logo.size}, icon and favicon from the original artwork.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--destination', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    prepare(args.source, args.destination)
