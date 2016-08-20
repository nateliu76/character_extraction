const constants = require('./constants');

module.exports = {
  initNewArrayWithVal: initNewArrayWithVal,
  isBlackPixel: isBlackPixel,
  isWhitePixel: isWhitePixel,
  hasEnoughBlackPixForBlock: hasEnoughBlackPixForBlock,
  hasEnoughWhitePixForBlock: hasEnoughWhitePixForBlock,
  blockRatio: blockRatio,
  isGap: isGap,
  isInBounds: isInBounds
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
