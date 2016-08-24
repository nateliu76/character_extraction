const constants = require('./utils/constants');
const imageUtil = require('./utils/imageUtil');
const obj = require('./obj');
const util = require('./utils/util');

// Marks the gaps within the subbubbles, and extracts the rectangles that have
// black pixels within

// Some blocks are further broken down to mark gaps within since they might not
// have been fully processed due to unaligned characters next to them

// Some blocks are merged with others to form squares. Since Chinese characters
// mostly have a square shape, we use this as a heuristic to combine characters
// that would be otherwise separated by the gap marking mechanism into two or
// more blocks, Ex: 是, 二, 引

// Finally, all blocks that have overlaps are resolved since characters cannot
// have overlaps

// The blocks are then converted to the CharacterLocation class and returned

module.exports = {
  getCharacterLocations: getCharacterLocations
};

function getCharacterLocations(matrix, subbubbles) {
  console.log('\nGetting all character locations within subbubbles...');
  console.log(subbubbles.length + ' subbubbles to process');
  
  var blocks = [];
  for (var i = 0; i < subbubbles.length; i++) {
    var markedMatrix = util.getMatrixWithMarkedGaps(subbubbles[i].matrix);
    
    var rawBlocks = getBlocksFromMarkedMatrix(markedMatrix);
    
    // debug print blocks pre dissect
    if (constants.IS_DEBUG_PRINT_PROCESS_SUBBUBBLE) {
      var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
      var filename = '3_1_' + i + '_raw_blocks.png';
      imageUtil.debugPrintBoundaries(arr, rawBlocks, filename);
    }
    
    var processedBlocks = maybeDissectSomeBlocks(markedMatrix, rawBlocks);
    var finalBlocks = maybeMergeSomeBlocks(markedMatrix, processedBlocks);
    
    if (constants.IS_DEBUG_PRINT_PROCESS_SUBBUBBLE) {
      var arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
      var filename = '3_2_' + i + '_dissected_blocks.png';
      imageUtil.debugPrintBoundaries(arr, processedBlocks, filename);
      
      arr = imageUtil.mapMatrixValToGrey(markedMatrix, constants.GAP_VAL);
      filename = '3_3_' + i + '_merged_blocks.png';
      imageUtil.debugPrintBoundaries(arr, finalBlocks, filename);
    }
    
    // add offsets
    Array.prototype.push.apply(
        blocks,
        finalBlocks.map(
            function(block) {
              block.yoffset += subbubbles[i].yoffset;
              block.xoffset += subbubbles[i].xoffset;
              return block;
            }));
  }
  return postProcessBlocks(matrix, blocks);
}

function maybeMergeSomeBlocks(markedMatrix, blocks) {
  markAdjBlocks(markedMatrix, blocks);
  
  var finalBlocks = [];
  for (var i = 0; i < blocks.length; i++) {
    var block = blocks[i];
    
    if (shouldTryMerging(block)) {
      var mergedBlock = getMergedBlock(block);
      if (isValidBlock(mergedBlock)) {
        finalBlocks.push(mergedBlock);
      }
    } else if (!block.matched && isValidBlock(block)) {
      finalBlocks.push(block);
    }
  }
  return finalBlocks;
}

function isValidBlock(block) {
  var isValidSize = 
      block.blockSize > constants.MIN_BLOCK_SIZE 
          && block.blockSize < constants.MAX_BLOCK_SIZE;
  return isValidSize && util.hasEnoughBlackPixForBlock(block.blackPixCount);
}

function shouldTryMerging(block) {
  // not sure if block.hasBlackPix is the good to have here, it worked well in
  // the prototype so let's keep it here for now
  return !block.matched 
      && block.hasBlackPix 
          && block.ratio < constants.MERGE_RATIO_THRES;
}

function getMergedBlock(block) {
  if (block.ylen > block.xlen) {
    return mergeWithRight(block);
  } else {
    return mergeWithDown(block);
  }
}

function mergeWithRight(block) {
  var ymin = block.ymin;
  var ymax = block.ymax;
  var xmin = block.xmin;
  var xmax = block.xmax;
  var ratio = block.ratio;
  var blackPixCount = block.blackPixCount;
  
  var nextRightBlock = block.rightBlock;
  for (var i = 0; nextRightBlock && i < constants.MAX_MERGE_NUM; i++) {
    var xmaxRight = nextRightBlock.xmax;
    var mergedRatio =
        util.blockRatio(block.ylen, xmaxRight - xmin + 1);
    if (mergedRatio > Math.max(ratio, nextRightBlock.ratio)) {
      ratio = mergedRatio;
      xmax = xmaxRight;
      blackPixCount += nextRightBlock.blackPixCount;
      nextRightBlock.matched = true;
      nextRightBlock = nextRightBlock.rightBlock;
      
    } else {
      break;
    }
  }
  return new obj.Block(ymin, ymax, xmin, xmax, blackPixCount);
}

function mergeWithDown(block) {
  var ymin = block.ymin;
  var ymax = block.ymax;
  var xmin = block.xmin;
  var xmax = block.xmax;
  var ratio = block.ratio;
  var blackPixCount = block.blackPixCount;
  
  var nextDownBlock = block.downBlock;
  for (var i = 0; nextDownBlock && i < constants.MAX_MERGE_NUM; i++) {
    var ymaxDown = nextDownBlock.ymax;
    var mergedRatio =
        util.blockRatio(ymaxDown - ymin + 1, block.xlen);
    if (mergedRatio > Math.max(ratio, nextDownBlock.ratio)) {
      ratio = mergedRatio;
      ymax = ymaxDown;
      blackPixCount += nextDownBlock.blackPixCount;
      nextDownBlock.matched = true;
      nextDownBlock = nextDownBlock.downBlock;
      
    } else {
      break;
    }
  }
  return new obj.Block(ymin, ymax, xmin, xmax, blackPixCount);
}

// modifies the blocks' downBlock and rightBlock pointer
function markAdjBlocks(markedMatrix, blocks) {
  // get entire matrix marked as gaps
  var regions = util.initNewArrayWithVal(markedMatrix, constants.GAP_VAL);
  
  // first pass, mark regions of each block
  for (var k = 0; k < blocks.length; k++) {
    var block = blocks[k];
    var ymin = block.ymin;
    var ymax = block.ymax;
    var xmin = block.xmin;
    var xmax = block.xmax;
    
    // mark left
    for (var i = ymin; i <= ymax; i++) {
      regions[i][xmin] = k;
    }
    // mark top
    for (var j = xmin; j <= xmax; j++) {
      regions[ymin][j] = k;
    }
  }
  
  // second pass, mark the blocks that are to the current block's right/below
  for (var k = 0; k < blocks.length; k++) {
    var block = blocks[k];
    var ymin = block.ymin;
    var ymax = block.ymax;
    var xmin = block.xmin;
    var xmax = block.xmax;
    
    // search down
    for (var i = ymax + 1; i < markedMatrix.length; i++) {
      if (!util.isGap(regions[i][xmin])) {
        var blockBelow = blocks[regions[i][xmin]];
        // verify the xmin and xmax match
        if (block.xmin === blockBelow.xmin && block.xmax === blockBelow.xmax) {
          block.downBlock = blockBelow;
        }
        break;
      }
    }
    // search right
    for (var j = xmax + 1; j < markedMatrix[0].length; j++) {
      if (!util.isGap(regions[ymin][j])) {
        var blockRight = blocks[regions[ymin][j]];
        // verify the ymin and ymax match
        if (block.ymin === blockRight.ymin && block.ymax === blockRight.ymax) {
          block.rightBlock = blockRight;
        }
        break;
      }
    }
  }
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
      if (!hasWordY[i - ymin]) {
        for (var j = xmin; j <= xmax; j++) {
          markedMatrix[i][j] = constants.GAP_VAL;
        }
      }
    }
  }
  // mark vertical gaps
  if (util.hasEnoughLenToDissect(block.xlen)) {
    for (var j = xmin; j <= xmax; j++) {
      if (!hasWordX[j - xmin]) {
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

function postProcessBlocks(matrix, blocks) {
  var resolvedBlocks = resolveOverlappingBlocks(matrix, blocks); 
  return resolvedBlocks.map(
      function(block) {
        return new obj.CharacterLocation(block);
      });
}

// might want to change the algorithm, smaller is not always better
// maybe change this to if overlap, check if similar, if so, the one with better
// ratio is used.
function resolveOverlappingBlocks(matrix, blocks) {
  var processedBlocks = [];
  
  // initialize list of sets
  var yVisited = [];
  for (var i = 0; i < matrix.length; i++) {
    yVisited.push(new Set());
  }
  var xVisited = [];
  for (var j = 0; j < matrix[0].length; j++) {
    xVisited.push(new Set());
  }
  
  // sort blocks by area size
  blocks.sort(
      function(block1, block2) {
        return block1.blockSize - block2.blockSize;
      });
  
  // iterate through blocks to find if there are any overlaps
  for (var blockIdx = 0; blockIdx < blocks.length; blockIdx++) {
    var block = blocks[blockIdx];
    var ystart = block.ymin + block.yoffset;
    var yend = block.ymax + block.yoffset;
    var xstart = block.xmin + block.xoffset;
    var xend = block.xmax + block.xoffset;
    
    // add current block to be returned if there are no overlaps
    if (!isOverlap(ystart, yend, xstart, xend, yVisited, xVisited)) {
      processedBlocks.push(block);
      // update visited
      for (var i = ystart; i <= yend; i++) {
        yVisited[i].add(blockIdx);
      }
      for (var j = xstart; j <= xend; j++) {
        xVisited[j].add(blockIdx);
      }
    }
  }
  return processedBlocks;
}

function isOverlap(ystart, yend, xstart, xend, yVisited, xVisited) {
  // get all blocks that occupy the y range from ystart to yend
  var yBlocks = new Set();
  for (var k = ystart; k <= yend; k++) {
    yVisited[k].forEach(function(a, b, c) { yBlocks.add(a); });
  }
  // get all blocks that occupy the x range from xstart to xend
  var xBlocks = new Set();
  for (var k = xstart; k <= xend; k++) {
    xVisited[k].forEach(function(a, b, c) { xBlocks.add(a); });
  }
  // find if they overlap
  return (new Set(
      Array.from(yBlocks).filter(
          function(idx) {
            return xBlocks.has(idx);
          }))
          .size > 0);
}
