from json import dump, load
from os import makedirs, mkdir
from os.path import join
from shutil import rmtree, copyfile
from typing import Iterable

from PIL import Image


def color_palette(texture: str) -> Image:
    data = sorted(colors(texture), key=lambda c: sum(c), reverse=True)

    if len(data) == 1:
        data = list(data) * 8

    while len(data) > 8:
        pixels = min(zip(data, data[2:]), key=lambda ps: sum(ps[0]) - sum(ps[1]))
        index = data.index(pixels[0]) + 1
        data.pop(index)

    while len(data) < 8:
        pixels = max(zip(data, data[1:]), key=lambda ps: sum(ps[0]) - sum(ps[1]))
        index = data.index(pixels[1])
        data.insert(index, tuple(c[1] + (c[0]-c[1]) // 2 for c in zip(pixels[0], pixels[1])))

    result = Image.new('RGBA', (8, 1))
    result.putdata(data)
    return result


def colors(texture: str) -> set[tuple[int]]:
    with Image.open(texture) as image:
        data = image.convert('RGBA').getdata()
    return set(filter(lambda p: p[3] > 0, data))


def create_atlas(path: str) -> None:
    with open('../minecraft/atlases/armor_trims.json') as file:
        atlas = load(file)

    permutations = atlas['sources'][0]['permutations']
    for item in items():
        permutations[item['name']] = f"super_trim:trims/color_palettes/{item['name']}"

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
    rgba = tuple(map(lambda c: sum(c) // len(c), rgba))

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
    create_atlas(join(path, 'assets/minecraft/atlases/armor_trims.json'))

    print('Creating color palettes...')
    makedirs(join(path, 'assets/super_trim/textures/trims/color_palettes'))
    create_color_palettes(join(path, 'assets/super_trim/textures/trims/color_palettes'))

    print('Creating en_us.json...')
    makedirs(join(path, 'assets/minecraft/lang'))
    create_lang(join(path, 'assets/minecraft/lang', 'en_us.json'))

    print('Creating pack.png...')
    copyfile('../pack.png', join(path, 'pack.png'))

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
