from PIL import Image, ImageDraw, ImageFont
import os

def generate(text: str="Default", small=False):
    resources_dir = os.path.join(os.path.curdir, 'resources')

    font_path = os.path.join(resources_dir, "Helvetica_Neue_CB.ttf")
    font_size = 45
    font_color = 'White'
    background_color = 'Black'

    image_width = 1280
    image_height = 720

    image = Image.new("RGB", (image_width, image_height), background_color)
    font = ImageFont.truetype(font_path, font_size)

    if small:
        text_box = list(font.getbbox(text))
        image_width = text_box[2] + font_size
        image_height = text_box[3] + font_size - text_box[1]
        image = image.resize((image_width, image_height))

    #Todo: auto text wrap if getlength > image_width when small = False

    x_pos = (image_width) // 2
    y_pos = (image_height) // 2

    draw = ImageDraw.Draw(image)
    draw.text((x_pos, y_pos), text, font=font, fill=font_color, anchor="mm")

    image.save(os.path.join(resources_dir, 'bumper.png'))

if __name__ == '__main__':
    text = input('Enter string to generate: ')
    small = bool(input('Small bumper? (Y/N): ').lower() in ['y', 'yes', 't', 'true', 'please'])
    generate(text, small)
