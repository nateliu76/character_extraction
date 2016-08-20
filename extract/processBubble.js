const constants = require('./utils/constants');
const imageUtil = require('./utils/imageUtil');
const obj = require('./obj');
const util = require('./utils/util');
var isDebugMode = false;

module.exports = {
  getSubbubbles: getSubbubbles
};

function getSubbubbles(bubbles) {
  console.log('\nGetting all subbubbles within bubbles...');
  
  // setting debug mode to true for now.
  isDebugMode = true;
  
  var subbubbles = []
  for (var i = 0; i < bubbles.length; i++) {
    var subbbubblesFromCurrBubble = getSubbubblesFromBubble(bubbles[i], i);
    subbubbles = subbubbles.concat(subbbubblesFromCurrBubble);
  }
  return subbubbles;
}

function getSubbubblesFromBubble(bubble, idx) {
  var matrix = bubble.matrix;
  var yoffset = bubble.yoffset;
  var xoffset = bubble.xoffset;
  
  var markedMatrix = getMatrixWithMarkedGaps(matrix);
  
  if (isDebugMode) {
    var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
    imageUtil.debugPrintMatrix(arr, '3_marked_matrix.png');
  }
  
  var visited = util.initNewArrayWithVal(matrix, false);
  
  var subbubbles = [];
  // iterate through each pixel and find subbubble
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[0].length; j++) {
      if (!util.isGap(markedMatrix[i][j]) && !visited[i][j]) {
        var subbubbleParams = getSubbubbleParams(markedMatrix, i, j, visited);
        if (subbubbleParams.hasSubbubble) {
          console.log('\nfound subbubble');
              
          var subbubble = 
              new obj.Subbubble(
                  subbubbleParams.subbubbleMatrix, 
                      yoffset + subbubbleParams.yoffset, 
                      xoffset + subbubbleParams.xoffset);
          
          // debug print subbubble here
          if (isDebugMode && subbubbles.length < 10) {
            var filename = 
                '4_' + idx + '_' + subbubbles.length + '_subbubble.png';
            var ymin = subbubbleParams.yoffset;
            var ymax = ymin + subbubbleParams.subbubbleMatrix.length - 1;
            var xmin = subbubbleParams.xoffset;
            var xmax = xmin + subbubbleParams.subbubbleMatrix[0].length - 1;
            var boundary = new obj.Boundary(ymin, ymax, xmin, xmax);
            var arr = 
                imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
            imageUtil.debugPrintBoundary(arr, boundary, filename);
          }
          
          subbubbles.push(subbubble);
        }
      }
    }
  }
  return subbubbles;
}

function getMatrixWithMarkedGaps(matrix) {
  var matrixCopy = [];
  for (var i = 0; i < matrix.length; i++) {
    matrixCopy.push(matrix[i].slice());
  }
  
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
      if (util.isBlackPixel(matrix[i][j])) {
        hasWordY[i] = true;
        hasWordX[j] = true;
      }
    }
  }
  // actually we don't really need the matrix to be marked, we can just use the
  // two hasWord arrays to see if it is marked, however this optimize might
  // not be significant.
  
  // mark copy of matrix based off value of hasWord
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[0].length; j++) {
      if (!hasWordY[i] || !hasWordX[j]) {
        matrixCopy[i][j] = constants.GAP_VAL;
      }
    }
  }
  return matrixCopy
}

function getSubbubbleParams(markedMatrix, ycoord, xcoord, visited) {
  var stack = [[ycoord, xcoord]];
  var ymin = ycoord;
  var ymax = ycoord;
  var xmin = xcoord;
  var xmax = xcoord;
  var blackPixCount = 0;
  
  // DFS, but search for rectangles nearby instead of pixels nearby
  while (stack.length > 0) {
    var coord = stack.pop();
    var y = coord[0];
    var x = coord[1];
    
    if (!visited[y][x]) {
      var boundary = getRectBoundary(markedMatrix, y, x);
      var ymincurr = boundary.ymin;
      var ymaxcurr = boundary.ymax;
      var xmincurr = boundary.xmin;
      var xmaxcurr = boundary.xmax;
      
      ymin = Math.min(ymin, ymincurr);
      ymax = Math.max(ymax, ymaxcurr);
      xmin = Math.min(xmin, xmincurr);
      xmax = Math.max(xmax, xmaxcurr);
      
      // traverse through rect and update visited and blackPixCount
      for (var i = ymincurr; i <= ymaxcurr; i++) {
        for (var j = xmincurr; j <= xmaxcurr; j++) {
          visited[i][j] = true;
          if (util.isBlackPixel(markedMatrix[i][j])) {
            blackPixCount++;
          }
        }
      }
      
      pushNearbyRectsToStack(
          markedMatrix, ymincurr, ymaxcurr, xmincurr, xmaxcurr, stack);
    }
  }
  if (util.hasEnoughBlackPixForBlock(blackPixCount)) {
    var subbubbleMatrix = [];
    for (var i = ymin; i <= ymax; i++) {
      var row = [];
      for (var j = xmin; j <= xmax; j++) {
        row.push(util.isGap(markedMatrix[i][j])
            ? constants.WHITE_COLOR 
            : markedMatrix[i][j]);
      }
      subbubbleMatrix.push(row);
    }
    
    return {
        hasSubbubble: true, 
        subbubbleMatrix: subbubbleMatrix, 
        yoffset: ymin, 
        xoffset: xmin};
  } else {
    return {hasSubbubble:false};
  }
}

// modifies stack
function pushNearbyRectsToStack(
    markedMatrix, ymincurr, ymaxcurr, xmincurr, xmaxcurr, stack) {
  var ylimit = markedMatrix.length - 1;
  var xlimit = markedMatrix[0].length - 1;
  var ymid = Math.floor(ymincurr + (ymaxcurr - ymincurr) / 2);
  var xmid = Math.floor(xmincurr + (xmaxcurr - xmincurr) / 2);
  
  // search up
  var ynext = ymincurr;
  for (var k = 0; k < constants.SUBBUBBLE_BOUNDARY; k++) {
    ynext--;
    if (ynext < 0) {
      break;
    }
    if (!util.isGap(markedMatrix[ynext][xmid])) {
      stack.push([ynext, xmid])
      break;
    }
  }
  
  // searh down
  ynext = ymaxcurr;
  for (var k = 0; k < constants.SUBBUBBLE_BOUNDARY; k++) {
    ynext++;
    if (ynext > ylimit) {
      break;
    }
    if (!util.isGap(markedMatrix[ynext][xmid])) {
      stack.push([ynext, xmid])
      break;
    }
  }
  
  // search left
  var xnext = xmincurr;
  for (var k = 0; k < constants.SUBBUBBLE_BOUNDARY; k++) {
    xnext--;
    if (xnext < 0) {
      break;
    }
    if (!util.isGap(markedMatrix[ymid][xnext])) {
      stack.push([ymid, xnext])
      break;
    }
  }
  
  // search right
  var xnext = xmaxcurr;
  for (var k = 0; k < constants.SUBBUBBLE_BOUNDARY; k++) {
    xnext++;
    if (xnext > xlimit) {
      break;
    }
    if (!util.isGap(markedMatrix[ymid][xnext])) {
      stack.push([ymid, xnext])
      break;
    }
  }
}

function getRectBoundary(markedMatrix, ycoord, xcoord) {
  var ylimit = markedMatrix.length - 1;
  var xlimit = markedMatrix[0].length - 1;
  
  // search up
  var ynext = ycoord;
  while (
      util.isInBounds(ylimit, xlimit, ynext - 1, xcoord) 
          && !util.isGap(markedMatrix[ynext - 1][xcoord])) {
    ynext--;
  }
  var ymin = ynext;
  
  // search down
  ynext = ycoord;
  while (
      util.isInBounds(ylimit, xlimit, ynext + 1, xcoord) 
          && !util.isGap(markedMatrix[ynext + 1][xcoord])) {
    ynext++;
  }
  var ymax = ynext;
  
  // search left
  var xnext = xcoord;
  while (
      util.isInBounds(ylimit, xlimit, ycoord, xnext - 1) 
          && !util.isGap(markedMatrix[ycoord][xnext - 1])) {
    xnext--;
  }
  var xmin = xnext;
  
  // search right
  xnext = xcoord;
  while (
      util.isInBounds(ylimit, xlimit, ycoord, xnext + 1) 
          && !util.isGap(markedMatrix[ycoord][xnext + 1])) {
    xnext++;
  }
  var xmax = xnext;
  
  return new obj.Boundary(ymin, ymax, xmin, xmax);
}
