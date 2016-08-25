const constants = require('./utils/constants');
const imageUtil = require('./utils/imageUtil');
const obj = require('./obj');
const queue =  require('./utils/Queue');
const util = require('./utils/util');

// This program makes the following assumptions and use them as heuristics:
// 1. The color of words within a text bubble is black
// 2. The color of the text bubble is white
// 3. The white portion of the bubble surrounds the black text

// Taking the above assumptions, we can find places that are possibly bubbles
// using the following steps:
// 1. Run flood fill to find out how many white pixels there are, this should be
//    above a certain threshold
// 2. Count the number of black pixels that are surrounded by the white pixels,
//    this should be above a certain threshold if there are words in the bubble

// An extra step is taken between 1 and 2 to get rid of pixels that are not 
// surrounded by the white pixels. After getting rid of them, we can then
// easily count the black pixels within the bubble.

module.exports = {
  getBubbles: getBubbles,
  getBubbleEnclosingCoord: getBubbleEnclosingCoord
};

// Get all possible bubbles that are in the matrix.
function getBubbles(matrix) {
  console.log('\nGetting all bubbles within the matrix...');
  
  var bubbles = [];
  var bubbleIdx = 0;
  var visitedWhitePix = util.initNewArrayWithVal(matrix, 0);
  
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[0].length; j++) {
      if (util.isWhitePixel(matrix[i][j]) && !visitedWhitePix[i][j]) {
        bubbleIdx++;
        var bubbleWhitePixParams = 
            getBubbleParams(matrix, i, j, visitedWhitePix, bubbleIdx);
        var boundary = bubbleWhitePixParams.boundary;
        
        if (util.hasEnoughWhitePixForBlock(
            bubbleWhitePixParams.whitePixCount)) {
          var isWhitePixOfBubble = 
              getIsWhitePixOfBubble(boundary, visitedWhitePix, bubbleIdx);
          var bubbleTextParams = 
              getBubbleText(matrix, boundary, isWhitePixOfBubble);
              
          if (util.hasEnoughBlackPixForBlock(bubbleTextParams.blackPixCount)) {
            var yoffset = bubbleTextParams.yoffset + boundary.ymin;
            var xoffset = bubbleTextParams.xoffset + boundary.xmin;
            bubbles.push(
                new obj.Bubble(
                    bubbleTextParams.bubbleMatrix, yoffset, xoffset));
          }
        }
      }
    }
  }
  return bubbles;
}

function getBubbleEnclosingCoord(matrix, ycoord, xcoord) {
  console.log('\ngetting bubble enclosing', ycoord, xcoord, '...');
  
  var visitedWhitePix = util.initNewArrayWithVal(matrix, 0);
  
  var bubbleParams = 
      getBubbleParamsEnclosingCoords(matrix, ycoord, xcoord, visitedWhitePix);
  
  if (bubbleParams.bubbleFound) {
    var bubbleIdx = bubbleParams.bubbleIdx;
    var boundary = bubbleParams.boundary;
    
    var isWhitePixOfBubble = 
        getIsWhitePixOfBubble(boundary, visitedWhitePix, bubbleIdx);
    
    var bubbleTextParams = getBubbleText(matrix, boundary, isWhitePixOfBubble);
    var yoffset = bubbleTextParams.yoffset + boundary.ymin;
    var xoffset = bubbleTextParams.xoffset + boundary.xmin;
    
    if (constants.IS_DEBUG_PRINT_PROCESS_MATRIX) {
      debugPrintBubble(
          matrix,
          boundary, 
          visitedWhitePix, 
          bubbleIdx, 
          isWhitePixOfBubble, 
          bubbleTextParams);
    }
    
    if (util.hasEnoughBlackPixForBlock(bubbleTextParams.blackPixCount)) {
      console.log('\nBubble found around given coordinates!');
      return new obj.Bubble(bubbleTextParams.bubbleMatrix, yoffset, xoffset);
    } else {
      console.log('\nNo bubble found around given coordinates');
    }
  }
  // TODO: return something smarter
  return new obj.Bubble(false, yoffset, xoffset);
}

function debugPrintBubble(
    matrix,
    boundary, 
    visitedWhitePix, 
    bubbleIdx, 
    isWhitePixOfBubble, 
    bubbleTextParams) {
  imageUtil.debugPrintBubblePix(
      matrix, boundary, visitedWhitePix, bubbleIdx, '1_0_bubble_marked.png');
  imageUtil.debugPrintOnlyBubblePix(
      matrix, boundary, isWhitePixOfBubble, '1_1_bubble_only.png');
  imageUtil.debugPrintMatrix(
      bubbleTextParams.bubbleMatrix, '1_2_clean_bubble.png');
}

// a wrapping function around getBubbleParams() that uses BFS to find the white
// pixels of the bubble (as opposed to iterating through every pixel as seen
// in getBubbles()
function getBubbleParamsEnclosingCoords(
    matrix, ycoord, xcoord, visitedWhitePix) {
  var bubbleIdx = 0;
  var ylen = matrix.length - 1;
  var xlen = matrix[0].length - 1;
  var ycoords = constants.Y_COORDS;
  var xcoords = constants.X_COORDS;
  var bubbleFound = false;
  
  // not sure if putting lists within a set is performant, might be worth it to
  // to change this to a 2d list.
  // visited keeps track of visited non white pixels
  var visited = new Set([[ycoord, xcoord]]);
  
  // run BFS around given coords
  var q = new queue.Queue();
  q.enqueue([ycoord, xcoord]);
  while (!q.isEmpty()) {
    var coord = q.dequeue();
    var y = coord[0];
    var x = coord[1];
    
    // check if bubbles are found for the white pixel
    if (util.isWhitePixel(matrix[y][x]) && !visitedWhitePix[y][x]) {
      console.log('\nfound white pixel at:', y, x);
      bubbleIdx++;
      var bubbleWhitePixParams = 
          getBubbleParams(matrix, y, x, visitedWhitePix, bubbleIdx);
      var boundary = bubbleWhitePixParams.boundary;
      
      // if bubble is found, break from BFS
      if (util.hasEnoughWhitePixForBlock(bubbleWhitePixParams.whitePixCount)) {
        console.log('bubble found around:', x, y);
        console.log('bubble boundary:', boundary);
        bubbleFound = true;
        break;
      }
    }
    // check the 4 nearby pixels and put on queue if necessary
    for (var k = 0; k < 4; k++) {
      var i = y + ycoords[k];
      var j = x + xcoords[k];
      var nextPos = [i, j];
      
      if (util.isInBounds(ylen, xlen, i, j) 
          && !visited.has(nextPos) 
              && !visitedWhitePix[i][j]) {
        q.enqueue(nextPos);
        visited.add(nextPos);
      }
    }
  }
  return {
      bubbleFound: bubbleFound,
      bubbleIdx: bubbleIdx,
      boundary: bubbleWhitePixParams.boundary};
}

function getBubbleParams(matrix, ycoord, xcoord, visitedWhitePix, bubbleIdx) {
  var ymin = ycoord;
  var ymax = ycoord;
  var xmin = xcoord;
  var xmax = xcoord;
  
  var stack = [[ycoord, xcoord]];
  visitedWhitePix[ycoord][xcoord] = bubbleIdx;
  whitePixCount = 1;
  
  var ylen = matrix.length - 1;
  var xlen = matrix[0].length - 1;
  var ycoords = constants.Y_COORDS;
  var xcoords = constants.X_COORDS;
  
  // flood fill all white pixels neighboring (ycoord, xcoord)
  while (stack.length > 0) {
    var coord = stack.pop();
    var y = coord[0];
    var x = coord[1];
    
    ymin = Math.min(ymin, y);
    ymax = Math.max(ymax, y);
    xmin = Math.min(xmin, x);
    xmax = Math.max(xmax, x);
    
    for (var k = 0; k < 4; k++) {
      var i = y + ycoords[k];
      var j = x + xcoords[k];
      if (util.isInBounds(ylen, xlen, i, j) 
          && util.isWhitePixel(matrix[i][j]) 
              && !visitedWhitePix[i][j]) {
        stack.push([i, j]);
        visitedWhitePix[i][j] = bubbleIdx;
        whitePixCount++;
      }
    }
  }
  return {
      whitePixCount: whitePixCount, 
      boundary: new obj.Boundary(ymin, ymax, xmin, xmax)};
}

// Get bubble with only the text portion of the bubble
function getBubbleText(matrix, boundary, isWhitePixOfBubble) {
  var isBackground = getBackgroundPixels(matrix, boundary, isWhitePixOfBubble);
  
  var blackPixCount = 0;
  var ymin = boundary.ymin;
  var xmin = boundary.xmin;
  var bubbleMatrix = [];
  for (var i = ymin; i <= boundary.ymax; i++) {
    var row = [];
    for (var j = xmin; j <= boundary.xmax; j++) {
      var isPixBackground = isBackground[i - ymin][j - xmin]
      // once tightenBubbleBoundary() is implemented, move black pixel counting
      // there
      if (util.isBlackPixel(matrix[i][j]) && !isPixBackground) {
        blackPixCount++;
      }
      var pixVal = isPixBackground ? constants.WHITE_COLOR : matrix[i][j];
      row.push(pixVal);
    }
    bubbleMatrix.push(row);
  }
  return tightenBubbleBoundary(bubbleMatrix, blackPixCount)
}

// Runs flood fill on the boundaries to determine the pixels that are part of 
// the "background". The background is defined to be part of the bubble that is
// surrounds the white pixels of the bubble.
function getBackgroundPixels(matrix, boundary, isWhitePixOfBubble) {
  var yhi = boundary.ymax - boundary.ymin;
  var xhi = boundary.xmax - boundary.xmin;
  
  var isBackground = [];
  for (var i = 0; i <= yhi; i++) {
    isBackground.push(new Array(xhi + 1).fill(false));
  }
  // run flood fill from the specified boundary
  for (var i = 0; i <= yhi; i++) {
    if (!isBackground[i][0] && !isWhitePixOfBubble[i][0]) {
      floodFillBackground(isWhitePixOfBubble, isBackground, boundary, i, 0);
    }
    if (!isBackground[i][xhi] && !isWhitePixOfBubble[i][xhi]) {
      floodFillBackground(isWhitePixOfBubble, isBackground, boundary, i, xhi);
    }
  }
  
  for (var j = 0; j <= xhi; j++) {
    if (!isBackground[0][j] && !isWhitePixOfBubble[0][j]) {
      floodFillBackground(isWhitePixOfBubble, isBackground, boundary, 0, j);
    }
    if (!isBackground[yhi][j] && !isWhitePixOfBubble[yhi][j]) {
      floodFillBackground(isWhitePixOfBubble, isBackground, boundary, yhi, j);
    }
  }
  return isBackground;
}

function floodFillBackground(
    isWhitePixOfBubble, isBackground, boundary, ycoord, xcoord) {
  var ylen = boundary.ymax - boundary.ymin;
  var xlen = boundary.xmax - boundary.xmin;
  var stack = [[ycoord, xcoord]];
  isBackground[ycoord][xcoord] = true;
  
  var ycoords = constants.Y_COORDS;
  var xcoords = constants.X_COORDS;
  
  // flood fill
  while (stack.length > 0) {
    var coord = stack.pop();
    var y = coord[0];
    var x = coord[1];
    
    for (var k = 0; k < 4; k++) {
      var i = y + ycoords[k];
      var j = x + xcoords[k];
      if (util.isInBounds(ylen, xlen, i, j) 
          && !isWhitePixOfBubble[i][j] 
          && !isBackground[i][j]) {
        stack.push([i, j]);
        isBackground[i][j] = true;
      }
    }
  }
}

function getIsWhitePixOfBubble(boundary, visitedWhitePix, bubbleIdx) {
  var isWhitePixOfBubble = [];
  for (var y = boundary.ymin; y <= boundary.ymax; y++) {
    var row = [];
    for (var x = boundary.xmin; x <= boundary.xmax; x++) {
      row.push(visitedWhitePix[y][x] === bubbleIdx);
    }
    isWhitePixOfBubble.push(row);
  }
  return isWhitePixOfBubble;
}

// remove blackPixCount from argument once implemented.
function tightenBubbleBoundary(bubbleMatrix, blackPixCount) {
  // To be implemented
  return {
      bubbleMatrix: bubbleMatrix,
      blackPixCount: blackPixCount,
      yoffset: 0,
      xoffset: 0};
}
