from PIL import Image, ImageDraw, ImageChops, ImageFont


# https://stackoverflow.com/a/59804079
def _crop_to_circle(avatar: Image):
    big_size = (128 * 3, 128 * 3)

    mask = Image.new("L", big_size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big_size, fill=255)
    mask = mask.resize((128, 128))
    mask = ImageChops.darker(mask, avatar.split()[-1])
    avatar.putalpha(mask)


def _create_progress_bar():
    im = Image.open("/home/johannes/Documents/Coding/Plyoox/plyoox/src/assets/progress_bar.png").convert("RGB")
    draw = ImageDraw.Draw(im)

    color = (98, 211, 245)
    x, y, diam = 200, -0.5, 60

    draw.ellipse([x, y, x + diam, y + diam], fill=color)
    ImageDraw.floodfill(im, xy=(2, 30), value=color, thresh=10)

    return im.resize((250, 20)).convert("RGBA")


image = Image.open("/home/johannes/Documents/Coding/Plyoox/plyoox/src/assets/level_card.png")
avatar_image = Image.open("/home/johannes/Documents/Coding/Plyoox/plyoox/src/assets/johannes.png")
progress_bar = _create_progress_bar()

avatar_offset = (29, 61)

_crop_to_circle(avatar_image)

font = ImageFont.truetype("/home/johannes/Documents/Coding/Plyoox/plyoox/src/assets/level_font.ttf", 24)

image.paste(avatar_image, avatar_offset, mask=avatar_image)
image.paste(progress_bar, (177, 129), mask=progress_bar)
draw = ImageDraw.Draw(image)
draw.text((175, 100), "JohannesIBK#9220", font=font)

image.show()
