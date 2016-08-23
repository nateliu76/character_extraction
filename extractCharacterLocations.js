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
  var bubbles = processMatrix.getBubbles(matrix);
  var subbubbles = processBubble.getSubbubbles(bubbles);
  var charLocations = 
      processSubbubble.getCharacterLocations(matrix, subbubbles);
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
  
  // debug print blocks in full image
  if (isDebugMode) {
    var filename1 = '0_bubbles_in_full_img.png';
    imageUtil.debugPrintBoundariesWithOffsets(matrix, [bubble], filename1);
    
    var filename2 = '0_subbubbles_in_full_img.png';
    imageUtil.debugPrintBoundariesWithOffsets(matrix, subbubbles, filename2);
    
    var filename3 = '0_char_locations_in_full_img.png';
    imageUtil.debugPrintBoundaries(matrix, charLocations, filename3);
  }
  return charLocations;
}
