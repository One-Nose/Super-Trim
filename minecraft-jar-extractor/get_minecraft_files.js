const downloadClient = require('minecraft-wrap').downloadClient
const extract = require('extract-zip')
const fs = require('fs-extra')

function getMinecraftFiles (minecraftVersion, temporaryDir, cb, multibar) {
  const jarPath = temporaryDir + '/' + minecraftVersion + '.jar'
  const unzippedFilesDir = temporaryDir + '/' + minecraftVersion
  fs.mkdirpSync(unzippedFilesDir)
  downloadClient(minecraftVersion, jarPath, async (err) => {
    if (err) {
      cb(err)
      return
    }
    try {
      let bar
      await extract(jarPath, { dir: unzippedFilesDir, onEntry: (_, zipfile) => {
        if (multibar && !bar)
          bar = multibar.newBar(
            `extract  [:bar] :percent | Version: ${minecraftVersion} | :current/:total`,
            { width: 50, total: zipfile.entryCount, renderThrottle: 128, clear: true }
          )
        if (bar) bar.tick()
      } })
      cb(null, unzippedFilesDir)
    } catch (err) {
      cb(err)
    }
  })
}

module.exports = getMinecraftFiles
