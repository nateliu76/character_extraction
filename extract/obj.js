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
  this.ratio = util.blockRatio(this.ylen, this.xlen);
  this.blockSize = this.ylen * this.xlen;
  
  this.yoffset = 0;
  this.xoffset = 0;
  
  this.blackPixCount = blackPixCount;
  
  this.downBlock = false;
  this.rightBlock = false;
  this.isCombinedWithOtherBlock = false;
  
  this.isValidBlock = function() {
    var isValidSize = 
        this.blockSize > constants.MIN_BLOCK_SIZE 
            && this.blockSize < constants.MAX_BLOCK_SIZE;
    return isValidSize && util.hasEnoughBlackPixForBlock(this.blackPixCount);
  }
  
  this.hasBlackPix = function() {
    return this.blackPixCount > 0;
  }
}

// A stripped down version of the Block object
function CharacterLocation(block) {
  this.ymin = block.ymin + block.yoffset;
  this.ymax = block.ymax + block.yoffset;
  this.xmin = block.xmin + block.xoffset;
  this.xmax = block.xmax + block.xoffset;
  this.blackPixCount = block.blackPixCount;
}

function Boundary(ymin, ymax, xmin, xmax) {
  this.ymin = ymin;
  this.ymax = ymax;
  this.xmin = xmin;
  this.xmax = xmax;
}
