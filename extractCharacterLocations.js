const processMatrix = require('./extract/processMatrix');
const processBubble = require('./extract/processBubble');
const processSubbubble = require('./extract/processSubbubble');

module.exports = {
  getAll: getAll,
  getNearCoord: getNearCoord
};

function getAll(matrix) {
  var bubbles = processMatrix.getBubbles(matrix);
  var subbubbles = processBubble.getSubbubbles(bubbles);
  var charLocations = processSubbubble.getCharacterLocations(subbubbles);
  return charLocations;
}

function getNearCoord(matrix, coords) {
  var bubble = processMatrix.getBubbleEnclosingCoord(matrix, coords);
  var subbubbles = processBubble.getSubbubbles([bubble]);
  var charLocations = processSubbubble.getCharacterLocations(subbubbles);
  return charLocations;
}
