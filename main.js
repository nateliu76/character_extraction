const jimp = require('jimp');
const imageUtil = require('./extract/utils/imageUtil');
const extractCharLocations = require('./extractCharacterLocations');

function startProcess(coords, error, img) {
  if (error) throw error;
  
  img.greyscale();
  console.log('width: ', img.bitmap.width);
  console.log('height:', img.bitmap.height);
  
  var matrix = imageUtil.imageToMatrix(img);
  
  var locations = 
      coords 
          ? extractCharLocations.getNearCoord(matrix, coords) 
          : extractCharLocations.getAll(matrix);
  
  console.log('\ndone, closing...');
}

function main() {
  var args = process.argv;
  if (args.length <= 2) {
    console.error('No input file.');
    return;
  }
  console.log('reading image...');
  
  // opens the image and starts processing it
  var filename = args[2];
  var coords = args.length === 5 ? [args[3], args[4]] : false;
  jimp.read(filename, startProcess.bind(null, coords));
}

main();
