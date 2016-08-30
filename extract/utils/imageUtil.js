const constants = require('./constants');
const jimp = require('jimp');
const obj = require('../obj');
const util = require('./util');

const HIGHLIGHT_GREEN = -1;
const HIGHLIGHT_BLUE = -2;
const HIGHLIGHT_GREY = -3;
const GREEN_HEX = jimp.rgbaToInt(0, 255, 0, 255);
const BLUE_HEX = jimp.rgbaToInt(0, 255, 255, 255);
const GREY_HEX = jimp.rgbaToInt(125, 125, 125, 255);

// Methods used to interact with Jimp
// includes image saving for debugging, and helper methods that help generate
// matrices for debugging.

module.exports = {
  saveImage: saveImage,
  imageToMatrix: imageToMatrix,
  debugPrintMatrix: saveImage,
  debugPrintBoundary: debugPrintBoundary,
  debugPrintBubblePix: debugPrintBubblePix,
  debugPrintOnlyBubblePix: debugPrintOnlyBubblePix,
  mapMatrixValToGrey: mapMatrixValToGrey,
  debugPrintBoundaries: debugPrintBoundaries,
  debugPrintBoundariesWithOffsets: debugPrintBoundariesWithOffsets
};

// Saves the matrix to an image using the filename.
// The filename should have the filetype suffix. Ex: some_image.png
function saveImage(matrix, filename) {
  var width = matrix[0].length;
  var height = matrix.length;
  var img = new jimp(width, height, function (err, img) {
    // set each pixel in new image according to value in matrix
    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        var pixHex = getHexVal(matrix[y][x]);
        img.setPixelColor(pixHex, x, y);
      }
    }
    img.write(filename);
    console.log('Done printing image:', filename);
  });
}

// Saves the pixel values of an image to a 2d list aka matrix.
// The image should be in greyscale.
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

// Converts the value of the matrix to an actual pixel value that is used by 
// jimp.
function getHexVal(pixVal) {
  if (pixVal === HIGHLIGHT_GREEN) {
    return GREEN_HEX;
  } else if (pixVal === HIGHLIGHT_BLUE) {
    return BLUE_HEX;
  } else if (pixVal === HIGHLIGHT_GREY) {
    return GREY_HEX;
  } else {
    return jimp.rgbaToInt(pixVal, pixVal, pixVal, 255);
  }
}

// Below are methods used for debugging.

function debugPrintBoundary(matrix, boundary, filename) {
  debugPrintBoundaries(matrix, [boundary], filename);
}

function debugPrintBoundaries(matrix, boundaries, filename, margin) {
  var arr = copyMatrix(matrix);
  for (var i = 0; i < boundaries.length; i++) {
    markBoundary(arr, boundaries[i], HIGHLIGHT_GREEN, margin);
  }
  saveImage(arr, filename);
}

function debugPrintBoundariesWithOffsets(matrix, objects, filename) {
  var boundaries = 
      objects.map(
          function(block) {
            var ymin = block.yoffset;
            var ymax = ymin + block.matrix.length - 1;
            var xmin = block.xoffset;
            var xmax = xmin + block.matrix[0].length - 1;
            return new obj.Boundary(ymin, ymax, xmin, xmax);
          });
  debugPrintBoundaries(matrix, boundaries, filename);
}

function debugPrintBubblePix(
    matrix, boundary, shouldMark, markIdx, filename) {
  var arr = copyMatrix(matrix);
  markPixels(arr, boundary, shouldMark, markIdx, HIGHLIGHT_GREEN);
  markBoundary(arr, boundary, HIGHLIGHT_BLUE);
  saveImage(arr, filename);
}

function debugPrintOnlyBubblePix(matrix, boundary, shouldMark, filename) {
  var arr = cropBubbleSection(matrix, boundary);
  boundary = {ymin: 0, ymax: arr.length - 1, xmin: 0, xmax: arr[0].length - 1};
  
  markPixels(arr, boundary, shouldMark, true, HIGHLIGHT_GREEN);
  saveImage(arr, filename);
}

function markPixels(matrix, boundary, shouldMark, markIdx, color) {
  for (var i = boundary.ymin; i <= boundary.ymax; i++) {
    for (var j = boundary.xmin; j <= boundary.xmax; j++) {
      if (shouldMark[i][j] === markIdx) {
        matrix[i][j] = color;
      }
    }
  }
}

function markBoundary(matrix, boundary, color, margin) {
  if (typeof margin === "undefined") {
    margin = constants.DEBUG_PRINT_BOUNDARY_MARGIN;
  }
  var ymin = boundary.ymin;
  var ymax = boundary.ymax;
  var xmin = boundary.xmin;
  var xmax = boundary.xmax;
  
  var ymin = ymin >= margin ? ymin - margin : 0;
  var ymax = 
      (ymax + margin < matrix.length) ? ymax + margin : matrix.length - 1;
  var xmin = xmin >= margin ? xmin - margin : 0;
  var xmax = 
      (xmax + margin < matrix[0].length) ? xmax + margin : matrix[0].length - 1;
  
  for (var i = ymin; i <= ymax; i++) {
    matrix[i][xmin] = color;
    matrix[i][xmax] = color;
  }
  for (var j = xmin; j <= xmax; j++) {
    matrix[ymin][j] = color;
    matrix[ymax][j] = color;
  }
}

function cropBubbleSection(matrix, boundary) {
  var arr = [];
  for (var i = boundary.ymin; i <= boundary.ymax; i++) {
    arr.push(matrix[i].slice(boundary.xmin, boundary.xmax + 1));
  }
  return arr;
}

function copyMatrix(matrix) {
  var arr = [];
  for (var i = 0; i < matrix.length; i++) {
    arr.push(matrix[i].slice());
  }
  return arr;
}

function mapMatrixValToGrey(matrix, val) {
  var arr = [];
  for (var k = 0; k < matrix.length; k++) {
    arr.push(matrix[k].map(
        function(pix) { return util.isGap(pix) ? HIGHLIGHT_GREY : pix; }));
  }
  return arr;
}
