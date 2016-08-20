const constants = require('./utils/constants');
const imageUtil = require('./utils/imageUtil');
const obj = require('./obj');
const queue =  require('./utils/Queue');
const util = require('./utils/util');

var isDebugMode = false;

module.exports = {
  getBubbles: getBubbles,
  getBubbleEnclosingCoord: getBubbleEnclosingCoord
};

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

function getBubbleEnclosingCoord(matrix, coords) {
  console.log('\ngetting bubble enclosing', coords + '...');
  isDebugMode = true;
  
  // ordered this way for ease of debugging since that is the way the coordinate
  // is formatted in ms paint
  var xcoord = parseInt(coords[0]);
  var ycoord = parseInt(coords[1]);
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
    
    if (isDebugMode) {
      imageUtil.debugPrintBubblePix(
          matrix, boundary, visitedWhitePix, bubbleIdx, '0_bubble_marked.png');
      imageUtil.debugPrintOnlyBubblePix(
          matrix, boundary, isWhitePixOfBubble, '1_bubble_only.png');
      imageUtil.debugPrintMatrix(
          bubbleTextParams.bubbleMatrix, '2_clean_bubble.png');
    }
    
    if (util.hasEnoughBlackPixForBlock(bubbleTextParams.blackPixCount)) {
      console.log('\nBubble found around given coordinates!');
      return new obj.Bubble(bubbleTextParams.bubbleMatrix, yoffset, xoffset);
    } else {
      console.log('\nNo bubble found around given coordinates');
    }
  }
  // return something smarter
  return new obj.Bubble(false, yoffset, xoffset);
}

function getBubbleParamsEnclosingCoords(
    matrix, ycoord, xcoord, visitedWhitePix) {
  var bubbleIdx = 0;
  var ylen = matrix.length - 1;
  var xlen = matrix[0].length - 1;
  var ycoords = constants.Y_COORDS;
  var xcoords = constants.X_COORDS;
  var bubbleFound = false;
  
  var visited = new Set([[ycoord, xcoord]]); // not sure if this is performant
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
      
      if (util.hasEnoughWhitePixForBlock(bubbleWhitePixParams.whitePixCount)) {
        console.log('bubble found around:', x, y);
        console.log('bubble boundary:', boundary);
        bubbleFound = true;
        break;
      }
    }
    // check the 4 nearby pixels
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

function getBubbleText(matrix, boundary, isWhitePixOfBubble) {
  var isBackground = getBackgroundPixels(matrix, boundary, isWhitePixOfBubble);
  
  var blackPixCount = 0;
  var ymin = boundary.ymin;
  var xmin = boundary.xmin;
  var bubbleMatrix = [];
  for (var i = ymin; i <= boundary.ymax; i++) {
    var row = [];
    for (var j = xmin; j <= boundary.xmax; j++) {
      var isBackgroundPix = isBackground[i - ymin][j - xmin]
      if (util.isBlackPixel(matrix[i][j]) && !isBackgroundPix) {
        blackPixCount++;
      }
      var pixVal = isBackgroundPix ? 255 : matrix[i][j];
      row.push(pixVal);
    }
    bubbleMatrix.push(row);
  }
  return tightenBubbleBoundary(bubbleMatrix, blackPixCount)
}

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
