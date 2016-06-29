import sys, os
import Queue
from PIL import Image

'''
Current flow
  1. detect bubble
  2. extract text from bubble
  3. crop extra white border
  4. apply threshold (optional)
  5. mark the "gaps" (white space between words)
  6. find bubbles
  7. find subbubbles for each bubble
  8. convert all subbubbles into blocks
      - find and mark gaps
      - break down gaps into boxes
      - further breakdown certain boxes
      - merge blocks to form squares
  9. make sure all bubbles have no overlap with each other, if overlap occurs,
     favor the smaller bubble and delete the larger one.

TODO:
  Possible improvements:
    1. code cleanup and add comments
    2. better filtering so light colored parts don't get cropped off?
    
    Features/improvements:
     - optimize performance

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
MIN_BLK_PIX = 3
MIN_BOX_SIZE = 8
MAX_BOX_SIZE = 40000
SUBBUBBLE_BOUNDARY = 15

directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
matrix_bounds = None

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
    enough_blk_pix = self.blk_pix_cnt >= MIN_BLK_PIX
    box_size = self.ylen * self.xlen
    valid_size = box_size < MAX_BOX_SIZE and box_size > MIN_BOX_SIZE
    return enough_blk_pix and valid_size
    
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
def mark_text_blocks(matrix, idx=''):
  matrix_w_gaps = mark_gaps(matrix, idx)
  raw_subbubbles = separate_subbubbles(matrix_w_gaps)
  processed_blocks = get_blocks_from_subbubble(raw_subbubbles)
  
  if DBG:
    boxes_img = [[100 if pix == -1 else pix for pix in row] \
                                  for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, processed_blocks)
    print_image(boxes_img, 'bubbles_pre_merge')
  
  # merge blocks
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
def separate_subbubbles(matrix_w_gaps):
  print 'finding all subbubbles...'
  visited = set()
  subbubbles = []
  for i, y in enumerate(matrix_w_gaps):
    for j, pix_val in enumerate(y):
      if pix_val >= WHITE_COLOR and (i, j) not in visited:
        subbubble = get_subbubble(matrix_w_gaps, i, j, visited)
        subbubbles.append(subbubble)
        print 'found subbubble:', str(len(subbubbles))
      else:
        visited.add((i, j))
    
  # print the boundaries of the subbubble in the image
  if DBG:
    subbubble_img = [[100 if pix == -1 else pix for pix in row] \
                                      for row in matrix_w_gaps]
    subbubble_blocks = [subbubble_to_Text_block(sb) for sb in subbubbles]
    write_blocks_to_img(subbubble_img, subbubble_blocks)
    print_image(subbubble_img, 'subbubble_img')
    
  return subbubbles

  
def get_blocks_from_subbubble(subbubbles):
  blocks = []
  for i, subbubble in enumerate(subbubbles):
    subbubble_matrix, yoffset, xoffset = subbubble
    subbubble_w_gaps = mark_gaps(subbubble_matrix, str(i))
    raw_blocks = convert_img_to_blocks(subbubble_w_gaps, str(i))
    processed_blocks = break_down_deformed_blocks(subbubble_w_gaps, raw_blocks)
    blocks += [add_offsets(block, yoffset, xoffset) \
                        for block in processed_blocks]
  return blocks

  
def subbubble_to_Text_block(subbubble):
  matrix, ymin, xmin = subbubble
  # create box for each subbubble
  return Text_block(ymin, ymin + len(matrix), xmin, xmin + len(matrix[0]), 
                    0, 0, 0, 1)


# TODO: optimize by checking if black pixels exist within the subbubble
# if not, return nothing
# also, optimize this to only reach out accross borders if bordering a gap
# this will greatly improve performance
def get_subbubble(matrix, ycoord, xcoord, all_visited):
  visited = set()
  stack = [(ycoord, xcoord)]
  ymin, ymax, xmin, xmax = ycoord, ycoord, xcoord, xcoord
  
  while stack:
    y, x = stack.pop()
    ystart = max(0, y - SUBBUBBLE_BOUNDARY)
    yend = min(len(matrix), y + SUBBUBBLE_BOUNDARY + 1)
    xstart = max(0, x - SUBBUBBLE_BOUNDARY)
    xend = min(len(matrix[0]), x + SUBBUBBLE_BOUNDARY + 1)
    
    if ystart < ymin:
      ymin = ystart
    if yend > ymax:
      ymax = yend
    if xstart < xmin:
      xmin = xstart
    if xend > xmax:
      xmax = xend
      
    for i in xrange(ystart, yend):
      for j in xrange(xstart, xend):
        if (i, j) not in visited:
          visited.add((i, j))
          if matrix[i][j] != -1:
            stack.append((i, j))

  # copy the subbubble portion of the image into its own matrix
  subbubble_matrix = [[matrix[i][j] if (i, j) in visited and matrix[i][j] != -1 else 255 \
                                      for j in xrange(xmin, xmax)] \
                                      for i in xrange(ymin, ymax)]
  all_visited |= visited
  # TODO: use named tuple instead
  return subbubble_matrix, ymin, xmin

  
'''
Continues to break down blocks into smaller blocks if they are deformed
(height width ratio is below threshold).

'''
def break_down_deformed_blocks(matrix_w_gaps, blocks):
  # break blocks down further if necessary
  for i in xrange(DISSECT_NUM):
    for block in blocks:
      if block.ratio <= DISSECT_RATIO_THRES:
        mark_gaps_within_block(matrix_w_gaps, block)
    blocks = convert_img_to_blocks(matrix_w_gaps, str(i))
  return blocks
  
  
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
    if block.ratio < RATIO_THRES:
      block = merge_w_nearby_blocks(block)
    if block.is_valid_block():
      final_blocks.append(block)
  return final_blocks
  
  
'''
Marks the locations of the image where the words don't exist.
This is done by marking the x coordinates and y coordinates in which black pixels
don't exist.

'''
def mark_gaps(matrix, idx):
  print 'marking gaps...'
  matrix_w_gaps = [list(x) for x in matrix]
  vert_has_word = [0] * len(matrix)
  horz_has_word = [0] * len(matrix[0])
  
  for i, y in enumerate(matrix):
    for j, x in enumerate(y):
      if x <= BLACK_COLOR:
        vert_has_word[i] = 1
        horz_has_word[j] = 1
        
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if vert_has_word[i] == 0 or horz_has_word[j] == 0:
        matrix_w_gaps[i][j] = -1
  
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
def mark_gaps_within_block(matrix, block):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
  vert_has_word = [0] * ylen
  horz_has_word = [0] * xlen
  
  for i in xrange(ymin, ymax + 1):
    for j in xrange(xmin, xmax + 1):
      if matrix[i][j] <= BLACK_COLOR and matrix[i][j] >= 0:
        vert_has_word[i - ymin] = 1
        horz_has_word[j - xmin] = 1
        
  if ylen > WORD_BREAK_MIN_LEN:
    for i in xrange(ymin, ymax + 1):
        if vert_has_word[i - ymin] == 0:
          for j in xrange(xmin, xmax + 1):
            matrix[i][j] = -1
  
  if xlen > WORD_BREAK_MIN_LEN:
    for j in xrange(xmin, xmax + 1):
        if horz_has_word[j - xmin] == 0:
          for i in xrange(ymin, ymax + 1):
            matrix[i][j] = -1
  
  
'''
Converts image with marked grids to blocks.

'''
def convert_img_to_blocks(matrix_w_gaps, idx=''):
  processed = set()
  blocks = []
  for i, row in enumerate(matrix_w_gaps):
    for j, pix in enumerate(row):
      if pix != -1 and (i, j) not in processed:
        block = get_block_parameters(matrix_w_gaps, i, j, processed)
        blocks.append(block)
      
  if DBG:
    boxes_img = [[100 if pix == -1 else pix for pix in row] \
                                  for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, blocks)
    print_image(boxes_img, 'boxes_preliminary' + idx)
      
  return blocks
  
  
'''
Mark which blocks are below or to the right of the block. This information will
be used for merging blocks later.

'''
def mark_adj_blocks(blocks, matrix_w_gaps):
  regions = [[-1] * len(matrix_w_gaps[0]) for x in xrange(len(matrix_w_gaps))]
  
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
      if regions[ymid][j] != -1:
        right_idx = regions[ymid][j]
        break
    if right_idx != -1:
      r_block = blocks[right_idx]
      if r_block.ymax == block.ymax and r_block.ymin == block.ymin:
        block.right = r_block
    # search down
    down_idx = -1
    for i in xrange(ymax + yoffset + 1, len(matrix_w_gaps)):
      if regions[i][xmid] != -1:
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
        matrix[i][xstart] = -1
        matrix[i][xend] = -1
      for j in xrange(xstart, xend + 1):
        matrix[ystart][j] = -1
        matrix[yend][j] = -1


'''
Given the top left coordinate of the block, find the parameters of the block,
and return the block in the Text_block class.

'''
def get_block_parameters(matrix, ycoord, xcoord, processed):
  blk_pix_cnt = 0
  
  # print 
  # print 'matrix dimensions:', len(matrix), len(matrix[0])
  # print 'starting from:', ycoord, xcoord
  
  i = ycoord
  while y_gap_is_small(matrix, i, xcoord):
    j = xcoord
    while x_gap_is_small(matrix, i, j):
      processed.add((i, j))
      if matrix[i][j] <= BLACK_COLOR and matrix[i][j] >= 0:
        blk_pix_cnt += 1
      j += 1
    i += 1
  
  ymin, ymax, xmin, xmax = ycoord, i - 1, xcoord, j - 1
  ylen, xlen = i - ycoord, j - xcoord
  ratio = box_ratio(ylen, xlen)
  return Text_block(ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt)


'''
right now define a valid gap between words needs to be at least 2 pixels

'''
def y_gap_is_small(matrix, i, j):
  if i < len(matrix) - 1:
    return matrix[i][j] != -1 or matrix[i + 1][j] != -1
  else:
    return i < len(matrix) and matrix[i][j] != -1
  
  
def x_gap_is_small(matrix, i, j):
  if j < len(matrix[0]) - 1:
    return matrix[i][j] != -1 or matrix[i][j + 1] != -1
  else:
    return j < len(matrix[0]) and matrix[i][j] != -1
  

'''
Runs BFS around given coordinate to find white pixels, use flood fill to 
find the boundaries of the bubble. Stops BFS when queue of white pixels
are empty.

Extracts texts using the boundaries found, and marks the text blocks in the
end.

'''
def search_for_bubble_near_coord(matrix, ycoord, xcoord):
  print "Running BFS around (%d, %d) + flood fill..." % (ycoord, xcoord)
  visited_white_pix = set()
  q = Queue.Queue()
  q.put((ycoord, xcoord))
  visited = set()
  visited.add((ycoord, xcoord))
  boundary = [ycoord, ycoord, xcoord, xcoord]
  
  while not q.empty():
    y, x = q.get()
    if matrix[y][x] >= WHITE_COLOR:
      flood_fill_white(matrix, visited_white_pix, y, x, boundary)
      if len(visited_white_pix) > MIN_WHITE_PIX:
        break
    for i, j in directions:
      next_pix = (y + i, x + j)
      if is_in_bounds(next_pix, matrix_bounds) and next_pix not in visited:
        q.put(next_pix)
        visited.add(next_pix)
    
  bubble, blk_pix_cnt, offsets = extract_text(matrix, boundary, visited_white_pix)
  if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
    mark_text_blocks(bubble)
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
def get_blocks_in_entire_img(matrix):
  final_img = [list(x) for x in matrix]
  visited = set()
  bubble_count = 0
  all_blocks = []
  print 'Searching for bubbles...'
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
      if pix >= WHITE_COLOR and (i, j) not in visited:
        visited_white_pix = set()
        boundary = [i, i, j, j]  # ymin, ymax, xmin, xmax
        flood_fill_white(matrix, visited_white_pix, i, j, boundary)
        visited |= visited_white_pix
        ymin, ymax, xmin, xmax = boundary
        # second condition added for right now to ensure we don't include the
        # entire image, this is due to performance
        # TODO: get rid of the 2nd condition when performance is more optimized
        if len(visited_white_pix) > MIN_WHITE_PIX and (ymin != 0 or xmin != 0):
          bubble, blk_pix_cnt, offsets = extract_text(matrix, boundary, \
                                          visited_white_pix, str(bubble_count))
          yoffset, xoffset = offsets
          if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
            print '\n%dth bubble found' % (bubble_count + 1)
            print 'Bubble found at:', boundary, 'from:', (i, j)
            bubble_count += 1
            blocks = mark_text_blocks(bubble, str(bubble_count))
            all_blocks += [add_offsets(b, ymin + yoffset, xmin + xoffset) \
                          for b in blocks]
  
  print "\nfinal processing for overlaps..."
  final_blocks = process_overlapping_blocks(matrix, all_blocks)
  write_to_final_img(final_img, final_blocks)
  print_image(final_img, 'final_img')
  
  
def add_offsets(block, yoffset, xoffset):
  block.yoffset += yoffset
  block.xoffset += xoffset
  return block
  

def process_overlapping_blocks(matrix, blocks):
  final_blocks = []
  blocks.sort(key=lambda x: x.ylen * x.xlen)
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
      final_img[i][xstart] = -1
      final_img[i][xend] = -1
    for j in xrange(xstart, xend + 1):
      final_img[ystart][j] = -1
      final_img[yend][j] = -1


'''
Extracts text from image given the boundaries of the bubble.

Marks the background to extract the text portion only, and in the end 
return the tightened bubble.

'''
def extract_text(matrix, boundary, white_space, idx=''):
  print "Running 2nd flood fill from corners"
  
  background_pixels = mark_background(white_space, boundary)
  ymin, ymax, xmin, xmax = boundary
  clean_bubble = [[255 if (i, j) in background_pixels else matrix[i][j] \
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  apply_threshold(clean_bubble, WHITE_COLOR, BLACK_COLOR)
  
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
  
  return tighten_bubble(clean_bubble, idx)

  
'''
Tightens the bubble by finding boundaries of where the black pixels are and
adding a bit of margin.

Returns the tightened bubble as well as the number of black pixles and the
x and y offset of the tightened bubble in the original image.

'''
def tighten_bubble(matrix, idx):
  print "Cropping extra white space..."
  xmin = len(matrix[0])
  xmax = -1
  ymin = len(matrix)
  ymax = -1
  black_pix_count = 0
  
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] <= BLACK_COLOR:
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
  
  
def mark_background(visited_white_pix, boundary):
  ymin, ymax, xmin, xmax = boundary
  border = set()
  # do flood fill from the boundaries
  for i in xrange(xmin, xmax + 1):
    if (ymin, i) not in border and (ymin, i) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, ymin, i)
    if (ymax, i) not in border and (ymax, i) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, ymax, i)
      
  for i in xrange(ymin, ymax + 1):
    if (i, xmin) not in border and (i, xmin) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, i, xmin)
    if (i, xmax) not in border and (i, xmax) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, i, xmax)  

  return border

  
def flood_fill_non_white(visited_white_pix, border, boundary, ycoord, xcoord):
  stack = [(ycoord, xcoord)]
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
def flood_fill_white(matrix, visited_white_pix, ycoord, xcoord, boundary):
  stack = [(ycoord, xcoord)]
  visited_white_pix.add((ycoord, xcoord))
  while stack:
    y, x = stack.pop()
    if y < boundary[0]:
      boundary[0] = y
    if y > boundary[1]:
      boundary[1] = y
    if x < boundary[2]:
      boundary[2] = x
    if x > boundary[3]:
      boundary[3] = x
    
    for i, j in directions:
      yn, xn = y + i, x + j
      next_pix = (yn, xn)
      if is_in_bounds(next_pix, matrix_bounds) and \
          matrix[yn][xn] >= WHITE_COLOR and next_pix not in visited_white_pix:
        stack.append(next_pix)
        visited_white_pix.add(next_pix)

        
'''
Checks if the given corrdinate is in bounds

'''
def is_in_bounds(coord, limits):
  i, j = coord
  ymin, ymax, xmin, xmax = limits
  return i >= ymin and i <= ymax and j >= xmin and j <= xmax
  
  
'''
Applies threshold on image. Not necessary to use if we use WHITE_COLOR and
BLACK_COLOR when comparing.

Left here in case it becomes useful at some point.

'''
def apply_threshold(matrix, white_thres=255, black_thres=0):
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] >= white_thres:
        matrix[i][j] = 255
      if matrix[i][j] <= black_thres:
        matrix[i][j] = 0

      
'''
Prints processed image matrix to image.
special values that map to colors:
-1: green
-2: red

'''
def print_image(matrix, fname):
  blk = (0, 0, 0)           # color black
  wht = (255, 255, 255)     # color white
  grn = (0, 255, 0)
  red = (255, 0, 0)
  
  pixels2 = [grn if x == -1 else red if x == -2 else (x, x, x) 
              for row in matrix for x in row]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  im2.putdata(pixels2)
  im2.save(fname + '.png', "PNG")
  
  
'''
MAIN

'''
def main():
  global matrix_bounds
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
  matrix_bounds = [0, height - 1, 0, width - 1]
  
  if len(args) >= 3:
    DBG = 1
    x, y = int(args[1]), int(args[2])
    search_for_bubble_near_coord(pixels, y, x)
  else:
    get_blocks_in_entire_img(pixels)


if __name__ == '__main__':
  main()
