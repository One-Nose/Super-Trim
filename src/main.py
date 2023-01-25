from json import load
from os import mkdir
from os.path import join
from shutil import rmtree

from PIL import Image


def color_palette(texture: str) -> Image:
    with Image.open(texture) as image:
        data = image.convert('RGBA').getdata()
        data = set(filter(lambda p: p[3] > 0, data))
        data = sorted(data, key=sum, reverse=True)

        if len(data) == 1:
            data = list(data) * 8

        while len(data) > 8:
            pixels = min(zip(data, data[2:]), key=lambda ps: sum(ps[0]) - sum(ps[1]))
            index = data.index(pixels[0]) + 1
            data.pop(index)

        while len(data) < 8:
            pixels = max(zip(data, data[1:]), key=lambda ps: sum(ps[0]) - sum(ps[1]))
            index = data.index(pixels[1])
            data.insert(index, tuple(c[1] + (c[0]-c[1]) // 2 for c in zip(*pixels)))

        result = Image.new('RGBA', (8, 1))
        result.putdata(data)
        return result


def create_color_palettes(path: str) -> None:
    rmtree(path)
    mkdir(path)

    with open('items.json') as file:
        items = load(file)

    for item in items:
        if item['texture'] is not None:
            color_palette(texture_path(item['texture'])).save(join(path, item['name'] + '.png'))


def texture_path(namespaced_path: str):
    try:
        namespace, path = namespaced_path.split(':')
    except ValueError:
        namespace, path = 'minecraft', namespaced_path
    return join('..', namespace, 'textures', path + '.png')


if __name__ == '__main__':
    create_color_palettes('../color_palettes')
