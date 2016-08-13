const processMatrix = require('./processMatrix');
const processBubble = require('./processBubble');
const processSubbubble = require('./processSubbubble');

module.exports = {
  getAll: getAllBlocksInMatrix,
  getNearCoord: getBlocksNearCoord
};

function getAllBlocksInMatrix(matrix) {
  var bubbles = processMatrix.getBubbles(matrix);
  
  // debug print for bubbles
  
  var subbubbles = processBubble.getSubbubbles(bubbles);
  
  // debug print for subbubbles
  
  var blocks = processSubbubble.getBlocks(subbubbles);
  
  // debug print for blocks
  
  return blocks;
}

function getBlocksNearCoord(matrix, coords) {
  var bubble = getBubbleEnclosingCoord(matrix, coords);
  
  var subbubbles = processBubble.getSubbubbles(bubble);
  
  var blocks = processSubbubble.getBlocks(subbubbles);
  
  return blocks;
}
