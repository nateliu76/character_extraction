import sys, os
import Queue
from PIL import Image

'''
TO DO:
  1. better filtering so light colored parts don't get cropped off
  2. clustering/grouping words into connected components?
  3. Improve boxing for edge cases:
    - first character/last character
    - DP?
  4. make comments, starting to forget lol

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
DISSECT_NUM = 2
DISSECT_RATIO_THRES = 0.6
WORD_BREAK_MIN_LEN = 30
MIN_BLK_PIX = 3
MIN_BOX_SIZE = 8
MAX_BOX_SIZE = 40000

directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
matrix_bounds = None

class Text_bubble():
  def __init__(self, ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word, blk_pix_cnt):
    self.ymin = ymin
    self.ymax = ymax
    self.xmin = xmin
    self.xmax = xmax
    self.ylen = ylen
    self.xlen = xlen
    self.ratio = ratio
    self.has_word = has_word
    self.blk_pix_cnt = blk_pix_cnt
    self.down = None
    self.right = None
    self.matched = False
    
  def is_valid_box(self):
    enough_blk_pix = self.blk_pix_cnt >= MIN_BLK_PIX
    box_size = self.ylen * self.xlen
    valid_size = box_size < MAX_BOX_SIZE and box_size > MIN_BOX_SIZE
    return enough_blk_pix and valid_size
    
  def unpack(self):
    return (self.ymin, self.ymax, self.xmin, self.xmax, self.ylen, self.xlen,
            self.ratio, self.has_word)
    
  def unpack_all(self):
    return (self.ymin, self.ymax, self.xmin, self.xmax, self.ylen, self.xlen,
            self.ratio, self.has_word, self.blk_pix_cnt)
  
def tighten_bubble(matrix, idx=''):
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

  
def find_border(matrix, white_space, boundary):
  ymin, ymax, xmin, xmax = boundary
  border = set()
  # do flood fill from the boundaries
  for i in xrange(xmin, xmax + 1):
    if (ymin, i) not in border and (ymin, i) not in white_space:
      flood_fill_non_white(white_space, border, boundary, ymin, i)
    if (ymax, i) not in border and (ymax, i) not in white_space:
      flood_fill_non_white(white_space, border, boundary, ymax, i)
      
  for i in xrange(ymin, ymax + 1):
    if (i, xmin) not in border and (i, xmin) not in white_space:
      flood_fill_non_white(white_space, border, boundary, i, xmin)
    if (i, xmax) not in border and (i, xmax) not in white_space:
      flood_fill_non_white(white_space, border, boundary, i, xmax)  

  return border
  
  
def add_grid_lines(matrix, idx=''):
  print 'Adding grid lines...'
  box = find_gaps(matrix, idx)
  
  # approach 2: merge boxes so that it forms something close to a square
  boxes = process_boxes(box)
  
  if DBG:
    merged_box_img = [list(x) for x in matrix]
    for box in boxes:
      if not box:
        continue
      ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
      if has_word:
        ystart = max(0, ymin - CHAR_MARGIN)
        yend = min(len(matrix) - 1, ymax + CHAR_MARGIN)
        xstart = max(0, xmin - CHAR_MARGIN)
        xend = min(len(matrix[0]) - 1, xmax + CHAR_MARGIN)
        for i in xrange(ystart, yend + 1):
          merged_box_img[i][xstart] = -1
          merged_box_img[i][xend] = -1
        for j in xrange(xstart, xend + 1):
          merged_box_img[ystart][j] = -1
          merged_box_img[yend][j] = -1
    print_image(merged_box_img, 'boxes_merged' + idx)
  return boxes
  
  
def find_gaps(matrix, idx):
  box = [list(x) for x in matrix]
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
        box[i][j] = -1
  
  if DBG:
    box_img_thick = [list(x) for x in matrix]
    for i in xrange(len(matrix)):
      for j in xrange(len(matrix[0])):
        if vert_has_word[i] == 0 or horz_has_word[j] == 0:
          box_img_thick[i][j] = 150
    print_image(box_img_thick, 'thick grids' + idx)
    
    # approach 1: center grids
    # center_grids(vert_has_word)
    # center_grids(horz_has_word)
    # box_img = [list(x) for x in matrix]
    # for i in xrange(len(matrix)):
      # for j in xrange(len(matrix[0])):
        # if vert_has_word[i] == 0 or horz_has_word[j] == 0:
          # box_img[i][j] = 100
    # print_image(box_img, 'thin grids' + idx)
    
  return box
  
'''
TODO:
add condition that dissecting only works if box is dissected into more than one piece

'''
def dissect_box(matrix, box):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
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
  
  
def convert_pix_to_boxes(matrix, idx=''):
  # change image to 2d list of box dimensions
  processed = set()
  boxes = []
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
      if pix != -1 and (i, j) not in processed:
        boxes.append(get_dimensions(matrix, i, j, processed))
      
  if DBG:
    boxes_img = [[100 if pix == -1 else pix for pix in row] for row in matrix]
    for box in boxes:
      if not box:
        continue
      ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
      if has_word:
        ystart = max(0, ymin - CHAR_MARGIN)
        yend = min(len(matrix) - 1, ymax + CHAR_MARGIN)
        xstart = max(0, xmin - CHAR_MARGIN)
        xend = min(len(matrix[0]) - 1, xmax + CHAR_MARGIN)
        for i in xrange(ystart, yend + 1):
          boxes_img[i][xstart] = -2
          boxes_img[i][xend] = -2
        for j in xrange(xstart, xend + 1):
          boxes_img[ystart][j] = -2
          boxes_img[yend][j] = -2
    print_image(boxes_img, 'boxes_preliminary' + idx)
      
  return boxes
  
  
def process_boxes(matrix):
  boxes = convert_pix_to_boxes(matrix)
  
  for i in xrange(DISSECT_NUM):
    # break boxes down further
    for box in boxes:
      ratio = box[6]
      if ratio <= DISSECT_RATIO_THRES:
        dissect_box(matrix, box)
    boxes = convert_pix_to_boxes(matrix, str(i))
  
  # put all boxes to Text_bubble class
  bubbles = convert_boxes_to_bubbles(boxes, matrix)
  
  # merge bubbles
  final_bubbles = []
  for bubble in bubbles:
    # if already matched, skip
    if bubble.matched:
      continue
    # try and match with others if necessary
    if bubble.ratio < RATIO_THRES:
      bubble = merge_bubbles(bubble)
    if bubble.is_valid_box():
      final_bubbles.append(bubble)
    
  return [bubble.unpack() for bubble in final_bubbles]

  
def convert_boxes_to_bubbles(boxes, matrix):
  regions = [[-1] * len(matrix[0]) for x in xrange(len(matrix))]
  
  # first pass, mark idx for different boxes, optimize later
  bubbles = []
  idx = 0
  for box in boxes:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
    blk_pix_cnt = 0
    for i in xrange(ymin, ymax + 1):
      for j in xrange(xmin, xmax + 1):
        if matrix[i][j] <= BLACK_COLOR and matrix[i][j] >= 0:
          blk_pix_cnt += 1
          
    bubble = Text_bubble(ymin, ymax, xmin, xmax, ylen, xlen, 
                         ratio, has_word, blk_pix_cnt)
    for i in xrange(ymin, ymax + 1):
      for j in xrange(xmin, xmax + 1):
        regions[i][j] = idx
    idx += 1
    bubbles.append(bubble)
  
  # second pass, connect nodes/bubbles
  for bubble1 in bubbles:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = bubble1.unpack()
    ymid = (ymin + ymax) / 2
    xmid = (xmin + xmax) / 2
    # search right
    right_idx = -1
    for j in xrange(xmax + 1, len(matrix[0])):
      if regions[ymid][j] != -1:
        right_idx = regions[ymid][j]
        break    
    if right_idx != -1:
      r_bubble = bubbles[right_idx]
      if r_bubble.ymax == bubble1.ymax and r_bubble.ymin == bubble1.ymin:
        bubble1.right = r_bubble
      
    # search down
    down_idx = -1
    for i in xrange(ymax + 1, len(matrix)):
      if regions[i][xmid] != -1:
        down_idx = regions[i][xmid]
        break    
    if down_idx != -1:
      d_bubble = bubbles[down_idx]
      if d_bubble.xmax == bubble1.xmax and d_bubble.xmin == bubble1.xmin:
        bubble1.down = d_bubble
  return bubbles
  
  
def merge_bubbles(bubble):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, \
        has_word, blk_pix_cnt = bubble.unpack_all()
  
  if bubble.ylen > bubble.xlen:
    r_bubble = bubble.right
    for i in xrange(MAX_BOX_NUM):
      if not r_bubble:
        break
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, \
            has_word1, blk_pix_cnt1 = r_bubble.unpack_all()
      new_ratio = box_ratio(ylen, xlen + xmax1 - xmax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        xlen += xmax1 - xmax
        xmax = xmax1
        has_word |= has_word1
        blk_pix_cnt += blk_pix_cnt1
        r_bubble.matched = True
        r_bubble = r_bubble.right
      else:
        break
  else:
    d_bubble = bubble.down
    for i in xrange(MAX_BOX_NUM):
      if not d_bubble:
        break
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, \
            has_word1, blk_pix_cnt1 = d_bubble.unpack_all()
      new_ratio = box_ratio(xlen, ylen + ymax1 - ymax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        ylen += ymax1 - ymax
        ymax = ymax1
        has_word |= has_word1
        blk_pix_cnt += blk_pix_cnt1
        d_bubble.matched = True
        d_bubble = d_bubble.down
      else:
        break
  
  merged_bubble = Text_bubble(ymin, ymax, xmin, xmax, ylen, xlen, ratio, \
                      has_word, blk_pix_cnt)
  return merged_bubble
  

def merge_boxes(boxes, ycoord, xcoord, matched):
  matched[ycoord][xcoord] = 1
  curr_box = boxes[ycoord][xcoord]
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = curr_box
  if ylen > xlen:
    # merge boxes to the right
    for j in xrange(xcoord + 1, min(xcoord + MAX_BOX_NUM, len(boxes[0]))):
      next_box = boxes[ycoord][j]
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, has_word1 = next_box
      new_ratio = box_ratio(ylen, xlen + xmax1 - xmax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        xlen += xmax1 - xmax
        xmax = xmax1
        has_word |= has_word1
        matched[ycoord][j] = 1
      else:
        break
  else:
    # merge boxes below
    for i in xrange(ycoord + 1, min(ycoord + MAX_BOX_NUM, len(boxes))):
      next_box = boxes[i][xcoord]
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, has_word1 = next_box
      new_ratio = box_ratio(ylen + ymax1 - ymax, xlen)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        ylen += ymax1 - ymax
        ymax = ymax1
        has_word |= has_word1
        matched[i][xcoord] = 1
      else:
        break
  
  return ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word


def box_ratio(ylen, xlen):
  return float(min(xlen, ylen)) / max(xlen, ylen)


'''
added condition in which words will be at least 2 pixels apart
TODO:
there is one case that will break this

'''
def get_dimensions(matrix, ycoord, xcoord, processed):
  has_word = False
  i = ycoord
  while i + 1 < len(matrix) and (matrix[i][xcoord] != -1 or matrix[i + 1][xcoord] != -1):
    j = xcoord
    while j + 1< len(matrix[0]) and (matrix[i][j] != -1 or matrix[i][j + 1] != -1):
      processed.add((i, j))
      if not has_word and matrix[i][j] <= BLACK_COLOR and matrix[i][j] >= 0:
        has_word = True
      j += 1
    i += 1
  
  ymin, ymax, xmin, xmax = ycoord, i - 1, xcoord, j - 1
  ylen, xlen = i - ycoord, j - xcoord
  ratio = box_ratio(ylen, xlen)
  return ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word
  
  
def center_grids(hist):
  run = 0
  for i, pix in enumerate(hist):
    if pix == 0:
      run += 1
      hist[i] = 1
    if pix == 1 and run >= 3:
      mid_idx = (i - run) + (run - 1) / 2
      hist[mid_idx] = 0
    if pix == 1:
      run = 0
      
  if run >= 3:
    mid_idx = -run / 2
    hist[mid_idx] = 0

    
def search_for_bubble_around_coord(matrix, ycoord, xcoord):
  print "Running BFS around (%d, %d) + flood fill..." % (ycoord, xcoord)
  white_space = set()
  q = Queue.Queue()
  q.put((ycoord, xcoord))
  visited = set()
  visited.add((ycoord, xcoord))
  boundary = [ycoord, ycoord, xcoord, xcoord]
  
  # need to handle errors
  while not q.empty():
    y, x = q.get()
    if matrix[y][x] >= WHITE_COLOR:
      flood_fill_white(matrix, white_space, y, x, boundary)
      if len(white_space) > MIN_WHITE_PIX:
        break
    for i, j in directions:
      next = (y + i, x + j)
      if in_bounds(next, matrix_bounds) and next not in visited:
        q.put(next)
        visited.add(next)
    
  bubble, blk_pix_cnt, offsets = erase_border(matrix, boundary, white_space)
  if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
    add_grid_lines(bubble)
  else:
    print 'No bubble found with given coordinates'

    
def search_img_for_bubbles(matrix):
  final_img = [list(x) for x in matrix]
  visited = set()
  bubble_count = 0
  print 'Searching for bubbles...'
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
      if pix >= WHITE_COLOR and (i, j) not in visited:
        white_space = set()
        boundary = [i, i, j, j]  # ymin, ymax, xmin, xmax
        flood_fill_white(matrix, white_space, i, j, boundary)
        visited |= white_space
        ymin, ymax, xmin, xmax = boundary
        # is_full_img = ymin == 0 and ymax == len(matrix) - 1 \
                # and xmin == 0 and xmax == len(matrix[0]) - 1
        is_full_img = False
        if len(white_space) > MIN_WHITE_PIX and not is_full_img:
          bubble, blk_pix_cnt, offsets = erase_border(matrix, boundary, \
                                          white_space, str(bubble_count))
          yoffset, xoffset = offsets
          if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
            print '\n%dth bubble found' % (bubble_count + 1)
            print 'Bubble found at:', boundary
            bubble_count += 1
            boxes = add_grid_lines(bubble, str(bubble_count))
            print_to_final_img(final_img, boxes, ymin + yoffset, xmin + xoffset, matrix)
            
  print_image(final_img, 'final_img')
  
  
def print_to_final_img(final_img, boxes, yoffset, xoffset, matrix):
  for box in boxes:
    if not box:
      continue
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
    if has_word:
      ystart = max(0, yoffset + ymin - CHAR_MARGIN)
      yend = min(len(matrix) - 1, yoffset + ymax + CHAR_MARGIN)
      xstart = max(0, xoffset + xmin - CHAR_MARGIN)
      xend = min(len(matrix[0]) - 1, xoffset + xmax + CHAR_MARGIN)
      for i in xrange(ystart, yend + 1):
        final_img[i][xstart] = -1
        final_img[i][xend] = -1
      for j in xrange(xstart, xend + 1):
        final_img[ystart][j] = -1
        final_img[yend][j] = -1


def erase_border(matrix, boundary, white_space, idx=''):
  ymin, ymax, xmin, xmax = boundary
  
  if DBG:
    test_image1 = [[matrix[i][j] \
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    test_image2 = [[100 if (i, j) in white_space else matrix[i][j] 
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    print_image(test_image1, 'original_text_block' + idx)
    print_image(test_image2, 'text_block' + idx)
  
  print "Running 2nd flood fill from corners"
  border_pixels = find_border(matrix, white_space, boundary)
  
  bubble = [[255 if (i, j) in border_pixels else matrix[i][j] \
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  apply_threshold(bubble, WHITE_COLOR, BLACK_COLOR)
  
  if DBG:
    bord = [[0 if (i, j) in border_pixels else matrix[i][j] \
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    print_image(bord, 'borders' + idx)
    print_image(bubble, 'clean_block' + idx)
  
  return tighten_bubble(bubble)


def flood_fill_non_white(white_space, border, boundary, ycoord, xcoord):
  stack = [(ycoord, xcoord)]
  while stack:
    y, x = stack.pop()
    for i, j in directions:
      next = (y + i, x + j)
      if in_bounds(next, boundary) and next not in white_space and next not in border:
        stack.append(next)
        border.add(next)
    
  
def flood_fill_white(matrix, white_space, ycoord, xcoord, boundary):
  stack = [(ycoord, xcoord)]
  white_space.add((ycoord, xcoord))
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
      next = (yn, xn)
      if in_bounds(next, matrix_bounds) and matrix[yn][xn] >= WHITE_COLOR \
            and next not in white_space:
        stack.append(next)
        white_space.add(next)

        
def in_bounds(coord, limits):
  i, j = coord
  ymin, ymax, xmin, xmax = limits
  return i >= ymin and i <= ymax and j >= xmin and j <= xmax
  
  
def apply_threshold(matrix, white_thres=255, black_thres=0):
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] >= white_thres:
        matrix[i][j] = 255
      if matrix[i][j] <= black_thres:
        matrix[i][j] = 0

      
def print_image(matrix, fname):
  blk = (0, 0, 0)           # color black
  wht = (255, 255, 255)     # color white
  grn = (0, 255, 0)
  red = (255, 0, 0)
  
  pixels2 = [grn if x == -1 else red if x == -2 else (x, x, x) for row in matrix for x in row]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  im2.putdata(pixels2)
  im2.save(fname + '.png', "PNG")
  
  
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
    search_for_bubble_around_coord(pixels, y, x)
  else:
    search_img_for_bubbles(pixels)


if __name__ == '__main__':
  main()
