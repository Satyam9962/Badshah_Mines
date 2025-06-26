from PIL import Image, ImageDraw
import random

def get_safe_tiles(seed):
    random.seed(seed)
    return set(random.sample(range(25), 5))

def generate_prediction_image(safe_tiles):
    img = Image.new("RGB", (320, 320), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)
    for i in range(25):
        x = (i % 5) * 64
        y = (i // 5) * 64
        if i in safe_tiles:
            draw.rectangle([x+4, y+4, x+60, y+60], fill="green")
        else:
            draw.rectangle([x+4, y+4, x+60, y+60], outline="gray")
    return img