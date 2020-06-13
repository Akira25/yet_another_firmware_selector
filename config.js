
var config = {
  // Default language, see i18n.js
  language: 'de',
  // Show help text for images
  showHelp: true,
  // Files to get data from
  versions: {
  //'SNAPSHOT': '/api/names/SNAPSHOT', // when using sasu backend
    'hedy-1.0.6': 'misc/names-19.07.1.json',
    'hedy-1.0.6_fw': 'misc/names-19.07.1.json',
    'gonzo-1.1.0': 'misc/names-SNAPSHOT.json',
    'gonzo-1.1.0_fw': 'misc/names-SNAPSHOT.json',
    'OpenWRT 19.07.1': 'misc/names-19.07.1.json'
  },
  // Build custom images
  // See https://github.com/aparcar/asu
  //asu_url: 'https://chef.libremesh.org'
};
