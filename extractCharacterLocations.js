const processMatrix = require('./extract/processMatrix');
const processBubble = require('./extract/processBubble');
const processSubbubble = require('./extract/processSubbubble');

module.exports = {
  getAll: getAllBlocksInMatrix,
  getNearCoord: getBlocksNearCoord
};

/**
 * 
 * 
 */
function getAllBlocksInMatrix(matrix) {
  var bubbles = processMatrix.getBubbles(matrix);
  var subbubbles = processBubble.getSubbubbles(bubbles);
  var blocks = processSubbubble.getBlocks(subbubbles);
  return blocks;
}

function getBlocksNearCoord(matrix, coords) {
  var bubble = processMatrix.getBubbleEnclosingCoord(matrix, coords);
  var subbubbles = processBubble.getSubbubbles(bubble);
  var blocks = processSubbubble.getBlocks(subbubbles);
  return blocks;
}
