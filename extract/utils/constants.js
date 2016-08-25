// Constants for different files

module.exports = {
  // enables debug print for:
  // extractCharacterLocations.js, marks locations of the bubbles, subbubles, and 
  // characterLocations on the full image
  IS_DEBUG_PRINT_ALL_IN_FULL_IMG: true,
  // processMatrix.js
  IS_DEBUG_PRINT_PROCESS_MATRIX: false,
  // processBubble.js
  IS_DEBUG_PRINT_PROCESS_BUBBLE:false,
  // processSubbubble.js
  IS_DEBUG_PRINT_PROCESS_SUBBUBBLE: false,
  
  // pixel values of the corresponding color
  BLACK_COLOR: 0,
  WHITE_COLOR: 255,
  
  // the threshold values in which we determine if a pixel is of a certain color
  // black if pixVal < BLACK_COLOR_THRES
  BLACK_COLOR_THRES: 60,
  // white if pixVal > WHITE_COLOR_THRES
  WHITE_COLOR_THRES: 235,
  
  // the minimum/maximum size that's valid for a block
  MIN_BLOCK_SIZE: 8,
  MAX_BLOCK_SIZE: 40000,
  
  // the min of the amount of black/white pixels in order for an area to be
  // recongnized as a block
  BLOCK_MIN_WHITE_PIX_COUNT: 625,
  BLOCK_MIN_BLACK_PIX_COUNT: 4,
  
  // values used to iterate over for BFS/DFS
  Y_COORDS: [1, -1, 0, 0],
  X_COORDS: [0, 0, 1, -1],
  
  // value used to mark a pixel as a gap
  GAP_VAL: -1,
  // the amount of pixels needed
  SUBBUBBLE_BOUNDARY: 15,
  // the minimum length in terms of pixels needed to dissect/mark gaps within a
  // block
  WORD_BREAK_MIN_LEN: 30,
  // the minimum y/x or x/y ratio needed to dissect/mark gaps within a block
  DISSECT_RATIO_THRES: 0.6,
  // the y/x or x/y ratio needed to not be merged with nearby blocks
  MERGE_RATIO_THRES: 0.85,
  // the maximum amont of merges that can happen for a block merge action
  MAX_MERGE_NUM: 5
};
