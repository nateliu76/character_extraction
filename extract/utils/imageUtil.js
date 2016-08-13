const jimp = require("jimp");

module.exports = {
  saveImage: saveImage,
  imageToMatrix: imageToMatrix
};

function saveImage(matrix, filename) {
  var width = matrix[0].length;
  var height = matrix.length;
  var img = new jimp(width, height, function (err, img) {
    // set each pixel in new image according to value in matrix
    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        var pix = matrix[y][x];
        var pixHex = jimp.rgbaToInt(pix, pix, pix, 255);
        img.setPixelColor(pixHex, x, y);
      }
    }
    img.write(filename);
  });
}

function imageToMatrix(img) {
  var width = img.bitmap.width;
  var height = img.bitmap.height;
  var matrix = [];
  var idx = 0;
  for (var y = 0; y < height; y++) {
    var row = [];
    for (var x = 0; x < width; x++) {
      row.push(img.bitmap.data[idx]);
      idx += 4;
    }
    matrix.push(row);
  }
  return matrix;
}