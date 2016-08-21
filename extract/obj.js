const constants = require('./utils/constants');
const util = require('./utils/util');

module.exports = {
  Bubble: Bubble,
  Subbubble: Subbubble,
  Block: Block,
  CharacterLocation: CharacterLocation,
  Boundary: Boundary
};

function Bubble(matrix, yoffset, xoffset) {
  this.matrix = matrix;
  this.yoffset = yoffset;
  this.xoffset = xoffset;
}

function Subbubble(matrix, yoffset, xoffset) {
  this.matrix = matrix;
  this.yoffset = yoffset;
  this.xoffset = xoffset;
}

function Block(ymin, ymax, xmin, xmax, blackPixCount) {
  this.ymin = ymin;
  this.ymax = ymax;
  this.xmin = xmin;
  this.xmax = xmax;
  
  this.ylen = ymax - ymin + 1;
  this.xlen = xmax - xmin + 1;
  this.ratio = util.blockRatio(ylen, xlen);
  this.blockSize = this.ylen * this.xlen;
  
  this.yoffset = 0;
  this.xoffset = 0;
  
  this.blackPixCount = blackPixCount;
  
  this.downBlock = null;
  this.rightBlock = null;
  this.isCombinedWithOtherBlock = false;
  
  this.isValidBlock = function() {
    var isValidSize = 
        this.blockSize > constants.MIN_BLOCK_SIZE 
            && this.blockSize < constants.MAX_BLOCK_SIZE;
    return isValidSize && util.hasEnoughBlackPixForBlock(this.blackPixCount);
  }
}

// A stripped down version of the Block object
function CharacterLocation(block) {
  this.ymin = block.ymin;
  this.ymax = block.ymax;
  this.xmin = block.xmin;
  this.xmax = block.xmax;
  this.blackPixCount = blackPixCount;
}

function Boundary(ymin, ymax, xmin, xmax) {
  this.ymin = ymin;
  this.ymax = ymax;
  this.xmin = xmin;
  this.xmax = xmax;
}
