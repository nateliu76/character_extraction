const constants = require('./utils/constants');
const imageUtil = require('./utils/imageUtil');
const obj = require('./obj');
const util = require('./utils/util');

var isDebugMode = false;

// This class is used to deal with the case where we have multiple bubbles that
// are merged. This separates the bubbles into separate sub-bubbles for ease of
// processing. 

// In perhaps half the cases, it is possible that a bubble has only
// a single subbbubble.

// Might be worth it to use some quick heuristic to bypass this stage if there
// is only a single subbubble within the bubble.

// Gaps between words are marked in the cleaned up bubble that only contains 
// text. the Gap is defined to be places in the matrix where there are no 
// black pixels in that row and column.

// The assumptions used:
// 1. Subbubbles have a certain distance between each other
// 2. The words within a subbubble are close to each other
// 3. the region in which separates subbubbles will be marked as a gap (using 
//    the definition of what a gap is above)
// 4. Each region that is not part of a gap has the shape of a rectangle
// 5. Words can only appear within rectangles

// Using those assumptions, we find the subbubbles with the following method
// 1. Mark the gaps of the matrix to find which pixels have no words in that
//    row and column
// 2. Find rectangles, once a rectangle is found, find if it has any other 
//    rectangles nearby within a certain distance.
// 3. All clusters of rectangles are considered to be a subbubble if there are
//    words within them, and returned.

module.exports = {
  getSubbubbles: getSubbubbles
};

function getSubbubbles(bubbles) {
  console.log('\nGetting all subbubbles within bubbles...');
  
  isDebugMode = false;
  
  var subbubbles = []
  for (var i = 0; i < bubbles.length; i++) {
    var subbbubblesFromCurrBubble = getSubbubblesFromBubble(bubbles[i], i);
    Array.prototype.push.apply(subbubbles, subbbubblesFromCurrBubble);
  }
  return subbubbles;
}

function getSubbubblesFromBubble(bubble, idx) {
  var matrix = bubble.matrix;
  var yoffset = bubble.yoffset;
  var xoffset = bubble.xoffset;
  
  var markedMatrix = util.getMatrixWithMarkedGaps(matrix);
  
  if (isDebugMode) {
    var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
    imageUtil.debugPrintMatrix(arr, '2_0_marked_matrix.png');
  }
  
  var visited = util.initNewArrayWithVal(matrix, false);
  
  var subbubbles = [];
  // iterate through each pixel to find subbubble
  for (var i = 0; i < matrix.length; i++) {
    for (var j = 0; j < matrix[0].length; j++) {
      if (!util.isGap(markedMatrix[i][j]) && !visited[i][j]) {
        var subbubbleParams = getSubbubbleParams(markedMatrix, i, j, visited);
        if (subbubbleParams.hasSubbubble) {
          console.log('\nfound subbubble');
          
          if (isDebugMode) {
            debugPrintSubbubble(idx, subbubbles, markedMatrix, subbubbleParams);
          }
          
          var subbubble = 
              new obj.Subbubble(
                  subbubbleParams.matrix, 
                      yoffset + subbubbleParams.yoffset, 
                      xoffset + subbubbleParams.xoffset);
          subbubbles.push(subbubble);
        }
      }
    }
  }
  return subbubbles;
}

function debugPrintSubbubble(idx, subbubbles, markedMatrix, subbubbleParams) {
  var filename = '2_1_' + idx + '_' + subbubbles.length + '_subbubble.png';
  var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
  imageUtil.debugPrintBoundariesWithOffsets(arr, [subbubbleParams], filename);
}

function getSubbubbleParams(markedMatrix, ycoord, xcoord, visited) {
  var stack = [[ycoord, xcoord]];
  var ymin = ycoord;
  var ymax = ycoord;
  var xmin = xcoord;
  var xmax = xcoord;
  var blackPixCount = 0;
  
  // DFS, but search in units of rectangles instead of pixels
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
      
      // update subbubble's y/x min/max
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
      // search nearby coordinates for rectangles close by
      // add them to the stack if found
      pushNearbyRectsToStack(
          markedMatrix, ymincurr, ymaxcurr, xmincurr, xmaxcurr, stack);
    }
  }
  // check if the current subbubble has enough black pixels. If so, copy the 
  // subbubble's portion of the matrix (without gaps marked) and return it
  // along with other parameters
  if (util.hasEnoughBlackPixForBlock(blackPixCount)) {
    // note: might want to add some extra buffer for the boundary
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
        matrix: subbubbleMatrix, 
        yoffset: ymin, 
        xoffset: xmin};
  } else {
    return {hasSubbubble:false};
  }
}

// modifies stack by adding coordinates of nearby rectangles
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

// A rectangle is defined to be an area that is enclosed by gaps, the shape is
// of a rectangle.
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
