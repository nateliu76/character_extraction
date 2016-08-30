const constants = require('./extract/utils/constants');
const imageUtil = require('./extract/utils/imageUtil');
const obj = require('./extract/obj');
const processMatrix = require('./extract/processMatrix');
const processBubble = require('./extract/processBubble');
const processSubbubble = require('./extract/processSubbubble');

// API for extracting Chinese character locations in manga/comics
// There are two methods available
// 1. Get all possible character locations in the image matrix
// 2. Get all possible character locations in the text bubble near the 
//    given coordinate

// The image matrix needs to be a greyscale 2D list of pixel values
// See main.js as an example

module.exports = {
  getAll: getAll,
  getNearCoord: getNearCoord
};

// Given an manga image represented in the format of a 2d list of greyscale 
// pixel values, return all possible locations of Chinese characters that do 
// not overlap.
function getAll(matrix) {
  var startTime1 = new Date().getTime();
  var bubbles = processMatrix.getBubbles(matrix);
  
  var startTime2 = new Date().getTime();
  var subbubbles = processBubble.getSubbubbles(bubbles);
  
  var startTime3 = new Date().getTime();
  var charLocations = 
      processSubbubble.getCharacterLocations(matrix, subbubbles);
      
  var endTime = new Date().getTime();
  
  if (constants.IS_DEBUG_PRINT_ALL_IN_FULL_IMG) {
    // log the time it took to process the image
    console.log('\nFull run    : ', (endTime - startTime1) / 1000, 's');
    console.log('Get bubbles   : ', (startTime2 - startTime1) / 1000, 's');
    console.log('Get subbubbles: ', (startTime3 - startTime2) / 1000, 's');
    console.log('Get locations : ', (endTime - startTime3) / 1000, 's\n');
    
    // print/save locations of the bubbles, subbubbles, and character locations
    // in images
    debugPrints(matrix, bubbles, subbubbles, charLocations);
  }
  return charLocations;
}

// Given a 2d list of greyscale pixel values and a coordinate, return all 
// possible locations of Chinese characters in a manga/comic text bubble that
// is near the given coordinates.
function getNearCoord(matrix, ycoord, xcoord) {
  var bubble = processMatrix.getBubbleNearCoord(matrix, ycoord, xcoord);
  var subbubbles = processBubble.getSubbubbles([bubble]);
  var charLocations = 
      processSubbubble.getCharacterLocations(matrix, subbubbles);
  
  if (constants.IS_DEBUG_PRINT_ALL_IN_FULL_IMG) {
    debugPrints(matrix, [bubble], subbubbles, charLocations);
  }
  return charLocations;
}

function debugPrints(matrix, bubbles, subbubbles, charLocations) {
  var filename1 = '0_0_bubbles_in_full_img.png';
  imageUtil.debugPrintBoundariesWithOffsets(matrix, bubbles, filename1);
  
  var filename2 = '0_1_subbubbles_in_full_img.png';
  imageUtil.debugPrintBoundariesWithOffsets(matrix, subbubbles, filename2);
  
  var filename3 = '0_2_char_locations_in_full_img.png';
  imageUtil.debugPrintBoundaries(
      matrix, 
      charLocations, 
      filename3, 
      constants.DEBUG_PRINT_BOUNDARY_MARGIN - constants.CHAR_LOC_MARGIN);
}
