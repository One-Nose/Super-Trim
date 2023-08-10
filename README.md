# Super-Trim

A Minecraft datapack that enables all items as valid armor trimming materials.

A new update recently allowed us to trim armor using ten different materials. Using this data pack, you will be able to use ANY ITEM YOU WANT!

### Credit

This project uses an abridged version of [minecraft-jar-extractor](https://github.com/PrismarineJS/minecraft-jar-extractor).

## Usage instructions

In order to use this data pack, first go to the [releases](https://github.com/One-Nose/Super-Trim/releases) page and choose your desired version. It is recommended to choose the latest version that supports your desired Minecraft version.

> If you're using a earlier version that Super Trim 2.0.0,you must enable the experimental data pack first. You can enable the experimental data pack when creating a new world from the **Data Packs** menu.

Then, add the data pack (`Super-Trims.zip`) like any other data pack ([instructions](https://www.planetminecraft.com/blog/how-to-download-and-install-minecraft-data-packs/)). **You also have to download and use the resource pack (`Super-Trim-Resources.zip`), otherwise the data pack won't work.** Then, pick up a smithing table, an armor trimming smithing template, any supported piece of armor and any item you want and trim your armor (see the picture)!

## Limitations (aka bugs I didn't bother to solve)

-   Armor trimmed using the data pack has a purple trim texture in the inventory instead of its actual color.
-   Shift+click in the smithing table UI sometimes doesn't work.
-   Certain items such as spawn eggs and leaves trim the armor inaccurately.
-   Blocks with different sides only use one side to determine how the trim would look.
-   Dark materials make unreadable descriptions.

### Building

To build this data pack yourself, you'll need NodeJS and Python installed. First extract the desired minecraft version:

```
cd extractor
npm install
node image_names.js <version>
cd ..
```

Then, execute the main file:

```
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python src/main.py [<version>]
```
