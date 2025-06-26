from PIL import Image, ImageDraw
import hashlib
import random

def get_safe_tiles(seed: str):
    hash_val = hashlib.sha256(seed.encode()).hexdigest()
    random.seed(hash_val)
    return random.sample(range(25), 5)

def generate_prediction_image(safe_tiles):
    tile_size = 64
    grid_size = 5
    img = Image.new("RGB", (tile_size * grid_size, tile_size * grid_size), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    for i in range(25):
        row, col = divmod(i, 5)
        x0, y0 = col * tile_size + 5, row * tile_size + 5
        x1, y1 = x0 + tile_size - 10, y0 + tile_size - 10
        if i in safe_tiles:
            draw.rectangle([x0, y0, x1, y1], fill=(0, 255, 100))
        else:
            draw.rectangle([x0, y0, x1, y1], fill=(50, 50, 50))
    return img