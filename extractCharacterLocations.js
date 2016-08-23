const imageUtil = require('./extract/utils/imageUtil');
const obj = require('./extract/obj');
const processMatrix = require('./extract/processMatrix');
const processBubble = require('./extract/processBubble');
const processSubbubble = require('./extract/processSubbubble');

var isDebugMode = false;

module.exports = {
  getAll: getAll,
  getNearCoord: getNearCoord
};

// Given a 2d list of greyscale pixel values, return all possible locations of
// Chinese characters that do not overlap.
function getAll(matrix) {
  isDebugMode = true;
  
  var startTime = new Date().getTime();
  
  var bubbles = processMatrix.getBubbles(matrix);
  var subbubbles = processBubble.getSubbubbles(bubbles);
  var charLocations = 
      processSubbubble.getCharacterLocations(matrix, subbubbles);
      
  var endTime = new Date().getTime();
  console.log('\nFull run took: ', (endTime - startTime) / 1000, '\n');
  
  if (isDebugMode) {
    debugPrints(matrix, bubbles, subbubbles, charLocations);
  }
  return charLocations;
}

// Given a 2d list of greyscale pixel values and a coordinate, return all 
// possible locations of Chinese characters in a manga/comic text bubble that
// encloses the given coordinates. The locations do not overlap with each other.
function getNearCoord(matrix, coords) {
  isDebugMode = true;
  
  var bubble = processMatrix.getBubbleEnclosingCoord(matrix, coords);
  var subbubbles = processBubble.getSubbubbles([bubble]);
  var charLocations = 
      processSubbubble.getCharacterLocations(matrix, subbubbles);
  
  if (isDebugMode) {
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
  imageUtil.debugPrintBoundaries(matrix, charLocations, filename3);
}