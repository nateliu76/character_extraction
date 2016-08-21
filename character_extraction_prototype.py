import sys, os
import Queue
import time
from PIL import Image
from collections import deque

'''
Constants

'''
# if the current run is in debug mode or not
DEBUG_MODE = False
# the minimum threshold for the pixel to be identified as white
WHITE_COLOR = 245
# the minimum threshold for the pixel to be identified as black
BLACK_COLOR = 40
# the minimum threshold for the number of white pixels for the area to be 
# identified as a bubble
MIN_WHITE_PIX = 625
# the extra margin used when marking the area of a bubble
BUBBLE_MARGIN = 5
# the extra margin used to mark characters when printing to image
CHAR_MARGIN = 2
# the maximum ratio of the block to be considered for merging
MERGE_RATIO_THRES = 0.85
# the maximum number of blocks that can be merged to form a squarer block
MAX_BLOCK_NUM = 5
# the minimum block ratio for a it to not be dissected to more blocks
DISSECT_RATIO_THRES = 0.6
# the minimum length required for a block to be dissected further
WORD_BREAK_MIN_LEN = 30
# the minimum number of black pixels for the block to be considered valid
MIN_BLACK_PIX = 3
# the minimum block size for the block to be considered valid
MIN_BLOCK_SIZE = 8
# the maximum block size for the block to be considered valid
MAX_BLOCK_SIZE = 40000
# the maximum distance between rectangles for them to be considered in the same
# subbubble
SUBBUBBLE_BOUNDARY = 15
# the constant used to mark gaps in a matrix
GAP_COLOR = -1
# the constant used to mark pixels green in a matrix
GREEN_MARK = -2
# the constant used to mark pixels green in a matrix
RED_MARK = -3
# the 4 directions right, left, down, up.
directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
# records the number of blocks dissected
dissect_count = 0


'''
Text block class.

'''
class Text_block():
  def __init__(self, ymin, ymax, xmin, xmax, black_pix_count):
    self.ymin = ymin
    self.ymax = ymax
    self.xmin = xmin
    self.xmax = xmax
    
    self.ylen = ymax - ymin + 1
    self.xlen = xmax - xmin + 1
    self.ratio = box_ratio(self.ylen, self.xlen)
    
    self.yoffset = 0
    self.xoffset = 0
    
    self.black_pix_count = black_pix_count
    
    self.down = None
    self.right = None
    self.matched = False
    
  def is_valid_block(self):
    block_size = self.ylen * self.xlen
    valid_size = block_size < MAX_BLOCK_SIZE and block_size > MIN_BLOCK_SIZE
    return is_enough_black_pix_for_block(self.black_pix_count) and valid_size
            
  def get_boundary(self):
    return self.ymin, self.ymax, self.xmin, self.xmax
    
  def get_side_lengths(self):
    return self.ylen, self.xlen
    
  def get_ratio(self):
    return self.ratio
    
  def get_black_pix_count(self):
    return self.black_pix_count
            
  def has_word(self):
    return self.black_pix_count > 0
    
  def get_offsets(self):
    return self.yoffset, self.xoffset


'''
Given a bubble image, return a list of subbubbles.

This is done by marking the gaps within a bubble matrix, and processing the 
rectangles that are not marked as gaps.

Each subbubble consists of the subbubble matrix, ymin, and xmin.
ymin and xmin are offsets of the subbubble matrix within the bubble matrix.

'''      
def get_subbubbles_from_bubble(bubble_matrix, idx=''):
  print 'finding all subbubbles of bubble...'
  bubble_matrix_w_gaps = mark_gaps_in_matrix(bubble_matrix, idx)
  visited = \
      [[False] * len(bubble_matrix[0]) for x in xrange(len(bubble_matrix))]
  
  subbubbles = []
  for i, y in enumerate(bubble_matrix_w_gaps):
    for j, pix_val in enumerate(y):
      if not is_gap(pix_val) and not visited[i][j]:
        subbubble = get_subbubble(bubble_matrix_w_gaps, i, j, visited)
        if subbubble:
          subbubbles.append(subbubble)
          print 'found subbubble:', str(len(subbubbles))
    
  # print the boundaries of the subbubble in the image
  if DEBUG_MODE:
    subbubble_img = \
        [[100 if is_gap(pix) else pix for pix in row] \
            for row in bubble_matrix_w_gaps]
    subbubble_blocks = [subbubble_to_Text_block(sb) for sb in subbubbles]
    write_blocks_to_img(subbubble_img, subbubble_blocks)
    print_image(subbubble_img, 'subbubble_img' + idx)
    
  return subbubbles

  
'''
Processes list of subbubbles to get the blocks.

Gaps are marked for each subbubble, with further marking if certain boxes
are identified that they should be further dissected.
This can happen in the case where punctuation is introduced, and that the words
don't align well.

Blocks are merged if necessary to form squares (what most Chinese characters
are like)

Offsets for the subbubble (in relation to the bubble) are added to each block
at the end.

'''
def get_blocks_from_subbubbles(subbubbles):
  blocks = []
  for i, subbubble in enumerate(subbubbles):
    print 'processing subbubble', (i + 1)
  
    subbubble_matrix, yoffset, xoffset = subbubble
    subbubble_w_gaps = mark_gaps_in_matrix(subbubble_matrix, str(i))
    raw_blocks = convert_img_to_blocks(subbubble_w_gaps, str(i))
    processed_blocks = dissect_uneven_blocks(subbubble_w_gaps, raw_blocks)
    
    if DEBUG_MODE:
      boxes_img = \
          [[100 if is_gap(pix) else pix for pix in row] \
              for row in subbubble_w_gaps]
      write_blocks_to_img(boxes_img, processed_blocks)
      print_image(boxes_img, 'bubbles_pre_merge' + str(i))
    
    final_blocks = \
        merge_blocks_to_form_squares(subbubble_w_gaps, processed_blocks)
    
    # draw blocks on clean bubble
    if DEBUG_MODE:
      merged_blocks_img = \
          [[100 if is_gap(pix) else pix for pix in row] \
              for row in subbubble_w_gaps]
      write_blocks_to_img(merged_blocks_img, final_blocks)
      print_image(merged_blocks_img, 'final_merged_blocks' + str(i))
    
    blocks += [add_offsets(block, yoffset, xoffset) for block in final_blocks]
    
  return blocks

  
'''
Quick hack for debugging/printing, so that we can print/save the outline of a 
subbubble in an image.

'''
def subbubble_to_Text_block(subbubble):
  matrix, ymin, xmin = subbubble
  return Text_block(ymin, ymin + len(matrix), xmin, xmin + len(matrix[0]), 1)


'''
Returns the subbubble given a coordinate of the subbubble.

'''
def get_subbubble(bubble_matrix_w_gaps, ycoord, xcoord, visited):
  stack = deque([(ycoord, xcoord)])
  ymin, ymax, xmin, xmax = ycoord, ycoord, xcoord, xcoord
  ylimit = len(bubble_matrix_w_gaps)
  xlimit = len(bubble_matrix_w_gaps[0])
  black_pix_count = 0
  
  while stack:
    y, x = stack.pop()
    
    # if this rectangle is not handled yet, get the y/x min/max of the rectangle
    # and search for neighboring rectangles
    if not visited[y][x]:
      ymincurr, ymaxcurr, xmincurr, xmaxcurr = \
          get_rect_boundary(bubble_matrix_w_gaps, y, x)
      ymin = min(ymin, ymincurr)
      ymax = max(ymax, ymaxcurr)
      xmin = min(xmin, xmincurr)
      xmax = max(xmax, xmaxcurr)
      
      # Due to an edge case, it might be worth it to only include a rectangle 
      # as part of the subbubble if it contains black pixels.
      # consider this if the edge case happens where subbubbles within a bubble
      # are not divided properly
      
      for i in xrange(ymincurr, ymaxcurr + 1):
        for j in xrange(xmincurr, xmaxcurr + 1):
          visited[i][j] = True
          if is_black_pixel(bubble_matrix_w_gaps[i][j]):
            black_pix_count += 1
      
      # search for neighboring rectangles
      # since all neighboring rectangles have the same length, starting from
      # the middle should suffice
      xmid = xmincurr + (xmaxcurr - xmincurr) / 2
      ymid = ymincurr + (ymaxcurr - ymincurr) / 2
      
      # search up
      for count in xrange(1, SUBBUBBLE_BOUNDARY + 1):
        yn = ymincurr - count
        if yn < 0:
          break
        if not is_gap(bubble_matrix_w_gaps[yn][xmid]):
          stack.append((yn, xmid))
          break
      # search down
      for count in xrange(1, SUBBUBBLE_BOUNDARY + 1):
        yn = ymaxcurr + count
        if yn >= ylimit:
          break
        if not is_gap(bubble_matrix_w_gaps[yn][xmid]):
          stack.append((yn, xmid))
          break
      # search left
      for count in xrange(1, SUBBUBBLE_BOUNDARY + 1):
        xn = xmincurr - count
        if xn < 0:
          break
        if not is_gap(bubble_matrix_w_gaps[ymid][xn]):
          stack.append((ymid, xn))
          break
      # search right
      for count in xrange(1, SUBBUBBLE_BOUNDARY + 1):
        xn = xmaxcurr + count
        if xn >= xlimit:
          break
        if not is_gap(bubble_matrix_w_gaps[ymid][xn]):
          stack.append((ymid, xn))
          break
          
  if is_enough_black_pix_for_block(black_pix_count):
    # copy the subbubble portion of the image into its own matrix
    subbubble_matrix = [[bubble_matrix_w_gaps[i][j] \
                        if not is_gap(bubble_matrix_w_gaps[i][j]) else 255 \
                                      for j in xrange(xmin, xmax + 1)] \
                                      for i in xrange(ymin, ymax + 1)]
    
    return subbubble_matrix, ymin, xmin


'''
Given a coordinate of a rectangle in an image matrix with gaps marked, find the
rectangle's ymin, ymax, xmin, xmax.

'''
def get_rect_boundary(bubble_matrix_w_gaps, y, x):
  ylimit = len(bubble_matrix_w_gaps)
  xlimit = len(bubble_matrix_w_gaps[0])
  # find ymin
  yn = y
  while yn - 1 >= 0 and not is_gap(bubble_matrix_w_gaps[yn - 1][x]):
    yn -= 1
  ymin = yn
  # find ymax
  yn = y
  while yn + 1 < ylimit and not is_gap(bubble_matrix_w_gaps[yn + 1][x]):
    yn += 1
  ymax = yn
  # find xmin
  xn = x
  while xn - 1 >= 0 and not is_gap(bubble_matrix_w_gaps[y][xn - 1]):
    xn -= 1
  xmin = xn
  # find xmax
  xn = x
  while xn + 1 < xlimit and not is_gap(bubble_matrix_w_gaps[y][xn + 1]):
    xn += 1
  xmax = xn
  return ymin, ymax, xmin, xmax

  
'''
Dissect blocks into smaller blocks if necessary (height width ratio is below 
threshold).

Returns the list of processed blocks.

'''
def dissect_uneven_blocks(matrix_w_gaps, blocks):
  global dissect_count
  final_blocks = []
  
  for block in blocks:
    if should_further_dissect_block(block.ratio):
      dissect_count += 1
      # get blocks from within the original block
      mark_gaps_in_block_to_matrix(matrix_w_gaps, block)
      dissected_blocks = convert_img_within_block_to_blocks(matrix_w_gaps, block)
      final_blocks += dissected_blocks
    else:
      final_blocks.append(block)
      
  return final_blocks
  
  
'''
Identifies blocks to merge so that they are all as close to a square as 
possible and tries to merge them.

Returns the list of merged blocks.

'''
def merge_blocks_to_form_squares(matrix_w_gaps, blocks):
  mark_adj_blocks(blocks, matrix_w_gaps)
  final_blocks = []
  for block in blocks:
    if block.matched or not block.has_word():
      continue
    if should_try_merging(block.ratio):
      block = merge_w_nearby_blocks(block)
      
    if block.is_valid_block():
      final_blocks.append(block)
      
  return final_blocks
  
  
'''
Marks the locations of the image where the words don't exist.
This is done by marking the x coordinates and y coordinates in which black 
pixels don't exist.

The marked locations are called "gaps".

Returns the matrix with marked gaps.

'''
def mark_gaps_in_matrix(matrix, idx):
  print 'marking gaps...'
  matrix_w_gaps = [list(x) for x in matrix]
  vert_has_word = [False] * len(matrix)
  horz_has_word = [False] * len(matrix[0])
  
  for i, y in enumerate(matrix):
    for j, x in enumerate(y):
      if is_black_pixel(x):
        vert_has_word[i] = True
        horz_has_word[j] = True
        
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if not vert_has_word[i] or not horz_has_word[j]:
        matrix_w_gaps[i][j] = GAP_COLOR
  
  if DEBUG_MODE:
    gaps_marked = [list(x) for x in matrix]
    for i in xrange(len(matrix)):
      for j in xrange(len(matrix[0])):
        if not vert_has_word[i] or not horz_has_word[j]:
          gaps_marked[i][j] = 100
    print_image(gaps_marked, 'gaps_marked' + idx)
    
  return matrix_w_gaps

  
'''
Same as the function mark_gaps_in_matrix(), but for within a Text_block only.

Instead of returning the image, it modifies it directly.

'''
def mark_gaps_in_block_to_matrix(matrix, block):
  ymin, ymax, xmin, xmax, = block.get_boundary()
  ylen, xlen = block.get_side_lengths()
  vert_has_word = [0] * ylen
  horz_has_word = [0] * xlen
  
  for i in xrange(ymin, ymax + 1):
    for j in xrange(xmin, xmax + 1):
      if is_black_pixel(matrix[i][j]) and not is_gap(matrix[i][j]):
        vert_has_word[i - ymin] = 1
        horz_has_word[j - xmin] = 1
        
  if ylen > WORD_BREAK_MIN_LEN:
    for i in xrange(ymin, ymax + 1):
        if vert_has_word[i - ymin] == 0:
          for j in xrange(xmin, xmax + 1):
            matrix[i][j] = GAP_COLOR
  
  if xlen > WORD_BREAK_MIN_LEN:
    for j in xrange(xmin, xmax + 1):
        if horz_has_word[j - xmin] == 0:
          for i in xrange(ymin, ymax + 1):
            matrix[i][j] = GAP_COLOR
  
  
'''
Converts image with gaps marked to blocks.

'''
def convert_img_to_blocks(matrix_w_gaps, idx=''):
  processed = [[False] * len(matrix_w_gaps[0]) \
              for x in xrange(len(matrix_w_gaps))]
  blocks = []
  for i, row in enumerate(matrix_w_gaps):
    for j, pix in enumerate(row):
      if not is_gap(pix) and not processed[i][j]:
        block = get_block_parameters(matrix_w_gaps, i, j, processed)
        blocks.append(block)
      
  if DEBUG_MODE:
    boxes_img = [[100 if is_gap(pix) else pix for pix in row] \
                                  for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, blocks)
    print_image(boxes_img, 'boxes_preliminary' + idx)
      
  return blocks
  
  
'''
Same as the function convert_img_to_blocks(), but for within a block only.

'''
def convert_img_within_block_to_blocks(matrix_w_gaps, old_block):
  ymin, ymax, xmin, xmax = old_block.get_boundary()
  processed = [[False] * (xmax - xmin + 1) for x in xrange(ymax - ymin + 1)]
  blocks = []
  for i in xrange(ymin, ymax + 1):
    for j in xrange(xmin, xmax + 1):
      if not is_gap(matrix_w_gaps[i][j]) and not processed[i - ymin][j - xmin]:
        block = get_block_parameters(matrix_w_gaps, i, j, processed, ymin, xmin)
        blocks.append(block)
      
  return blocks

  
'''
Mark which blocks are below or to the right of the block. This information will
be used for merging blocks.

'''
def mark_adj_blocks(blocks, matrix_w_gaps):
  DEFAULT_VAL = -1
  regions = [[DEFAULT_VAL] * len(matrix_w_gaps[0]) for x in xrange(len(matrix_w_gaps))]
  
  # first pass, mark idx for different blocks
  for idx, block in enumerate(blocks):
    ymin, ymax, xmin, xmax = block.get_boundary()
    yoffset, xoffset = block.get_offsets()
    # actually we only need to mark the borders of the block, and not the entire
    # matrix, not sure if it gains us any performance though
    for i in xrange(ymin + yoffset, ymax + yoffset + 1):
      for j in xrange(xmin + xoffset, xmax + xoffset + 1):
        regions[i][j] = idx
  
  # second pass, mark the blocks that are to the current block's right/down
  for block in blocks:
    ymin, ymax, xmin, xmax = block.get_boundary()
    yoffset, xoffset = block.get_offsets()
    ymid = (ymin + ymax) / 2 + yoffset
    xmid = (xmin + xmax) / 2 + xoffset
    # search right
    right_idx = -1
    for j in xrange(xmax + xoffset + 1, len(matrix_w_gaps[0])):
      if regions[ymid][j] != DEFAULT_VAL:
        right_idx = regions[ymid][j]
        break
    if right_idx != -1:
      r_block = blocks[right_idx]
      if r_block.ymax == block.ymax and r_block.ymin == block.ymin:
        block.right = r_block
    # search down
    down_idx = -1
    for i in xrange(ymax + yoffset + 1, len(matrix_w_gaps)):
      if regions[i][xmid] != DEFAULT_VAL:
        down_idx = regions[i][xmid]
        break
    if down_idx != -1:
      d_block = blocks[down_idx]
      if d_block.xmax == block.xmax and d_block.xmin == block.xmin:
        block.down = d_block


'''
Depending on if the width or height is larger, try to merge the block with the
block below it, or the block to the right of it.
If the width height ratio is better than the original after merging, merge the
blocks, and continue to try merging in that direction.

The maximum number of boxes that can be merged is marked by MAX_BLOCK_NUM.

The offsets are added to the final merged block since those parameters are lost 
when constructing the new block.

'''
def merge_w_nearby_blocks(block):
  ymin, ymax, xmin, xmax = block.get_boundary()
  ylen, xlen = block.get_side_lengths()
  ratio = block.get_ratio()
  black_pix_count = block.get_black_pix_count()
  
  if ylen > xlen:
    # try merging with block(s) to the right
    r_block = block.right
    for i in xrange(MAX_BLOCK_NUM):
      if not r_block:
        break
      ymin1, ymax1, xmin1, xmax1 = r_block.get_boundary()
      ratio1 = r_block.get_ratio()
      black_pix_count1 = r_block.get_black_pix_count()
      new_ratio = box_ratio(ylen, xlen + xmax1 - xmax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        xlen += xmax1 - xmax
        xmax = xmax1
        black_pix_count += black_pix_count1
        r_block.matched = True
        r_block = r_block.right
      else:
        break
  else:
    # try merging with block(s) below
    d_block = block.down
    for i in xrange(MAX_BLOCK_NUM):
      if not d_block:
        break
      ymin1, ymax1, xmin1, xmax1 = d_block.get_boundary()
      ratio1 = d_block.get_ratio()
      black_pix_count1 = d_block.get_black_pix_count()
      new_ratio = box_ratio(xlen, ylen + ymax1 - ymax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        ylen += ymax1 - ymax
        ymax = ymax1
        black_pix_count += black_pix_count1
        d_block.matched = True
        d_block = d_block.down
      else:
        break
  
  final_block = Text_block(ymin, ymax, xmin, xmax, black_pix_count)
                      
  return add_offsets(final_block, block.yoffset, block.xoffset)


'''
Returns the width height ratio of the block.

'''
def box_ratio(ylen, xlen):
  return float(min(xlen, ylen)) / max(xlen, ylen)


'''
Marks the boundaries of the blocks, for printing/saving later.

'''
def write_blocks_to_img(matrix, blocks):
  for block in blocks:
    ymin, ymax, xmin, xmax = block.get_boundary()
    yoffset, xoffset = block.get_offsets()
    # we might not need this check
    if block.has_word():
      ystart = max(0, ymin - CHAR_MARGIN + yoffset)
      yend = min(len(matrix) - 1, ymax + CHAR_MARGIN + yoffset)
      xstart = max(0, xmin - CHAR_MARGIN + xoffset)
      xend = min(len(matrix[0]) - 1, xmax + CHAR_MARGIN + xoffset)
      for i in xrange(ystart, yend + 1):
        matrix[i][xstart] = GREEN_MARK
        matrix[i][xend] = GREEN_MARK
      for j in xrange(xstart, xend + 1):
        matrix[ystart][j] = GREEN_MARK
        matrix[yend][j] = GREEN_MARK


'''
Given the top left coordinate of the block, find the parameters of the block,
and return the block in the Text_block class.

'''
def get_block_parameters(
    matrix, ycoord, xcoord, processed, yoffset=0, xoffset=0):
  blk_pix_cnt = 0
  
  '''
  Note: 
  i think there might be a bug here, the block boundary will stop once
  there is a gap on y axis even if it is only 1 pixel deep, this is because
  the x axis pointer will determine that it has reached the boundary.
  '''
  i = ycoord
  while y_not_reached_boundary(matrix, i, xcoord):
    j = xcoord
    while x_not_reached_boundary(matrix, i, j):
      processed[i - yoffset][j - xoffset] = True
      if is_black_pixel(matrix[i][j]):
        blk_pix_cnt += 1    
      j += 1
    i += 1
  
  ymax = i - 1
  xmax = j - 1
  return Text_block(ycoord, ymax, xcoord, xmax, blk_pix_cnt)


'''
Returns true if found a gap that is at least 2 pixels in the y axis direction.

'''
def y_not_reached_boundary(matrix, i, j):
  if i < len(matrix) - 1:
    return not is_gap(matrix[i][j]) or not is_gap(matrix[i + 1][j])
  else:
    return i < len(matrix) and not is_gap(matrix[i][j])
  

'''
Returns true if found a gap that is at least 2 pixels in the x axis direction.

'''  
def x_not_reached_boundary(matrix, i, j):
  if j < len(matrix[0]) - 1:
    return not is_gap(matrix[i][j]) or not is_gap(matrix[i][j + 1])
  else:
    return j < len(matrix[0]) and not is_gap(matrix[i][j])
  

'''
Currently used mainly for debug.

Runs BFS around given coordinate to find nearby bubble and uses flood fill to 
find the boundaries of the nearby bubble.

This function was initially meant to simulate a mouse click on a given 
coordinate on an image, which would kickstart the process of finding the bubble
around that coordinate, and circle the words in that bubble.

'''
def search_for_bubble_near_given_coord(matrix, ycoord, xcoord):
  print "Running BFS around (%d, %d) + flood fill..." % (ycoord, xcoord)
  q = Queue.Queue()
  q.put((ycoord, xcoord))
  visited = set()
  visited.add((ycoord, xcoord))
  matrix_bounds = (0, len(matrix) - 1, 0, len(matrix[0]) - 1)
  
  visited_white_pix = [[0] * len(matrix[0]) for x in xrange(len(matrix))]
  bubble_search_idx = 0
  
  while not q.empty():
    y, x = q.get()
    
    if is_white_pixel(matrix[y][x]) and not visited_white_pix[y][x]:
      bubble_search_idx += 1
      bubble_white_pix_count, bubble_boundary = \
          get_bubble_parameters(
              matrix, y, x, visited_white_pix, bubble_search_idx)
      if is_enough_white_pix_for_bubble(bubble_white_pix_count):
        break
        
    # visited needs to have only the non white pixels
    for i, j in directions:
      next_pix = (y + i, x + j)
      if is_in_bounds(next_pix, matrix_bounds) and next_pix not in visited \
          and not visited_white_pix[y + i][x + j]:
        q.put(next_pix)
        visited.add(next_pix)
  
  ymin, ymax, xmin, xmax = bubble_boundary
  is_white_pix_of_bubble = \
      [[visited_white_pix[i][j] == bubble_search_idx \
          for j in xrange(xmin, xmax + 1)] \
          for i in xrange(ymin, ymax + 1)]
  
  bubble_parameters = \
      get_clear_image_w_text(matrix, bubble_boundary, is_white_pix_of_bubble)
  
  bubble, black_pix_count, offsets = bubble_parameters
  if bubble and is_enough_black_pix_for_block(black_pix_count):
    subbubbles = get_subbubbles_from_bubble(bubble)
    get_blocks_from_subbubbles(subbubbles)
  else:
    print 'No bubble found with given coordinates'


'''
Searches the entire image for Chinese characters, and circles them with the
Text_block class.

This is done is by running the single bubble finding algorithm on all
white pixels in the image, with heuristics to determine if the region is a text
bubble.

Note that there will be false positives (regions identified as Chinese 
characters, but are actually not), but that is fine for the purpose of this
program.

Does the following in order
 - Get all bubbles using bubble finding algorithm
 - Get all subbubbles within each bubble
 - Get all the blocks within each subbubble

Saves the image with all characters marked for debug.

Prints out performance related timing info as well.

Note that at each step, offsets need to be added, this is because:
 - Need offsets for bubble in relation to the image
 - Need offsets for the tightened bubble in relation to the original bubble
 - Need offsets for the subbubble in relation to the bubble

'''
def get_all_blocks_in_image(matrix):
  start_time = time.time()
  
  visited_white_pix = [[0] * len(matrix[0]) for x in xrange(len(matrix))]
  bubble_count = 0
  bubble_matrices_w_offsets = []
  bubble_search_idx = 0
  
  # find all bubbles in the image
  print 'Searching for bubbles...'
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
    
      if is_white_pixel(pix) and not visited_white_pix[i][j]:
        # need to use set here instead of visited_white_pix or else we risk of
        # getting characters from other bubbles that are included in the current
        # boundary
        bubble_search_idx += 1
        bubble_white_pix_count, bubble_boundary = \
            get_bubble_parameters(
                matrix, i, j, visited_white_pix, bubble_search_idx)
        
        if is_enough_white_pix_for_bubble(bubble_white_pix_count):
          ymin, ymax, xmin, xmax = bubble_boundary
          is_white_pix_of_bubble = \
              [[visited_white_pix[y][x] == bubble_search_idx \
                  for x in xrange(xmin, xmax + 1)] \
                  for y in xrange(ymin, ymax + 1)]
          
          print '\ngetting clear image of text...'
          bubble_and_parameters = \
              get_clear_image_w_text(matrix, bubble_boundary, \
                                     is_white_pix_of_bubble, str(bubble_count))
          bubble_matrix, black_pix_count, offsets = bubble_and_parameters
          
          if bubble_matrix and is_enough_black_pix_for_block(black_pix_count):
            print '%dth bubble found' % (bubble_count + 1)
            print 'Bubble found at:', bubble_boundary, 'from:', (i, j)
            bubble_count += 1
            yoffset, xoffset = get_bubble_offsets(offsets, bubble_boundary)
            bubble_matrices_w_offsets.append((bubble_matrix, yoffset, xoffset))
            
  get_bubble_instant = time.time()
  get_bubble_time = get_bubble_instant - start_time
  
  # process all bubbles to get subbubbles
  print '\nprocessing all bubbles...'
  subbubbles = []
  for i, bubble_matrix_w_offsets in enumerate(bubble_matrices_w_offsets):
    bubble_matrix, yoffset, xoffset = bubble_matrix_w_offsets
    raw_subbubbles = get_subbubbles_from_bubble(bubble_matrix, str(i))
    subbubbles += \
        [add_subbubble_offsets(sb, yoffset, xoffset) for sb in raw_subbubbles]
  
  print '\ntotal amount of bubbles:', len(bubble_matrices_w_offsets)
  print 'total amount of subbubbles:', len(subbubbles)
  process_bubble_instant = time.time()
  process_bubble_time = process_bubble_instant - get_bubble_instant
  
  # process all subbubbles to get blocks
  processed_blocks = get_blocks_from_subbubbles(subbubbles)
  
  process_subbubble_instant = time.time()
  process_subbubble_time = process_subbubble_instant - process_bubble_instant
  
  # resolve overlapping blocks
  print "\nresolving overlapping blocks..."
  final_blocks = resolve_overlapping_blocks(matrix, processed_blocks)
  
  print '\nfinal step, printing image...'
  final_img = [list(x) for x in matrix]
  write_blocks_to_img(final_img, final_blocks)
  print_image(final_img, 'final_img')
  
  # print performance related timings
  print '\nget bubbles from image time:', get_bubble_time
  print '\nget subbubbles from bubbles time:', process_bubble_time
  print '\nget blocks from subbubbles time:', process_subbubble_time
  print '\ndissect count:', dissect_count
  print 
  
  # debug print
  if DEBUG_MODE:
    print_bubbles(bubble_matrices_w_offsets)
    print_subbubbles(subbubbles)
  
  
'''
Prints images of individual bubbles.

'''
def print_bubbles(bubbles):
  for i, bubble_matrix_w_offsets in enumerate(bubbles):
    bubble_matrix, yoffset, xoffset = bubble_matrix_w_offsets
    print_image(bubble_matrix, 'bubble' + str(i))
  

'''
Prints images of individual subbubbles.

'''  
def print_subbubbles(subbubbles):
  for i, subbubble in enumerate(subbubbles):
    matrix, ymin, ymax = subbubble
    print_image(matrix, 'subbubble' + str(i))
  
  
'''
Convenience method to add bubble offsets to subbubble offsets, and wrap them all
in a tuple.

'''
def add_subbubble_offsets(subbubble, yoffset, xoffset):
  subbubble_matrix, yoffset1, xoffset1 = subbubble
  return subbubble_matrix, yoffset + yoffset1, xoffset + xoffset1
  
  
'''
Convenience method to add offsets to a block.

'''
def add_offsets(block, yoffset, xoffset):
  block.yoffset += yoffset
  block.xoffset += xoffset
  return block
  
  
'''
There are two sets of offsets in play here:
 - the offset from the original image to the bubble
 - the offset from the original bubble to the tightened bubble

This method adds the two offsets together

'''
def get_bubble_offsets(tightened_bubble_additional_offsets, original_bubble_boundary):
  yoffset, xoffset = tightened_bubble_additional_offsets
  ymin, ymax, xmin, xmax = original_bubble_boundary
  yoffset += ymin
  xoffset += xmin
  return yoffset, xoffset


'''
For overlapping blocks, favor the smaller block over the larger block.

'''
def resolve_overlapping_blocks(matrix, blocks):
  final_blocks = []
  
  # each block is given an index. and the index is inserted to the list of
  # sets that correspond to where the block is.
  yvisited = [set() for i in xrange(len(matrix))]
  xvisited = [set() for i in xrange(len(matrix[0]))]
  
  # sort blocks from small to large in terms of area
  blocks.sort(key = lambda x: x.ylen * x.xlen)
  
  for n, block in enumerate(blocks):
    ymin, ymax, xmin, xmax = block.get_boundary()
    yoffset, xoffset = block.get_offsets()
    ystart = yoffset + ymin
    yend = yoffset + ymax
    xstart = xoffset + xmin
    xend = xoffset + xmax
    
    # if no overlap, add block to visited, and append to final list of blocks
    if not is_overlap(ystart, yend, xstart, xend, yvisited, xvisited):
      final_blocks.append(block)
      for i in xrange(ystart, yend + 1):
        yvisited[i].add(n)
      for i in xrange(xstart, xend + 1):
        xvisited[i].add(n)
  
  return final_blocks
  
  
'''
If both yvisited and xvisited contain the same index in the range specified,
that means that the current block defined by the y/x min/max overlaps with the
block with that index.

'''
def is_overlap(ystart, yend, xstart, xend, yvisited, xvisited):
  yoverlap = set()
  xoverlap = set()
  for i in xrange(ystart, yend + 1):
    yoverlap |= yvisited[i]
  for i in xrange(xstart, xend + 1):
    xoverlap |= xvisited[i]
    
  return len(yoverlap & xoverlap) > 0


'''
Extracts the part of the image with text.

Marks the background to extract the text portion only, and in the end 
return the tightened bubble.

'''
def get_clear_image_w_text(matrix, boundary, visited_white_pix, idx=''):
  print "Running 2nd flood fill from corners"
  
  background_pixels = get_background_pixels(visited_white_pix, boundary, matrix)
  
  ymin, ymax, xmin, xmax = boundary
  clean_bubble = \
      [[255 if background_pixels[i - ymin][j - xmin] else matrix[i][j] \
          for j in xrange(xmin, xmax + 1)] \
          for i in xrange(ymin, ymax + 1)]
  
  if DEBUG_MODE:
    original_bubble = \
        [[matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                       for i in xrange(ymin, ymax + 1)]
    bubble_w_marked_white_pix = \
        [[GREEN_MARK if visited_white_pix[i - ymin][j - xmin] else matrix[i][j] 
            for j in xrange(xmin, xmax + 1)] \
            for i in xrange(ymin, ymax + 1)]
    bubble_w_marked_background = \
        [[GREEN_MARK if background_pixels[i - ymin][j - xmin] else matrix[i][j]\
           for j in xrange(xmin, xmax + 1)] \
           for i in xrange(ymin, ymax + 1)]
    print_image(original_bubble, 'original_block' + idx)
    print_image(bubble_w_marked_white_pix, 'bubble_w_marked_white_pix' + idx)
    print_image(bubble_w_marked_background, 'bubble_w_marked_background' + idx)
    print_image(clean_bubble, 'clean_block' + idx)
  
  return tighten_bubble_boundary(clean_bubble, idx)

  
'''
Tightens the bubble by cropping out the space in the border that do not contain
black pixels (necessary for a valid character).

Returns the tightened bubble as well as the number of black pixels and the
x and y offset of the tightened bubble in the original image.

'''
def tighten_bubble_boundary(bubble_matrix, idx):
  print "Cropping extra white space..."
  xmin = len(bubble_matrix[0])
  xmax = -1
  ymin = len(bubble_matrix)
  ymax = -1
  black_pix_count = 0
  
  for i in xrange(len(bubble_matrix)):
    for j in xrange(len(bubble_matrix[0])):
      if is_black_pixel(bubble_matrix[i][j]):
        black_pix_count += 1
        if i < ymin:
          ymin = i
        if i > ymax:
          ymax = i
        if j < xmin:
          xmin = j
        if j > xmax:
          xmax = j
  
  xmin = xmin - (BUBBLE_MARGIN if xmin >= BUBBLE_MARGIN else 0)
  xmax = xmax \
      + (BUBBLE_MARGIN if xmax + BUBBLE_MARGIN < len(bubble_matrix[0]) else 0)
  ymin = ymin - (BUBBLE_MARGIN if ymin >= BUBBLE_MARGIN else 0)
  ymax = ymax \
      + (BUBBLE_MARGIN if ymax + BUBBLE_MARGIN < len(bubble_matrix) else 0)
  
  tightened_bubble = [[bubble_matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                                           for i in xrange(ymin, ymax + 1)]
  
  if DEBUG_MODE:
    box = [list(x) for x in bubble_matrix]
    block = Text_block(ymin, ymax, xmin, xmax, 1)
    write_blocks_to_img(box, [block])
    print_image(box, 'box_lines' + idx)
    print_image(tightened_bubble, 'tightened_bubble' + idx)
  
  return tightened_bubble, black_pix_count, (ymin, xmin)
  
  
'''
Gets all the background pixels that are not part of the bubble.

'''
def get_background_pixels(visited_white_pix, boundary, matrix):
  ymin, ymax, xmin, xmax = boundary
  yhi = ymax - ymin
  xhi = xmax - xmin
  
  is_background = [[False] * (xhi + 1) for x in xrange(yhi + 1)]
  # run flood fill from the boundaries
  for i in xrange(xhi + 1):
    if not is_background[0][i] and not visited_white_pix[0][i]:
      flood_fill_backgroud(visited_white_pix, is_background, boundary, 0, i)
    if not is_background[yhi][i] and not visited_white_pix[yhi][i]:
      flood_fill_backgroud(visited_white_pix, is_background, boundary, yhi, i)
      
  for i in xrange(yhi + 1):
    if not is_background[i][0] and not visited_white_pix[i][0]:
      flood_fill_backgroud(visited_white_pix, is_background, boundary, i, 0)
    if not is_background[i][xhi] and not visited_white_pix[i][xhi]:
      flood_fill_backgroud(visited_white_pix, is_background, boundary, i, xhi) 

  return is_background

  
'''
Runs flood fill to get all pixels that are the background of the bubble.

Note that this is considered to be a part of the program that eats up a lot of
the processing time, therefore all operations within the loop need to be
as performant as possible. Hence for less cleaner code.

'''
def flood_fill_backgroud(
    visited_white_pix, is_background, boundary, ycoord, xcoord):
  ymin, ymax, xmin, xmax = boundary
  stack = deque([(ycoord, xcoord)])
  is_background[ycoord][xcoord] = True
  
  ylimit = ymax - ymin
  xlimit = xmax - xmin
  
  while stack:
    y, x = stack.pop()
    ylo = y - 1
    yhi = y + 1
    xlo = x - 1
    xhi = x + 1
    
    if ylo >= 0 and not visited_white_pix[ylo][x] and not is_background[ylo][x]:
      stack.append((ylo, x))
      is_background[ylo][x] = True
        
    if yhi <= ylimit and not visited_white_pix[yhi][x] \
                     and not is_background[yhi][x]:
      stack.append((yhi, x))
      is_background[yhi][x] = True
        
    if xlo >= 0 and not visited_white_pix[y][xlo] and not is_background[y][xlo]:
      stack.append((y, xlo))
      is_background[y][xlo] = True
        
    if xhi <= xlimit and not visited_white_pix[y][xhi] \
                     and not is_background[y][xhi]:
      stack.append((y, xhi))
      is_background[y][xhi] = True
    
    
'''
Gets the white pixel count, the boundaries of the bubble, as well as mark the
white pixels in the 2d list visited_white_pix.

This is done by using flood fill, note that this part also needs to be 
performant, and therefore might have less cleaner code.

'''
def get_bubble_parameters(
    matrix, ycoord, xcoord, visited_white_pix, search_idx):
  ymin, ymax, xmin, xmax = ycoord, ycoord, xcoord, xcoord
  stack = deque([(ycoord, xcoord)])
  visited_white_pix[ycoord][xcoord] = search_idx
  white_pix_count = 1
  
  while stack:
    y, x = stack.pop()
    
    if y < ymin:
      ymin = y
    if y > ymax:
      ymax = y
    if x < xmin:
      xmin = x
    if x > xmax:
      xmax = x
    
    ylo = y - 1
    yhi = y + 1
    xlo = x - 1
    xhi = x + 1
    
    if ylo >= 0 and is_white_pixel(matrix[ylo][x]) \
                and not visited_white_pix[ylo][x]:
      stack.append((ylo, x))
      visited_white_pix[ylo][x] = search_idx
      white_pix_count += 1
      
    if yhi < len(matrix) and is_white_pixel(matrix[yhi][x]) \
                         and not visited_white_pix[yhi][x]:
      stack.append((yhi, x))
      visited_white_pix[yhi][x] = search_idx
      white_pix_count += 1
      
    if xlo >= 0 and is_white_pixel(matrix[y][xlo]) \
                and not visited_white_pix[y][xlo]:
      stack.append((y, xlo))
      visited_white_pix[y][xlo] = search_idx
      white_pix_count += 1
      
    if xhi < len(matrix[0]) and is_white_pixel(matrix[y][xhi]) \
                            and not visited_white_pix[y][xhi]:
      stack.append((y, xhi))
      visited_white_pix[y][xhi] = search_idx
      white_pix_count += 1
        
  return white_pix_count, (ymin, ymax, xmin, xmax)

        
'''
Checks if the given corrdinate is in bounds.
For performance reasons, not used when doing flood fill since this requiring
4 checks instead of 1.

'''
def is_in_bounds(coord, limits):
  i, j = coord
  ymin, ymax, xmin, xmax = limits
  return i >= ymin and i <= ymax and j >= xmin and j <= xmax
  
  
'''
Util method for determining if a pixel is black.

'''
def is_black_pixel(val):
  return val <= BLACK_COLOR and val >= 0


'''
Util method for determining if a pixel is white.

'''
def is_white_pixel(val):
  return val >= WHITE_COLOR and val <= 255
  

'''
Util method for determining if a pixel is part of the marked gap.

'''
def is_gap(val):
  return val == -1

  
'''
Util method for determining if the number of white pixels is enough to be a 
bubble.

'''
def is_enough_white_pix_for_bubble(white_pixel_count):
  return white_pixel_count > MIN_WHITE_PIX


'''
Util method for determining if the number of black pixels is enough to be a 
block containing a character.

'''
def is_enough_black_pix_for_block(black_pixel_count):
  return black_pixel_count > MIN_BLACK_PIX
  
  
'''
Util method for determining if a block should be further dissected.

'''
def should_further_dissect_block(ratio):
  return ratio <= DISSECT_RATIO_THRES
  

'''
Util method for determining if a block should be tried for merging with other
blocks.

'''  
def should_try_merging(ratio):
  return ratio < MERGE_RATIO_THRES
  
  
'''
Saves processed image matrix to image.

'''
def print_image(matrix, fname):
  blk = (0, 0, 0)           # color black
  wht = (255, 255, 255)     # color white
  grn = (0, 255, 0)
  red = (255, 0, 0)
  
  pixels = [grn if x == GREEN_MARK else red if x == RED_MARK else (x, x, x) 
              for row in matrix for x in row]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  im2.putdata(pixels)
  im2.save(fname + '.png', "PNG")
  
  
def get_pixels_vals_from_image(im):
  # convert to gray scale
  im = im.convert("L")
  
  pixels = list(im.getdata())
  width, height = im.size
  
  # convert to list to 2D list
  return [pixels[i * width:(i + 1) * width] for i in xrange(height)]

  
'''
MAIN

Calls either search_for_bubble_near_given_coord() or get_all_blocks_in_image()
depending on the arguments.

'''
def main():
  global DEBUG_MODE
  
  start_time = time.time()
  print 'starting to record time...'
  
  args = sys.argv[1:]
  filename = args[0]
  print "Reading image file..."
  try:
    im = Image.open(filename)
  except IOError:
    print "Error in file name"
    sys.exit()
  
  pixels = get_pixels_vals_from_image(im)
  
  if len(args) >= 3:
    DEBUG_MODE = True
    x, y = int(args[1]), int(args[2])
    search_for_bubble_near_given_coord(pixels, y, x)
  else:
    get_all_blocks_in_image(pixels)
    
  print 'total run time:', (time.time() - start_time)


if __name__ == '__main__':
  main()
