/* exported config */

var config = {
  // Default language, see i18n.js
  language: 'en',
  // Show help text for images
  showHelp: true,
  // Image overview file or path to the ASU API
  versions: {
    //'FALTER_19.07.4': '../misc/snapshot/overview.json',
    'Falter_tunneldigger': '../misc/falter_tunneldigger.json',
    'Falter_notunnel': '../misc/falter_notunnel.json'
//    'Falter_backbone': '../misc/falter_backbone.json'
    // '19.07.1': '../misc/19.07.1/overview.json',
    // '18.06.7': '../misc/18.06.7/overview.json'
  },
  // Build custom images
  // See https://github.com/aparcar/asu
  //asu_url: 'https://chef.libremesh.org'
};
