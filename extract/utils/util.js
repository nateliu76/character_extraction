const constants = require('./constants');

module.exports = {
  isBlackPixel: isBlackPixel,
  isWhitePixel: isWhitePixel
};

function isBlackPixel(pix) {
  return pix <= constants.BLACK_COLOR && pix >= 0;
}

function isWhitePixel(pix) {
  return pix >= constants.WHITE_COLOR;
}
