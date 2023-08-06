"""A scripts that generates the data pack and resource pack"""

from contextlib import suppress
from json import dump, load
from os import makedirs, remove
from pathlib import Path
from shutil import copyfile, make_archive, rmtree
from sys import argv
from typing import Iterable, Sequence, TypedDict

from PIL import Image
from tqdm import tqdm

ROOT = Path.cwd()

SRC_ROOT = ROOT / 'src'
EXTRACTOR_ROOT = ROOT / 'extractor'
DATA_ROOT = EXTRACTOR_ROOT / 'minecraft_extracted_data'
OUT_ROOT = EXTRACTOR_ROOT / 'out'


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


class MCMetaPack(TypedDict, total=False):
    """The 'pack' field of a pack.mcmeta file"""

    pack_format: int
    description: str
    supported_formats: int | list[int] | dict[str, int]


def color_palette(texture: Path) -> Image.Image:
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


def colors(texture: Path) -> set[tuple[int, int, int, int]]:
    """Gets all unique colors in a given texture"""

    with Image.open(texture) as image:
        data: Sequence[tuple[int, int, int, int]] = image.convert('RGBA').getdata()
    return set(color for color in data if color[3] > 0)


def create_atlas(path: Path, atlas_name: str, version: str) -> None:
    """
    Copies a source from an atlas from the minecraft version folder
    and saves an updated version of the atlas in the given path
    """

    with (
        DATA_ROOT / version / 'assets' / 'minecraft' / 'atlases' / f'{atlas_name}.json'
    ).open(encoding='UTF-8') as file:
        atlas: dict[str, list[AtlasSource]] = load(file)

    atlas['sources'][0]['permutations'] = {
        item['name']: 'super_trim:trims/color_palettes/' + item['name']
        for item in items(version)
    }

    with path.open('x', encoding='UTF-8') as file:
        dump(atlas, file, indent=2)


def create_color_palettes(path: Path, version: str) -> None:
    """Creates and saves all color palettes in the given path"""

    refresh_dir(path)

    for item in items(version):
        color_palette(texture_path(item['texture'], version)).save(
            path / f'{item["name"]}.png'
        )


def create_datapack(
    path: Path,
    version: str,
    pack_format: int,
    supported_formats: tuple[int, int] | None = None,
) -> None:
    """Generates the data pack in the specified path"""

    with tqdm(
        total=6,
        bar_format='{l_bar}{bar:50}| {n_fmt}/{total_fmt}{postfix}',
        postfix='Preparing datapack...',
    ) as pbar:
        refresh_dir(path)

        pbar.postfix = 'Creating pack.mcmeta...'
        pbar.update()
        create_mcmeta(
            path,
            'Enables all items as armor trimming materials',
            pack_format,
            supported_formats,
        )

        pbar.postfix = 'Creating trim_materials.json...'
        pbar.update()
        makedirs(path / 'data' / 'minecraft' / 'tags' / 'items')
        create_tag(
            path / 'data' / 'minecraft' / 'tags' / 'items' / 'trim_materials.json',
            version,
        )

        pbar.postfix = 'Creating materials...'
        pbar.update()
        makedirs(path / 'data' / 'super_trim' / 'trim_material')
        for item in items(version):
            create_material(
                path / 'data' / 'super_trim' / 'trim_material', item, version
            )

        pbar.postfix = 'Creating pack.png...'
        pbar.update()
        copyfile(ROOT / 'pack.png', path / 'pack.png')

        pbar.postfix = 'Creating Super Trim.zip...'
        pbar.update()
        with suppress(FileNotFoundError):
            remove(ROOT / 'Super-Trim.zip')
        make_archive(str(ROOT / 'Super-Trim'), 'zip', ROOT / 'datapack')

        pbar.postfix = 'Datapack ready'
        pbar.update()


def create_lang(path: Path, version: str) -> None:
    """Creates the lang file and saves it in the given path"""

    with (DATA_ROOT / version / 'assets' / 'minecraft' / 'lang' / 'en_us.json').open(
        encoding='UTF-8'
    ) as file:
        lang = load(file)

    result = {}

    for item in items(version):
        try:
            display_name = lang['item.minecraft.' + item['name']]
        except KeyError:
            if item['name'].endswith('_smithing_template'):
                display_name = 'Smithing Template'
            else:
                display_name = lang['block.minecraft.' + item['name']]

        result['trim_material.minecraft.' + item['name']] = display_name + ' Material'

    with path.open('x', encoding='UTF-8') as file:
        dump(result, file, indent=2)


def create_material(path: Path, item: Item, version: str) -> None:
    """Creates a JSON material definition and saves it at the given directory"""

    rgba = zip(*colors(texture_path(item['texture'], version)))
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

    with (path / f'{item["name"]}.json').open('x', encoding='UTF-8') as file:
        dump(material, file, indent=2)


def create_mcmeta(
    path: Path,
    description: str,
    pack_format: int,
    supported_formats: tuple[int, int] | None = None,
) -> None:
    """Saves a pack.mcmeta file at the given directory"""

    with (path / 'pack.mcmeta').open('x', encoding='UTF-8') as file:
        pack: MCMetaPack = {'description': description, 'pack_format': pack_format}
        if supported_formats:
            pack['supported_formats'] = {
                'min_inclusive': supported_formats[0],
                'max_inclusive': supported_formats[1],
            }
        dump({'pack': pack}, file, indent=2)


def create_resourcepack(
    path: Path,
    version: str,
    pack_format: int,
    supported_formats: tuple[int, int] | None = None,
) -> None:
    """Generates the resource pack"""

    with tqdm(
        total=7,
        bar_format='{l_bar}{bar:50}| {n_fmt}/{total_fmt}{postfix}',
        postfix='Preparing resource pack...',
    ) as pbar:
        refresh_dir(path)

        pbar.postfix = 'Creating pack.mcmeta...'
        pbar.update()
        create_mcmeta(
            path,
            'Resource pack for the Super Trim data pack',
            pack_format,
            supported_formats,
        )

        pbar.postfix = 'Creating armor_trims.json...'
        pbar.update()
        makedirs(path / 'assets' / 'minecraft' / 'atlases')
        create_atlas(
            path / 'assets' / 'minecraft' / 'atlases' / 'armor_trims.json',
            'armor_trims',
            version,
        )

        pbar.postfix = 'Creating color palettes...'
        pbar.update()
        makedirs(
            path / 'assets' / 'super_trim' / 'textures' / 'trims' / 'color_palettes'
        )
        create_color_palettes(
            path / 'assets' / 'super_trim' / 'textures' / 'trims' / 'color_palettes',
            version,
        )

        pbar.postfix = 'Creating en_us.json...'
        pbar.update()
        makedirs(path / 'assets' / 'minecraft' / 'lang')
        create_lang(path / 'assets' / 'minecraft' / 'lang' / 'en_us.json', version)

        pbar.postfix = 'Creating pack.png...'
        pbar.update()
        copyfile(ROOT / 'pack.png', path / 'pack.png')

        pbar.postfix = 'Creating Super-Trim-Resources.zip...'
        pbar.update()
        with suppress(FileNotFoundError):
            remove(ROOT / 'Super-Trim-Resources.zip')
        make_archive(str(ROOT / 'Super-Trim-Resources'), 'zip', ROOT / 'resourcepack')

        pbar.postfix = 'Resource pack ready'
        pbar.update()


def create_tag(path: Path, version: str) -> None:
    """Creates a tag file for all the new materials at the given path"""

    tag = {'values': ['minecraft:' + item['name'] for item in items(version)]}

    with path.open('x', encoding='UTF-8') as file:
        dump(tag, file, indent=2)


def items(version: str) -> Iterable[Item]:
    """Returns all items in a game version that aren't trim materials in vanilla"""

    with (
        DATA_ROOT
        / version
        / 'data'
        / 'minecraft'
        / 'tags'
        / 'items'
        / 'trim_materials.json'
    ).open(encoding='UTF-8') as file:
        blacklist: list[str] = load(file)['values']
    blacklist.append('minecraft:air')

    with (OUT_ROOT / version / 'items_textures.json').open(encoding='UTF-8') as file:
        item_list: list[Item] = load(file)
        return (
            item for item in item_list if 'minecraft:' + item['name'] not in blacklist
        )


def refresh_dir(path: Path) -> None:
    """Clears a directory"""

    rmtree(path, ignore_errors=True)
    path.mkdir()


def texture_path(namespaced_path: str, version: str) -> Path:
    """Gets an actual path from a namespaced texture path"""

    try:
        path = namespaced_path.split(':')[1]
    except IndexError:
        path = namespaced_path
    path = Path(path + '.png')

    if path.parts[0] == 'block':
        path = Path('blocks', *path.parts[1:])

    return OUT_ROOT / version / path


if __name__ == '__main__':
    create_datapack(ROOT / 'datapack', argv[1], 15, (15, 16))
    create_resourcepack(ROOT / 'resourcepack', argv[1], 15, (15, 16))
