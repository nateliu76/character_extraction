const constants = require('./constants');

module.exports = {
  initNewArrayWithVal: initNewArrayWithVal,
  isBlackPixel: isBlackPixel,
  isWhitePixel: isWhitePixel,
  hasEnoughBlackPixForBlock: hasEnoughBlackPixForBlock,
  hasEnoughWhitePixForBlock: hasEnoughWhitePixForBlock,
  blockRatio: blockRatio,
  isGap: isGap,
  isInBounds: isInBounds,
  getMatrixWithMarkedGaps: getMatrixWithMarkedGaps,
  shouldDissectBlock: shouldDissectBlock,
  hasEnoughLenToDissect: hasEnoughLenToDissect
};

function initNewArrayWithVal(matrix, val) {
  var arr = [];
  for (var i = 0; i < matrix.length; i++) {
    arr.push(new Array(matrix[0].length).fill(val));
  }
  return arr;
}

function isBlackPixel(pix) {
  return pix <= constants.BLACK_COLOR_THRES && pix >= 0;
}

function isWhitePixel(pix) {
  return pix >= constants.WHITE_COLOR_THRES;
}

function hasEnoughBlackPixForBlock(pixCount) {
  return pixCount >= constants.BLOCK_MIN_BLACK_PIX_COUNT;
}

function hasEnoughWhitePixForBlock(whitePixCount) {
  return whitePixCount >= constants.BLOCK_MIN_WHITE_PIX_COUNT;
}

function blockRatio(len1, len2) {
  return Math.min(len1, len2) * 1.0 / Math.max(len1, len2);
}

function isGap(pixVal) {
  return pixVal === constants.GAP_VAL;
}

function isInBounds(ylen, xlen, y, x) {
  return y >= 0 && y <= ylen && x >= 0 && x <= xlen;
}

// Mark gaps for the matrix
function getMatrixWithMarkedGaps(matrix) {
  // initialize hasWord arrays for y, x dir
  var hasWordY = [];
  var hasWordX = [];
  for (var i = 0; i < matrix.length; i++) {
    hasWordY.push(false);
  }
  for (var j = 0; j < matrix[0].length; j++) {
    hasWordX.push(false);
  }
  
  // iterate through every pixel in matrix and mark hasWord
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[0].length; j++) {
      if (isBlackPixel(matrix[i][j])) {
        hasWordY[i] = true;
        hasWordX[j] = true;
      }
    }
  }
  // actually we don't really need the matrix to be marked, we can just use the
  // two hasWord arrays to see if it is marked, however this optimize might
  // not be significant.
  
  // mark copy of matrix based off value of hasWord
  var matrixCopy = [];
  for (var i = 0; i < matrix.length; i++) {
    matrixCopy.push(matrix[i].slice());
  }
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[0].length; j++) {
      if (!hasWordY[i] || !hasWordX[j]) {
        matrixCopy[i][j] = constants.GAP_VAL;
      }
    }
  }
  return matrixCopy
}

function shouldDissectBlock(block) {
  return block.ratio <= constants.DISSECT_RATIO_THRES 
      && (hasEnoughLenToDissect(block.ylen) 
          || hasEnoughLenToDissect(block.xlen));
}

function hasEnoughLenToDissect(len) {
  return len > constants.WORD_BREAK_MIN_LEN;
}
