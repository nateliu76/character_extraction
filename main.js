const jimp = require('jimp');
const imageUtil = require('./extract/utils/imageUtil');
const extractCharLocations = require('./extractCharacterLocations');

// This is an example of how to use extractCharacterLocations.js.
// Reads in arguments from the command line and does corresponding action.

function startProcess(coords, error, img) {
  if (error) {
    throw error;
  }
  
  img.greyscale();
  console.log('width: ', img.bitmap.width);
  console.log('height:', img.bitmap.height);
  
  var matrix = imageUtil.imageToMatrix(img);
  
  if (coords) {
    // ordered this way for ease of debugging since x, y is the way the 
    // coordinate is formatted in ms paint (as opposed to y, x)
    var xcoord = parseInt(coords[0]);
    var ycoord = parseInt(coords[1]);
    extractCharLocations.getNearCoord(matrix, ycoord, xcoord) 
  } else {
    extractCharLocations.getAll(matrix);
  }
  
  console.log('\ndone, closing...');
}

function main() {
  var args = process.argv;
  if (args.length <= 2) {
    console.error('No input file.');
    return;
  }
  console.log('reading image...');
  
  // open the image and start processing it
  var filename = args[2];
  var coords = args.length === 5 ? [args[3], args[4]] : false;
  jimp.read(filename, startProcess.bind(null, coords));
}

main();
