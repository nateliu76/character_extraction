const constants = require('./utils/constants');
const imageUtil = require('./utils/imageUtil');
const obj = require('./obj');
const util = require('./utils/util');

var isDebugMode = false;

module.exports = {
  getCharacterLocations: getCharacterLocations
};

function getCharacterLocations(subbubbles) {
  console.log('\nGetting all character locations within subbubbles...');
  console.log(subbubbles.length, 'subbubbles to process');
  
  isDebugMode = true;
  
  var blocks = [];
  for (var i = 0; i < subbubbles.length; i++) {
    var markedMatrix = util.getMatrixWithMarkedGaps(subbubbles[i].matrix);
    
    var rawBlocks = getBlocksFromMarkedMatrix(markedMatrix);
    
    // debug print blocks pre dissect
    if (isDebugMode) {
      console.log('finished getting blocks from marked matrix');
      var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
      var filename = '5_' + i + '_raw_blocks.png';
      imageUtil.debugPrintBoundaries(arr, rawBlocks, filename);
    }
    
    var processedBlocks = maybeDissectSomeBlocks(markedMatrix, rawBlocks);
    
    // debug print blocks pre merge
    if (isDebugMode) {
      var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
      var filename = '6_' + i + '_dissected_blocks.png';
      imageUtil.debugPrintBoundaries(arr, processedBlocks, filename);
    }
    continue;
    
    var finalBlocks = maybeMergeSomeBlocks(processedBlocks);
    
    // debug print blocks post merge
    
    Arrays.prototype.push.apply(
        blocks,
        finalBlocks.map(
            function(block) {
              block.yoffset += subbubbles[i].yoffset;
              block.xoffset += subbubbles[i].xoffset;
              return block;
            }));
  }
  return postProcessBlocks(blocks);
}

function maybeMergeSomeBlocks(markedMatrix, blocks) {
  markAdjBlocks(markedMatrix, blocks);
  
  var finalBlocks = [];
  for (var i = 0; i < blocks.length; i++) {
    var block = blocks[i];
    
    if (shouldTryMerging(block)) {
      var mergedBlock = getMergedBlock(block);
      if (mergedBlock.isValidBlock()) {
        finalBlocks.push(mergedBlock);
      }
    } else if (!block.matched && block.isValidBlock()) {
      finalBlocks.push(block);
    }
  }
  return finalBlocks;
}

function shouldTryMerging(block) {
  // not sure if block.hasBlackPix is the good to have here...
  return !block.matched 
      && block.hasBlackPix 
          && block.ratio < constants.MERGE_RATIO_THRES;
}

function getMergedBlock() {
  
}

function markAdjBlocks(markedMatrix, blocks) {
  
}

// modifies markedMatrix
function maybeDissectSomeBlocks(markedMatrix, blocks) {
  var processedBlocks = [];
  
  for (var i = 0; i < blocks.length; i++) {
    var block = blocks[i];
    
    if (util.shouldDissectBlock(block)) {
      var dissectedBlocks = getDissectedBlocks(markedMatrix, block);
      Array.prototype.push.apply(processedBlocks, dissectedBlocks);
    } else {
      processedBlocks.push(block);
    }
  }
  return processedBlocks;
}

function getDissectedBlocks(markedMatrix, block) {
  markGapsWithinBlock(markedMatrix, block);
  
  var ymin = block.ymin;
  var ymax = block.ymax;
  var xmin = block.xmin;
  var xmax = block.xmax;
  
  var processed = [];
  for (var i = 0; i < block.ylen; i++) {
    processed.push(new Array(block.xlen).fill(false));
  }
  
  var blocks = [];
  for (var i = ymin; i <= ymax; i++) {
    for (var j = xmin; j <= xmax; j++) {
      if (!util.isGap(markedMatrix[i][j]) && !processed[i - ymin][j - xmin]) {
        var block = 
            getBlockFromMarkedMatrixGiveCoord(
                markedMatrix, i, j, processed, ymin, xmin);
        blocks.push(block);
      }
    }
  }
  return blocks;
}

function markGapsWithinBlock(markedMatrix, block) {
  var ymin = block.ymin;
  var ymax = block.ymax;
  var xmin = block.xmin;
  var xmax = block.xmax;
  
  // initialize hasWord arrays for y, x dir
  var hasWordY = [];
  var hasWordX = [];
  for (var i = 0; i < block.ylen; i++) {
    hasWordY.push(false);
  }
  for (var j = 0; j < block.xlen; j++) {
    hasWordX.push(false);
  }
  
  // mark which rows and columns has words/black pixels
  for (var i = ymin; i <= ymax; i++) {
    for (var j = xmin; j <= xmax; j++) {
      if (util.isBlackPixel(markedMatrix[i][j])) {
        hasWordY[i - ymin] = true;
        hasWordX[j - xmin] = true;
      }
    }
  }
  // mark horizontal gaps
  if (util.hasEnoughLenToDissect(block.ylen)) {
    for (var i = ymin; i <= ymax; i++) {
      if (!hasWordY[i]) {
        for (var j = xmin; j <= xmax; j++) {
          markedMatrix[i][j] = constants.GAP_VAL;
        }
      }
    }
  }
  // mark vertical gaps
  if (util.hasEnoughLenToDissect(block.xlen)) {
    for (var j = xmin; j <= xmax; j++) {
      if (!hasWordX[j]) {
        for (var i = ymin; i <= ymax; i++) {
          markedMatrix[i][j] = constants.GAP_VAL;
        }
      }
    }
  }
}

function getBlocksFromMarkedMatrix(markedMatrix) {
  var processed = util.initNewArrayWithVal(markedMatrix, false);
  var blocks = [];
  
  // iterate through marked matrix and find blocks
  for (var i = 0; i < markedMatrix.length; i++) {
    for (var j = 0; j < markedMatrix[0].length; j++) {
      if (!util.isGap(markedMatrix[i][j]) && !processed[i][j]) {
        var block = 
            getBlockFromMarkedMatrixGiveCoord(
                markedMatrix, i, j, processed, 0, 0);
        blocks.push(block);
      }
    }
  }
  return blocks;
}

function getBlockFromMarkedMatrixGiveCoord(
    markedMatrix, ymin, xmin, processed, yoffset, xoffset) {
  // find the bottom boundary
  var ynext = ymin;
  while(!hasReachedBottomBoundary(markedMatrix, ynext, xmin)) {
    ynext++;
  }
  
  // find the right boundary
  var xnext = xmin;
  while(!hasReachedRightBoundary(markedMatrix, ymin, xnext)) {
    xnext++;
  }
  
  var ymax = ynext - 1;
  var xmax = xnext - 1;
  
  // go through the block and count the number of black pixels
  var blackPixCount = 0;
  for (var i = ymin; i <= ymax; i++) {
    for (var j = xmin; j <= xmax; j++) {
      processed[i - yoffset][j - xoffset] = true;
      if (util.isBlackPixel(markedMatrix[i][j])) {
        blackPixCount++;
      }
    }
  }
  return new obj.Block(ymin, ymax, xmin, xmax, blackPixCount);
}

function hasReachedBottomBoundary(matrix, i, j) {
  return (i >= matrix.length || util.isGap(matrix[i][j]))
      && (i + 1 >= matrix.length || util.isGap(matrix[i + 1][j]));
}

function hasReachedRightBoundary(matrix, i, j) {
  return (j >= matrix[0].length || util.isGap(matrix[i][j]))
      && (j + 1 >= matrix[0].length || util.isGap(matrix[i][j + 1]));
}

function postProcessBlocks(blocks) {
  var resolvedBlocks = resolveOverlappingBlocks(blocks); 
  return 
      resolvedBlocks.map(
          function(block) {
            return new obj.CharacterLocation(block);
          });
}

function resolveOverlappingBlocks(blocks) {
  
}
