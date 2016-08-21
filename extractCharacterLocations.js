const processMatrix = require('./extract/processMatrix');
const processBubble = require('./extract/processBubble');
const processSubbubble = require('./extract/processSubbubble');

module.exports = {
  getAll: getAll,
  getNearCoord: getNearCoord
};

// Given a 2d list of greyscale pixel values, return all possible locations of
// Chinese characters that do not overlap.
function getAll(matrix) {
  var bubbles = processMatrix.getBubbles(matrix);
  var subbubbles = processBubble.getSubbubbles(bubbles);
  var charLocations = processSubbubble.getCharacterLocations(subbubbles);
  return charLocations;
}

// Given a 2d list of greyscale pixel values and a coordinate, return all 
// possible locations of Chinese characters in a manga/comic text bubble that
// encloses the given coordinates. The locations do not overlap with each other.
function getNearCoord(matrix, coords) {
  var bubble = processMatrix.getBubbleEnclosingCoord(matrix, coords);
  var subbubbles = processBubble.getSubbubbles([bubble]);
  var charLocations = processSubbubble.getCharacterLocations(subbubbles);
  return charLocations;
}
