import sys, os
import Queue
from PIL import Image

'''
Current flow
  1. detect bubble
  2. extract text from bubble
  3. crop extra white border
  4. mark the "gaps" (white space between words)
  5. find bubbles
  6. find subbubbles for each bubble
  7. convert all subbubbles into blocks
      - find and mark gaps
      - break down gaps into boxes
      - further breakdown certain boxes
      - merge blocks to form squares
  8. make sure all bubbles have no overlap with each other, if overlap occurs,
     favor the smaller bubble and delete the larger one.

TODO:
  Possible improvements:
     - better filtering so light colored parts don't get cropped off?
    
    Other improvements:
     - add performance measurement
     - add comments

'''

DBG = 0
WHITE_COLOR = 245
BLACK_COLOR = 40
MIN_WHITE_PIX = 625
THRES = 128
BUBBLE_MARGIN = 5
CHAR_MARGIN = 2
RATIO_THRES = 0.85
MAX_BOX_NUM = 5
BLACK_PIX_THRES = 20
DISSECT_NUM = 1
DISSECT_RATIO_THRES = 0.6
WORD_BREAK_MIN_LEN = 30
MIN_BLACK_PIX = 3
MIN_BLOCK_SIZE = 8
MAX_BLOCK_SIZE = 40000
SUBBUBBLE_BOUNDARY = 15
GAP_COLOR = -1
GREEN_MARK = -2
RED_MARK = -3

directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

'''
Text block class.

'''
class Text_block():
  def __init__(self, ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt):
    self.ymin = ymin
    self.ymax = ymax
    self.xmin = xmin
    self.xmax = xmax
    self.ylen = ylen
    self.xlen = xlen
    self.ratio = ratio
    self.blk_pix_cnt = blk_pix_cnt
    self.down = None
    self.right = None
    self.matched = False
    # TODO: delete the offset fields and merge them into y/x min/max
    self.yoffset = 0
    self.xoffset = 0
    
  def is_valid_block(self):
    block_size = self.ylen * self.xlen
    valid_size = block_size < MAX_BLOCK_SIZE and block_size > MIN_BLOCK_SIZE
    return is_enough_black_pix_for_block(self.blk_pix_cnt) and valid_size
    
  def unpack(self):
    return (self.ymin, self.ymax, self.xmin, self.xmax, self.ylen, self.xlen,
            self.ratio, self.blk_pix_cnt)
            
  def has_word(self):
    return self.blk_pix_cnt > 0
    
  def get_offsets(self):
    return self.yoffset, self.xoffset

    
'''
The root function for marking the locations of the words.

'''
def get_blocks_enclosing_text(matrix, idx=''):
  matrix_w_gaps = mark_gaps_in_matrix(matrix, idx)
  subbubbles = get_subbubbles(matrix_w_gaps)
  processed_blocks = get_blocks_from_subbubble(subbubbles)
  
  if DBG:
    boxes_img = [[100 if is_gap(pix) else pix for pix in row] \
                                  for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, processed_blocks)
    print_image(boxes_img, 'bubbles_pre_merge')
  
  final_blocks = merge_blocks_to_form_squares(matrix_w_gaps, processed_blocks)
  
  # draw blocks on clean bubble
  if DBG:
    merged_blocks_img = [list(x) for x in matrix]
    write_blocks_to_img(merged_blocks_img, final_blocks)
    print_image(merged_blocks_img, 'final_merged_blocks' + idx)
  
  return final_blocks


'''
Given an image with the gaps marked, return a list of subbubbles

'''  
def get_subbubbles(matrix_w_gaps):
  print 'finding all subbubbles...'
  visited = set()
  subbubbles = []
  for i, y in enumerate(matrix_w_gaps):
    for j, pix_val in enumerate(y):
      # might want to change is_white_pixel() to not is_gap()
      if is_white_pixel(pix_val) and (i, j) not in visited:
        subbubble = get_subbubble(matrix_w_gaps, i, j, visited)
        if subbubble:
          subbubbles.append(subbubble)
          print 'found subbubble:', str(len(subbubbles))
      else:
        visited.add((i, j))
    
  # print the boundaries of the subbubble in the image
  if DBG:
    subbubble_img = [[100 if is_gap(pix) else pix for pix in row] \
                                      for row in matrix_w_gaps]
    subbubble_blocks = [subbubble_to_Text_block(sb) for sb in subbubbles]
    write_blocks_to_img(subbubble_img, subbubble_blocks)
    print_image(subbubble_img, 'subbubble_img')
    
  return subbubbles

  
def get_blocks_from_subbubble(subbubbles):
  blocks = []
  for i, subbubble in enumerate(subbubbles):
    subbubble_matrix, yoffset, xoffset = subbubble
    subbubble_w_gaps = mark_gaps_in_matrix(subbubble_matrix, str(i))
    raw_blocks = convert_img_to_blocks(subbubble_w_gaps, str(i))
    processed_blocks = dissect_uneven_blocks(subbubble_w_gaps, raw_blocks)
    blocks += [add_offsets(block, yoffset, xoffset) \
                        for block in processed_blocks]
  return blocks

  
'''
Quick hack for debugging/printing purposes.

'''
def subbubble_to_Text_block(subbubble):
  matrix, ymin, xmin = subbubble
  # create box for each subbubble
  return Text_block(ymin, ymin + len(matrix), xmin, xmin + len(matrix[0]), 
                    0, 0, 0, 1)


# TODO: possible to further optimize this by finding the border of the rectangle 
# instead of using flood fill.
def get_subbubble(matrix, ycoord, xcoord, all_visited):
  visited = set()
  stack = [(ycoord, xcoord)]
  ymin, ymax, xmin, xmax = ycoord, ycoord, xcoord, xcoord
  boundary = (0, len(matrix) - 1, 0, len(matrix[0]) - 1)
  black_pix_count = 0
  
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
    if is_black_pixel(matrix[y][x]):
      black_pix_count += 1
    
    for dy, dx in directions:
      i, j = y, x
      for count in xrange(SUBBUBBLE_BOUNDARY):
        i += dy
        j += dx
        # break on the first pixel that is either not in bounds, or is part of 
        # the subbubble
        if not is_in_bounds((i, j), boundary):
          break
        if (i, j) not in visited and not is_gap(matrix[i][j]):
          stack.append((i, j))
          visited.add((i, j))
          break

  # copy the subbubble portion of the image into its own matrix
  # TODO: might be worth it to compare the performace between what is below
  # and the list comprehension version
  subbubble_matrix = [[255] * (xmax - xmin + 1) for j in xrange(ymin, ymax + 1)]
  for pixel in visited:
    y, x = pixel
    if not is_gap(matrix[y][x]):
      subbubble_matrix[y - ymin][x - xmin] = matrix[y][x]
  
  all_visited |= visited
  if is_enough_black_pix_for_block(black_pix_count):
    return subbubble_matrix, ymin, xmin

  
'''
Continues to break down blocks into smaller blocks if they are deformed
(height width ratio is below threshold).

'''
def dissect_uneven_blocks(matrix_w_gaps, blocks):
  for block in blocks:
    if should_further_dissect_block(block.ratio):
      # TODO: perhaps should make copy of image within block, and avoid 
      # processing the entire block again when converting the image to blocks
      mark_gaps_in_block_to_matrix(matrix_w_gaps, block)
  return convert_img_to_blocks(matrix_w_gaps)
  
  
'''
Tries to merge Text_blocks so that they are all as close to a square as 
possible.

does this guarantee that we start from the top left?
if not, how does that impact this?

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
This is done by marking the x coordinates and y coordinates in which black pixels
don't exist.

'''
def mark_gaps_in_matrix(matrix, idx):
  print 'marking gaps...'
  matrix_w_gaps = [list(x) for x in matrix]
  vert_has_word = [0] * len(matrix)
  horz_has_word = [0] * len(matrix[0])
  
  for i, y in enumerate(matrix):
    for j, x in enumerate(y):
      if is_black_pixel(x):
        vert_has_word[i] = 1
        horz_has_word[j] = 1
        
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if vert_has_word[i] == 0 or horz_has_word[j] == 0:
        matrix_w_gaps[i][j] = GAP_COLOR
  
  if DBG:
    gaps_marked = [list(x) for x in matrix]
    for i in xrange(len(matrix)):
      for j in xrange(len(matrix[0])):
        if vert_has_word[i] == 0 or horz_has_word[j] == 0:
          gaps_marked[i][j] = 100
    print_image(gaps_marked, 'gaps_marked' + idx)
    
  return matrix_w_gaps

  
'''
Like the function mark_gaps(), but for within a Text_block.

'''
def mark_gaps_in_block_to_matrix(matrix, block):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
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
Converts image with marked grids to blocks.

'''
def convert_img_to_blocks(matrix_w_gaps, idx=''):
  processed = set()
  blocks = []
  for i, row in enumerate(matrix_w_gaps):
    for j, pix in enumerate(row):
      if not is_gap(pix) and (i, j) not in processed:
        block = get_block_parameters(matrix_w_gaps, i, j, processed)
        blocks.append(block)
      
  if DBG:
    boxes_img = [[100 if is_gap(pix) else pix for pix in row] \
                                  for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, blocks)
    print_image(boxes_img, 'boxes_preliminary' + idx)
      
  return blocks
  
  
'''
Mark which blocks are below or to the right of the block. This information will
be used for merging blocks later.

'''
# TODO: review this and see if able to make this cleaner...
def mark_adj_blocks(blocks, matrix_w_gaps):
  DEFAULT_VAL = -1
  regions = [[DEFAULT_VAL] * len(matrix_w_gaps[0]) for x in xrange(len(matrix_w_gaps))]
  
  # first pass, mark idx for different blocks
  for idx, block in enumerate(blocks):
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
    yoffset, xoffset = block.get_offsets()
    # need to take offsets into account
    for i in xrange(ymin + yoffset, ymax + yoffset + 1):
      for j in xrange(xmin + xoffset, xmax + xoffset + 1):
        regions[i][j] = idx
  
  # second pass, connect nodes/blocks
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
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

'''
# TODO: review this and see if able to make this cleaner...
def merge_w_nearby_blocks(block):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
  
  if ylen > xlen:
    r_block = block.right
    for i in xrange(MAX_BOX_NUM):
      if not r_block:
        break
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, \
            blk_pix_cnt1 = r_block.unpack()
      new_ratio = box_ratio(ylen, xlen + xmax1 - xmax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        xlen += xmax1 - xmax
        xmax = xmax1
        blk_pix_cnt += blk_pix_cnt1
        r_block.matched = True
        r_block = r_block.right
      else:
        break
  else:
    d_block = block.down
    for i in xrange(MAX_BOX_NUM):
      if not d_block:
        break
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, \
            blk_pix_cnt1 = d_block.unpack()
      new_ratio = box_ratio(xlen, ylen + ymax1 - ymax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        ylen += ymax1 - ymax
        ymax = ymax1
        blk_pix_cnt += blk_pix_cnt1
        d_block.matched = True
        d_block = d_block.down
      else:
        break
  
  final_block = Text_block(ymin, ymax, xmin, xmax, ylen, xlen, ratio,
                      blk_pix_cnt)
                      
  return add_offsets(final_block, block.yoffset, block.xoffset)


'''
Returns the width height ratio of the block.

'''
def box_ratio(ylen, xlen):
  return float(min(xlen, ylen)) / max(xlen, ylen)


'''
Marks the boundaries of the Text_blocks.

'''
def write_blocks_to_img(matrix, blocks):
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
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
def get_block_parameters(matrix, ycoord, xcoord, processed):
  blk_pix_cnt = 0
  
  i = ycoord
  while y_gap_is_small(matrix, i, xcoord):
    j = xcoord
    while x_gap_is_small(matrix, i, j):
      processed.add((i, j))
      if is_black_pixel(matrix[i][j]):
        blk_pix_cnt += 1
      j += 1
    i += 1
  
  ymin, ymax, xmin, xmax = ycoord, i - 1, xcoord, j - 1
  ylen, xlen = i - ycoord, j - xcoord
  ratio = box_ratio(ylen, xlen)
  return Text_block(ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt)


'''
a valid gap between words needs to be at least 2 pixels

'''
def y_gap_is_small(matrix, i, j):
  if i < len(matrix) - 1:
    return not is_gap(matrix[i][j]) or not is_gap(matrix[i + 1][j])
  else:
    return i < len(matrix) and not is_gap(matrix[i][j])
  
  
def x_gap_is_small(matrix, i, j):
  if j < len(matrix[0]) - 1:
    return not is_gap(matrix[i][j]) or not is_gap(matrix[i][j + 1])
  else:
    return j < len(matrix[0]) and not is_gap(matrix[i][j])
  

'''
Used mainly for debug.

Runs BFS around given coordinate to find white pixels, use flood fill to 
find the boundaries of the bubble. Stops BFS when queue of white pixels
are empty.

Extracts texts using the boundaries found, and marks the text blocks in the
end.

'''
def search_for_bubble_near_given_coord(matrix, ycoord, xcoord):
  print "Running BFS around (%d, %d) + flood fill..." % (ycoord, xcoord)
  q = Queue.Queue()
  q.put((ycoord, xcoord))
  visited = set()
  visited.add((ycoord, xcoord))
  matrix_bounds = (0, len(matrix) - 1, 0, len(matrix[0]) - 1)
  
  all_visited_white_pix = set()
  while q:
    y, x = q.get()
    if is_white_pixel(matrix[y][x]):
      bubble_white_pix, bubble_boundary = get_bubble_parameters(matrix, y, x)
      all_visited_white_pix |= bubble_white_pix
      if is_enough_white_pix_for_bubble(len(bubble_white_pix)):
        break
        
    for i, j in directions:
      next_pix = (y + i, x + j)
      if is_in_bounds(next_pix, matrix_bounds) and next_pix not in all_visited_white_pix:
        q.put(next_pix)
        visited.add(next_pix)
    
  bubble_parameters = get_clear_image_w_text(matrix, bubble_boundary, bubble_white_pix)
  bubble, black_pix_count, offsets = bubble_parameters
  if bubble and is_enough_black_pix_for_block(black_pix_count):
    # this prints out the debug images
    get_blocks_enclosing_text(bubble)
  else:
    print 'No bubble found with given coordinates'


'''
Searches the entire image for texts.
The way this is done is by running the single bubble finding algorithm on all
white pixels in the image.
Flood fill is run on every white pixel, with heuristics to determine if the
region is a text bubble.

Note that there will be false positives, but that is fine.


'''
# TODO: get all bubbles, then get all subbubbles, then get all blocks
# this makes it easier to measure performance.
# Note that normally it might be better to get blocks asap, so we can send it to
# OCR for processing, but all blocks need to be processed for overlaps anyway,
# so they are blocked
def get_all_blocks_in_image(matrix):
  final_img = [list(x) for x in matrix]
  visited = set()
  bubble_count = 0
  all_blocks = []
  print 'Searching for bubbles...'
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
      if is_white_pixel(pix) and (i, j) not in visited:
        bubble_white_pix, bubble_boundary = get_bubble_parameters(matrix, i, j)
        visited |= bubble_white_pix
        
        if is_enough_white_pix_for_bubble(len(bubble_white_pix)):
          bubble_parameters = get_clear_image_w_text(matrix, bubble_boundary, \
                                          bubble_white_pix, str(bubble_count))
          bubble, black_pix_count, offsets = bubble_parameters
          yoffset, xoffset = offsets
          
          if bubble and is_enough_black_pix_for_block(black_pix_count):
            print '\n%dth bubble found' % (bubble_count + 1)
            print 'Bubble found at:', bubble_boundary, 'from:', (i, j)
            bubble_count += 1
            
            # TODO: append block to list of blocks, process them in another loop
            ymin, ymax, xmin, xmax = bubble_boundary
            blocks = get_blocks_enclosing_text(bubble, str(bubble_count))
            all_blocks += [add_offsets(b, ymin + yoffset, xmin + xoffset) \
                          for b in blocks]
  
  print "\nfinal step, resolving overlapping blocks..."
  final_blocks = resolve_overlapping_blocks(matrix, all_blocks)
  write_to_final_img(final_img, final_blocks)
  print_image(final_img, 'final_img')
  
  
def add_offsets(block, yoffset, xoffset):
  block.yoffset += yoffset
  block.xoffset += xoffset
  return block
  

def resolve_overlapping_blocks(matrix, blocks):
  final_blocks = []
  blocks.sort(key = lambda x: x.ylen * x.xlen)
  ypix = [set() for i in xrange(len(matrix))]
  xpix = [set() for i in xrange(len(matrix[0]))]
  for n, block in enumerate(blocks):
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_count = block.unpack()
    yoffset, xoffset = block.get_offsets()
    ystart = yoffset + ymin
    yend = yoffset + ymax
    xstart = xoffset + xmin
    xend = xoffset + xmax
    
    # check for overlaps
    if is_overlap(ystart, yend, xstart, xend, ypix, xpix):
      continue
    else:
      # add image to sets if no overlap
      final_blocks.append(block)
      for i in xrange(ystart, yend + 1):
        ypix[i].add(n)
      for i in xrange(xstart, xend + 1):
        xpix[i].add(n)
  
  return final_blocks
  
  
# this might be worth optimizing?
def is_overlap(ystart, yend, xstart, xend, ypix, xpix):
  yoverlap = set()
  xoverlap = set()
  for i in xrange(ystart, yend + 1):
    yoverlap |= ypix[i]
  for i in xrange(xstart, xend + 1):
    xoverlap |= xpix[i]
  return len(yoverlap & xoverlap) > 0

  
def write_to_final_img(final_img, blocks):
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_count = block.unpack()
    yoffset, xoffset = block.get_offsets()
    
    ystart = max(0, yoffset + ymin - CHAR_MARGIN)
    yend = min(len(final_img) - 1, yoffset + ymax + CHAR_MARGIN)
    xstart = max(0, xoffset + xmin - CHAR_MARGIN)
    xend = min(len(final_img[0]) - 1, xoffset + xmax + CHAR_MARGIN)
    
    for i in xrange(ystart, yend + 1):
      final_img[i][xstart] = GREEN_MARK
      final_img[i][xend] = GREEN_MARK
      
    for j in xrange(xstart, xend + 1):
      final_img[ystart][j] = GREEN_MARK
      final_img[yend][j] = GREEN_MARK


'''
Extracts text from image given the boundaries of the bubble.

Marks the background to extract the text portion only, and in the end 
return the tightened bubble.

'''
def get_clear_image_w_text(matrix, boundary, white_space, idx=''):
  print "Running 2nd flood fill from corners"
  
  background_pixels = get_background_pixels(white_space, boundary)
  ymin, ymax, xmin, xmax = boundary
  clean_bubble = [[255 if (i, j) in background_pixels else matrix[i][j] \
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  
  if DBG:
    test_image1 = [[matrix[i][j] \
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    test_image2 = [[100 if (i, j) in white_space else matrix[i][j] 
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    bord = [[0 if (i, j) in background_pixels else matrix[i][j] \
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    print_image(test_image1, 'original_text_block' + idx)
    print_image(test_image2, 'text_block' + idx)
    print_image(bord, 'borders' + idx)
    print_image(clean_bubble, 'clean_block' + idx)
  
  return tighten_bubble_boundary(clean_bubble, idx)

  
'''
Tightens the bubble by finding boundaries of where the black pixels are and
adding a bit of margin.

Returns the tightened bubble as well as the number of black pixles and the
x and y offset of the tightened bubble in the original image.

'''
def tighten_bubble_boundary(matrix, idx):
  print "Cropping extra white space..."
  xmin = len(matrix[0])
  xmax = -1
  ymin = len(matrix)
  ymax = -1
  black_pix_count = 0
  
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if is_black_pixel(matrix[i][j]):
        black_pix_count += 1
        xmin = min(j, xmin)
        xmax = max(j, xmax)
        ymin = min(i, ymin)
        ymax = max(i, ymax)
  
  xmin = xmin - BUBBLE_MARGIN if xmin >= BUBBLE_MARGIN else 0
  xmax = xmax + BUBBLE_MARGIN if xmax < len(matrix[0]) - BUBBLE_MARGIN else 0
  ymin = ymin - BUBBLE_MARGIN if ymin >= BUBBLE_MARGIN else 0
  ymax = ymax + BUBBLE_MARGIN if ymax < len(matrix) - BUBBLE_MARGIN else 0
  
  if DBG:
    box = [list(x) for x in matrix]
    for i in xrange(len(matrix)):
      box[i][xmin] = 0
      box[i][xmax] = 0
    for i in xrange(len(matrix[0])):
      box[ymin][i] = 0
      box[ymax][i] = 0
    print_image(box, 'box_lines' + idx)
  
  tightened_bubble = [[matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                      for i in xrange(ymin, ymax + 1)]
  return tightened_bubble, black_pix_count, (ymin, xmin)
  
  
def get_background_pixels(visited_white_pix, boundary):
  ymin, ymax, xmin, xmax = boundary
  border = set()
  # do flood fill from the boundaries
  for i in xrange(xmin, xmax + 1):
    if (ymin, i) not in border and (ymin, i) not in visited_white_pix:
      flood_fill_backgroud(visited_white_pix, border, boundary, ymin, i)
    if (ymax, i) not in border and (ymax, i) not in visited_white_pix:
      flood_fill_backgroud(visited_white_pix, border, boundary, ymax, i)
      
  for i in xrange(ymin, ymax + 1):
    if (i, xmin) not in border and (i, xmin) not in visited_white_pix:
      flood_fill_backgroud(visited_white_pix, border, boundary, i, xmin)
    if (i, xmax) not in border and (i, xmax) not in visited_white_pix:
      flood_fill_backgroud(visited_white_pix, border, boundary, i, xmax)  

  return border

  
def flood_fill_backgroud(visited_white_pix, border, boundary, ycoord, xcoord):
  stack = [(ycoord, xcoord)]
  border.add((ycoord, xcoord))
  while stack:
    y, x = stack.pop()
    for i, j in directions:
      next_pix = (y + i, x + j)
      if is_in_bounds(next_pix, boundary) and \
          next_pix not in visited_white_pix and next_pix not in border:
        stack.append(next_pix)
        border.add(next_pix)
    
  
'''
Runs flood fill on image for white pixels.

Modifies visited_white_pix so we don't visit the same pixel twice.
Modifies boundary so we can determine the boundaries of the bubble.

'''
def get_bubble_parameters(matrix, ycoord, xcoord):
  ymin, ymax, xmin, xmax = ycoord, ycoord, xcoord, xcoord
  visited = set()
  matrix_bounds = [0, len(matrix) - 1, 0, len(matrix[0]) - 1]
  stack = [(ycoord, xcoord)]
  visited.add((ycoord, xcoord))
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
    
    for i, j in directions:
      yn = y + i
      xn = x + j
      next_pix = (yn, xn)
      if is_in_bounds(next_pix, matrix_bounds) and \
          is_white_pixel(matrix[yn][xn]) and next_pix not in visited:
        stack.append(next_pix)
        visited.add(next_pix)
  return visited, (ymin, ymax, xmin, xmax)

        
'''
Checks if the given corrdinate is in bounds

'''
def is_in_bounds(coord, limits):
  i, j = coord
  ymin, ymax, xmin, xmax = limits
  return i >= ymin and i <= ymax and j >= xmin and j <= xmax
  
  
def is_black_pixel(val):
  return val <= BLACK_COLOR and val >= 0


def is_white_pixel(val):
  return val >= WHITE_COLOR
  

def is_gap(val):
  return val == -1

  
def is_enough_white_pix_for_bubble(white_pixel_count):
  return white_pixel_count > MIN_WHITE_PIX


def is_enough_black_pix_for_block(black_pixel_count):
  return black_pixel_count > MIN_BLACK_PIX
  
  
def should_further_dissect_block(ratio):
  return ratio <= DISSECT_RATIO_THRES
  
  
def should_try_merging(ratio):
  return ratio < RATIO_THRES
  
  
'''
Prints processed image matrix to image.

'''
def print_image(matrix, fname):
  blk = (0, 0, 0)           # color black
  wht = (255, 255, 255)     # color white
  grn = (0, 255, 0)
  red = (255, 0, 0)
  
  pixels2 = [grn if x == GREEN_MARK else red if x == RED_MARK else (x, x, x) 
              for row in matrix for x in row]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  im2.putdata(pixels2)
  im2.save(fname + '.png', "PNG")
  
  
'''
MAIN

'''
def main():
  global DBG
  
  args = sys.argv[1:]
  filename = args[0]
  print "Reading image file..."
  try:
    im = Image.open(filename)
  except IOError:
    print "Error in file name"
    sys.exit()
  
  # get pixel values and store to list
  im = im.convert("L")
  pixels = list(im.getdata())
  width, height = im.size
  
  # convert to list to 2D list
  pixels = [pixels[i * width:(i + 1) * width] for i in xrange(height)]
  
  if len(args) >= 3:
    DBG = 1
    x, y = int(args[1]), int(args[2])
    search_for_bubble_near_given_coord(pixels, y, x)
  else:
    get_all_blocks_in_image(pixels)


if __name__ == '__main__':
  main()
