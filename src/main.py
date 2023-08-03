"""A scripts that generates the data pack and resource pack"""

from contextlib import suppress
from json import dump, load
from os import makedirs, mkdir, remove
from os.path import join
from shutil import copyfile, make_archive, rmtree
from typing import Iterable

from PIL import Image


def color_palette(texture: str) -> Image:
    data = sorted(colors(texture), key=lambda c: sum(c), reverse=True)

    if len(data) == 1:
        data *= 8

    while len(data) > 8:
        pixels = min(zip(data, data[2:]), key=lambda ps: sum(ps[0]) - sum(ps[1]))
        index = data.index(pixels[0]) + 1
        data.pop(index)

    while len(data) < 8:
        pixels = max(
            zip(data, data[1:]), key=lambda colors: sum(colors[0]) - sum(colors[1])
        )
        index = data.index(pixels[1])
        data.insert(index, tuple(sum(color_part) // 2 for color_part in zip(*pixels)))

    result = Image.new('RGBA', (8, 1))
    result.putdata(data)
    return result


def colors(texture: str) -> set[tuple[int, int, int, int]]:
    with Image.open(texture) as image:
        data = image.convert('RGBA').getdata()
    return set(color for color in data if color[3] > 0)


def create_atlas(path: str, atlas_name: str, index: int) -> None:
    with open(f'../minecraft/atlases/{atlas_name}.json') as file:
        atlas = load(file)

    atlas['sources'][index]['permutations'] = {
        item['name']: 'super_trim:trims/color_palettes/' + item['name']
        for item in items()
    }

    with open(path, 'x') as file:
        dump(atlas, file, indent=2)


def create_color_palettes(path: str) -> None:
    refresh_dir(path)

    for item in items():
        if item['texture'] is not None:
            color_palette(texture_path(item['texture'])).save(join(path, f"{item['name']}.png"))


def create_datapack(path: str) -> None:
    print('Preparing datapack...')
    refresh_dir(path)

    print('Creating pack.mcmeta...')
    create_mcmeta(path, 'Enables all items as armor trimming materials', 11)

    print('Creating trim_materials.json...')
    makedirs(join(path, 'data/minecraft/tags/items'))
    create_tag(join(path, 'data/minecraft/tags/items/trim_materials.json'))

    print('Creating materials...')
    makedirs(join(path, 'data/super_trim/trim_material'))
    for item in items():
        create_material(join(path, 'data/super_trim/trim_material'), item)

    print('Creating pack.png...')
    copyfile('../pack.png', join(path, 'pack.png'))

    print('Creating Super Trim.zip...')
    with suppress(FileNotFoundError):
        remove('../Super Trim.zip')
    make_archive('../Super Trim', 'zip', '../datapack')

    print('Datapack ready')


def create_lang(path: str) -> None:
    with open('../minecraft/lang/en_us.json') as file:
        lang = load(file)

    result = {}

    for item in items():
        try:
            display_name = lang[f"item.minecraft.{item['name']}"]
        except KeyError:
            if item['name'].endswith('_smithing_template'):
                display_name = 'Smithing Template'
            else:
                display_name = lang[f"block.minecraft.{item['name']}"]

        result[f"trim_material.minecraft.{item['name']}"] = f'{display_name} Material'
    
    with open(path, 'x') as file:
        dump(result, file, indent=2)


def create_material(path: str, item: dict[str, str]) -> None:
    rgba = zip(*colors(texture_path(item['texture'])))
    rgba = tuple(sum(color_part) // len(color_part) for color_part in rgba)

    material = {
        'asset_name': item['name'],
        'description': {
            'color': f'#{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}',
            'translate': f"trim_material.minecraft.{item['name']}"
        },
        'ingredient': f"minecraft:{item['name']}",
        'item_model_index': 1.0
    }

    with open(join(path, f"{item['name']}.json"), 'x') as file:
        dump(material, file, indent=2)


def create_mcmeta(path: str, description: str, pack_format: int) -> None:
    with open(join(path, 'pack.mcmeta'), 'x') as file:
        dump({
            'pack': {
                'description': description,
                'pack_format': pack_format
            }
        }, file, indent=2)


def create_resourcepack(path: str) -> None:
    print('Preparing resource pack...')
    refresh_dir(path)

    print('Creating pack.mcmeta...')
    create_mcmeta(path, 'Resource pack for the Super Trim data pack', 12)

    print('Creating armor_trims.json...')
    makedirs(join(path, 'assets/minecraft/atlases'))
    create_atlas(join(path, 'assets/minecraft/atlases/armor_trims.json'), 'armor_trims', 0)

    print('Creating color palettes...')
    makedirs(join(path, 'assets/super_trim/textures/trims/color_palettes'))
    create_color_palettes(join(path, 'assets/super_trim/textures/trims/color_palettes'))

    print('Creating en_us.json...')
    makedirs(join(path, 'assets/minecraft/lang'))
    create_lang(join(path, 'assets/minecraft/lang', 'en_us.json'))

    print('Creating pack.png...')
    copyfile('../pack.png', join(path, 'pack.png'))

    print('Creating Super Trim - Resources.zip...')
    with suppress(FileNotFoundError):
        remove('../Super Trim - Resources.zip')
    make_archive('../Super Trim - Resources', 'zip', '../resourcepack')

    print('Resource pack ready')


def create_tag(path: str) -> None:
    tag = {'values': []}
    for item in items():
        tag['values'].append(f"minecraft:{item['name']}")
    
    with open(path, 'x') as file:
        dump(tag, file, indent=2)


def items() -> Iterable[dict[str, str]]:
    with open('../update_1_20/data/minecraft/tags/items/trim_materials.json') as file:
        blacklist: list[str] = load(file)['values']
    blacklist.append('minecraft:air')

    with open('items.json') as file:
        return filter(lambda i: f"minecraft:{i['name']}" not in blacklist, load(file))


def refresh_dir(path: str) -> None:
    rmtree(path, ignore_errors=True)
    mkdir(path)


def texture_path(namespaced_path: str):
    try:
        namespace, path = namespaced_path.split(':')
    except ValueError:
        namespace, path = 'minecraft', namespaced_path
    return join('..', namespace, 'textures', f'{path}.png')


if __name__ == '__main__':
    create_datapack('../datapack')
    create_resourcepack('../resourcepack')
