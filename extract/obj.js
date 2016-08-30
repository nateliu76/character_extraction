const constants = require('./utils/constants');
const util = require('./utils/util');

const MARGIN = 2;

// Container objects used

module.exports = {
  Bubble: Bubble,
  Subbubble: Subbubble,
  Block: Block,
  CharacterLocation: CharacterLocation,
  Boundary: Boundary
};

// offsets are the offsets of the bubble's matrix in relation to the image
// matrix
function Bubble(matrix, yoffset, xoffset) {
  this.matrix = matrix;
  this.yoffset = yoffset;
  this.xoffset = xoffset;
}

// offsets are the offsets of the subbubble's matrix in relation to the image
// matrix
function Subbubble(matrix, yoffset, xoffset) {
  this.matrix = matrix;
  this.yoffset = yoffset;
  this.xoffset = xoffset;
}

// 
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
  
  this.hasBlackPix = function() {
    return this.blackPixCount > 0;
  }
}

// A stripped down version of the Block object, with added margins
function CharacterLocation(block, matrix) {
  var ymin = block.ymin + block.yoffset;
  var ymax = block.ymax + block.yoffset;
  var xmin = block.xmin + block.xoffset;
  var xmax = block.xmax + block.xoffset;
  
  this.ymin = 
      ymin >= constants.CHAR_LOC_MARGIN ? ymin - constants.CHAR_LOC_MARGIN : 0;
  this.ymax = 
      ((ymax + constants.CHAR_LOC_MARGIN < matrix.length) 
          ? ymax + constants.CHAR_LOC_MARGIN 
          : matrix.length - 1);
  this.xmin = 
      xmin >= constants.CHAR_LOC_MARGIN ? xmin - constants.CHAR_LOC_MARGIN : 0;
  this.xmax = 
      ((xmax + constants.CHAR_LOC_MARGIN < matrix[0].length) 
          ? xmax + constants.CHAR_LOC_MARGIN 
          : matrix[0].length - 1);
  this.blackPixCount = block.blackPixCount;
}

// basically a Rect object
function Boundary(ymin, ymax, xmin, xmax) {
  this.ymin = ymin;
  this.ymax = ymax;
  this.xmin = xmin;
  this.xmax = xmax;
}
