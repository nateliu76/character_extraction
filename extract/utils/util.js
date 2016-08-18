const constants = require('./constants');

module.exports = {
  isBlackPixel: isBlackPixel,
  isWhitePixel: isWhitePixel,
  hasEnoughBlackPixForBlock: hasEnoughBlackPixForBlock,
  blockRatio: blockRatio
};

function isBlackPixel(pix) {
  return pix <= constants.BLACK_COLOR && pix >= 0;
}

function isWhitePixel(pix) {
  return pix >= constants.WHITE_COLOR;
}

function hasEnoughBlackPixForBlock(pixCount) {
  return pixCount >= constants.BLOCK_MIN_BLACK_PIX_COUNT;
}

function blockRatio(len1, len2) {
  return Math.min(len1, len2) * 1.0 / Math.max(len1, len2);
}