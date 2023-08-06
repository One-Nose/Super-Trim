"""A scripts that generates the data pack and resource pack"""

from contextlib import suppress
from json import dump, load
from os import makedirs, mkdir, remove
from os.path import abspath, join
from shutil import copyfile, make_archive, rmtree
from typing import Iterable, Sequence, TypedDict

from PIL import Image
from tqdm import tqdm

ROOT = abspath('.')

MINECRAFT_ROOT = join(ROOT, 'minecraft')
SRC_ROOT = join(ROOT, 'src')


class AtlasSource(TypedDict, total=False):
    """A source within an atlas definition"""

    type: str
    textures: list[str]
    palette_key: str
    permutations: dict[str, str]


class Item(TypedDict):
    """An item from items.json"""

    name: str
    model: str
    texture: str


def color_palette(texture: str) -> Image.Image:
    """Creates an 8-pixels color palette of a given texture"""

    data = sorted(colors(texture), key=sum, reverse=True)

    if len(data) == 1:
        data *= 8

    while len(data) > 8:
        pixels = min(
            zip(data, data[2:]), key=lambda colors: sum(colors[0]) - sum(colors[1])
        )
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
    """Gets all unique colors in a given texture"""

    with Image.open(texture) as image:
        data: Sequence[tuple[int, int, int, int]] = image.convert('RGBA').getdata()
    return set(color for color in data if color[3] > 0)


def create_atlas(path: str, atlas_name: str, index: int) -> None:
    """
    Copies a source from an atlas from the minecraft folder
    and saves an updated version of the atlas in the given path
    """

    with open(
        join(MINECRAFT_ROOT, 'atlases', atlas_name + '.json'), encoding='UTF-8'
    ) as file:
        atlas: dict[str, list[AtlasSource]] = load(file)

    atlas['sources'][index]['permutations'] = {
        item['name']: 'super_trim:trims/color_palettes/' + item['name']
        for item in items()
    }

    with open(path, 'x', encoding='UTF-8') as file:
        dump(atlas, file, indent=2)


def create_color_palettes(path: str) -> None:
    """Creates and saves all color palettes in the given path"""

    refresh_dir(path)

    for item in items():
        color_palette(texture_path(item['texture'])).save(
            join(path, item['name'] + '.png')
        )


def create_datapack(path: str) -> None:
    """Generates the data pack in the specified path"""

    with tqdm(
        total=6,
        bar_format='{l_bar}{bar:50}| {n_fmt}/{total_fmt}{postfix}',
        postfix='Preparing datapack...',
    ) as pbar:
        refresh_dir(path)

        pbar.update()
        pbar.postfix = 'Creating pack.mcmeta...'
        create_mcmeta(path, 'Enables all items as armor trimming materials', 11)

        pbar.update()
        pbar.postfix = 'Creating trim_materials.json...'
        makedirs(join(path, 'data', 'minecraft', 'tags', 'items'))
        create_tag(
            join(path, 'data', 'minecraft', 'tags', 'items', 'trim_materials.json')
        )

        pbar.update()
        pbar.postfix = 'Creating materials...'
        makedirs(join(path, 'data', 'super_trim', 'trim_material'))
        for item in items():
            create_material(join(path, 'data', 'super_trim', 'trim_material'), item)

        pbar.update()
        pbar.postfix = 'Creating pack.png...'
        copyfile(join(ROOT, 'pack.png'), join(path, 'pack.png'))

        pbar.update()
        pbar.postfix = 'Creating Super Trim.zip...'
        with suppress(FileNotFoundError):
            remove(join(ROOT, 'Super Trim.zip'))
        make_archive(join(ROOT, 'Super Trim'), 'zip', join(ROOT, 'datapack'))

        pbar.update()
        pbar.postfix = 'Datapack ready'


def create_lang(path: str) -> None:
    """Creates the lang file and saves it in the given path"""

    with open(join(MINECRAFT_ROOT, 'lang', 'en_us.json'), encoding='UTF-8') as file:
        lang = load(file)

    result = {}

    for item in items():
        try:
            display_name = lang['item.minecraft.' + item['name']]
        except KeyError:
            if item['name'].endswith('_smithing_template'):
                display_name = 'Smithing Template'
            else:
                display_name = lang['block.minecraft.' + item['name']]

        result['trim_material.minecraft.' + item['name']] = display_name + ' Material'

    with open(path, 'x', encoding='UTF-8') as file:
        dump(result, file, indent=2)


def create_material(path: str, item: Item) -> None:
    """Creates a JSON material definition and saves it at the given directory"""

    rgba = zip(*colors(texture_path(item['texture'])))
    rgba = tuple(sum(color_part) // len(color_part) for color_part in rgba)

    material = {
        'asset_name': item['name'],
        'description': {
            'color': f'#{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}',
            'translate': 'trim_material.minecraft.' + item['name'],
        },
        'ingredient': 'minecraft:' + item['name'],
        'item_model_index': 1.0,
    }

    with open(join(path, item['name'] + '.json'), 'x', encoding='UTF-8') as file:
        dump(material, file, indent=2)


def create_mcmeta(path: str, description: str, pack_format: int) -> None:
    """Saves a pack.mcmeta file at the given directory"""

    with open(join(path, 'pack.mcmeta'), 'x', encoding='UTF-8') as file:
        dump(
            {'pack': {'description': description, 'pack_format': pack_format}},
            file,
            indent=2,
        )


def create_resourcepack(path: str) -> None:
    """Generates the resource pack"""

    with tqdm(
        total=7,
        bar_format='{l_bar}{bar:50}| {n_fmt}/{total_fmt}{postfix}',
        postfix='Preparing resource pack...',
    ) as pbar:
        refresh_dir(path)

        pbar.update()
        pbar.postfix = 'Creating pack.mcmeta...'
        create_mcmeta(path, 'Resource pack for the Super Trim data pack', 12)

        pbar.update()
        pbar.postfix = 'Creating armor_trims.json...'
        makedirs(join(path, 'assets', 'minecraft', 'atlases'))
        create_atlas(
            join(path, 'assets', 'minecraft', 'atlases', 'armor_trims.json'),
            'armor_trims',
            0,
        )

        pbar.update()
        pbar.postfix = 'Creating color palettes...'
        makedirs(
            join(path, 'assets', 'super_trim', 'textures', 'trims', 'color_palettes')
        )
        create_color_palettes(
            join(path, 'assets', 'super_trim', 'textures', 'trims', 'color_palettes')
        )

        pbar.update()
        pbar.postfix = 'Creating en_us.json...'
        makedirs(join(path, 'assets', 'minecraft', 'lang'))
        create_lang(join(path, 'assets', 'minecraft', 'lang', 'en_us.json'))

        pbar.update()
        pbar.postfix = 'Creating pack.png...'
        copyfile(join(ROOT, 'pack.png'), join(path, 'pack.png'))

        pbar.update()
        pbar.postfix = 'Creating Super Trim - Resources.zip...'
        with suppress(FileNotFoundError):
            remove(join(ROOT, 'Super Trim - Resources.zip'))
        make_archive(
            join(ROOT, 'Super Trim - Resources'), 'zip', join(ROOT, 'resourcepack')
        )

        pbar.update()
        pbar.postfix = 'Resource pack ready'


def create_tag(path: str) -> None:
    """Creates a tag file for all the new materials at the given path"""

    tag = {'values': ['minecraft:' + item['name'] for item in items()]}

    with open(path, 'x', encoding='UTF-8') as file:
        dump(tag, file, indent=2)


def items() -> Iterable[Item]:
    """Returns all items in the game that aren't trim materials in vanilla"""

    with open(
        join(
            ROOT,
            'update_1_20',
            'data',
            'minecraft',
            'tags',
            'items',
            'trim_materials.json',
        ),
        encoding='UTF-8',
    ) as file:
        blacklist: list[str] = load(file)['values']
    blacklist.append('minecraft:air')

    with open(join(SRC_ROOT, 'items.json'), encoding='UTF-8') as file:
        item_list: list[Item] = load(file)
        return (
            item for item in item_list if 'minecraft:' + item['name'] not in blacklist
        )


def refresh_dir(path: str) -> None:
    """Clears a directory"""

    rmtree(path, ignore_errors=True)
    mkdir(path)


def texture_path(namespaced_path: str) -> str:
    """Gets an actual path from a namespaced texture path"""

    try:
        namespace, path = namespaced_path.split(':')
    except ValueError:
        namespace, path = 'minecraft', namespaced_path
    return join(ROOT, namespace, 'textures', path + '.png')


if __name__ == '__main__':
    create_datapack(join(ROOT, 'datapack'))
    create_resourcepack(join(ROOT, 'resourcepack'))
