import sys, os
import Queue
from PIL import Image

'''
TO DO:
  2. Improve boxing for edge cases:
    - words not aligned
    - spacing between words not consistent in a row or column
      - use heuristic that words are either aligned vertically or horizontally
    - first character/last character

'''


WHITE_COLOR = 245
BLACK_COLOR = 20
MIN_WHITE_PIX = 625
THRES = 128
BUBBLE_MARGIN = 5
CHAR_MARGIN = 2
RATIO_THRES = 0.85
MAX_BOX_NUM = 5
BLACK_PIX_THRES = 20
directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
matrix_bounds = None

  
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
  xmax = xmax + BUBBLE_MARGIN if xmax < len(matrix[0]) - BUBBLE_MARGIN else -1
  ymin = ymin - BUBBLE_MARGIN if ymin >= BUBBLE_MARGIN else 0
  ymax = ymax + BUBBLE_MARGIN if ymax < len(matrix) - BUBBLE_MARGIN else -1
  
  # draw box for debug
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

  
def add_grid_lines(matrix, idx=''):
  print 'Adding grid lines...'
  vert_has_word = [0] * len(matrix)
  horz_has_word = [0] * len(matrix[0])
  
  for i, y in enumerate(matrix):
    for j, x in enumerate(y):
      if x <= BLACK_COLOR:
        vert_has_word[i] = 1
        horz_has_word[j] = 1
        
  box_img_thick = [list(x) for x in matrix]
  box = [list(x) for x in matrix]
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if vert_has_word[i] == 0 or horz_has_word[j] == 0:
        box_img_thick[i][j] = 150
        box[i][j] = -1
  print_image(box_img_thick, 'thick grids' + idx)
  
  # approach 1: make thin grid lines
  center_grids(vert_has_word)
  center_grids(horz_has_word)
      
  box_img = [list(x) for x in matrix]
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if vert_has_word[i] == 0 or horz_has_word[j] == 0:
        box_img[i][j] = 100
  print_image(box_img, 'thin grids' + idx)
  
  # approach 2: merge boxes so that it forms something close to a square
  boxes = process_boxes(box)
  
  merged_box_img = [list(x) for x in box_img_thick]
  for row in boxes:
    for box in row:
      if not box:
        continue
      ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
      if has_word:
        ystart = max(0, ymin - CHAR_MARGIN)
        yend = min(len(matrix) - 1, ymax + CHAR_MARGIN)
        xstart = max(0, xmin - CHAR_MARGIN)
        xend = min(len(matrix[0]) - 1, xmax + CHAR_MARGIN)
        for i in xrange(ystart, yend + 1):
          merged_box_img[i][xstart] = 0
          merged_box_img[i][xend] = 0
        for j in xrange(xstart, xend + 1):
          merged_box_img[ystart][j] = 0
          merged_box_img[yend][j] = 0
  print_image(merged_box_img, 'boxes_merged' + idx)
  return boxes
  
  
def process_boxes(matrix):
  # change image to list of box dimensions
  processed = set()
  boxes = []
  for i, row in enumerate(matrix):
    row_boxes = []
    for j, pix in enumerate(row):
      if pix != -1 and (i, j) not in processed:
        row_boxes.append(get_dimensions(matrix, i, j, processed))
    if row_boxes:
      boxes.append(row_boxes)
  
  matched = [[0] * len(boxes[0]) for i in xrange(len(boxes))]
  for i, row in enumerate(boxes):
    for j, box in enumerate(row):
      ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = box
      if matched[i][j]:
        boxes[i][j] = False
        continue
      if ratio < RATIO_THRES:
        boxes[i][j] = merge_boxes(boxes, i, j, matched)
    
  return boxes


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

  
def get_dimensions(matrix, ycoord, xcoord, processed):
  has_word = False
  i = ycoord
  while i < len(matrix) and matrix[i][xcoord] != -1:
    j = xcoord
    while j < len(matrix[0]) and matrix[i][j] != -1:
      processed.add((i, j))
      if not has_word and matrix[i][j] <= BLACK_COLOR:
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


def search_for_bubble(matrix, ycoord=None, xcoord=None):
  if ycoord and xcoord:
    print "Running BFS + flood fill..."
    white_space = set()
    q = Queue.Queue()
    q.put((ycoord, xcoord))
    visited = set()
    visited.add((ycoord, xcoord))
    boundary = [ycoord, ycoord, xcoord, xcoord]
    
    while not q.empty() and len(white_space) < MIN_WHITE_PIX:
      y, x = q.get()
      if matrix[y][x] >= WHITE_COLOR:
        flood_fill_white(matrix, white_space, y, x, boundary)
          
      for i, j in directions:
        next = (y + i, x + j)
        if in_bounds(next, matrix_bounds) and next in visited:
          continue
        q.put(next)
        visited.add(next)
    add_grid_lines(erase_border(matrix, boundary, white_space))
    return
  
  final_img = [list(x) for x in matrix]
  visited = set()
  bubble_count = 0
  print 'Searching for bubbles...'
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
      if pix >= WHITE_COLOR and (i, j) not in visited:
        white_space = set()
        white_space.add((ycoord, xcoord))
        boundary = [i, i, j, j]  # ymin, ymax, xmin, xmax
        flood_fill_white(matrix, white_space, i, j, boundary)
        visited |= white_space
        ymin, ymax, xmin, xmax = boundary
        if ymin == 0 and ymax == len(matrix) - 1 and xmin == 0 and xmax == len(matrix[0]) - 1:
          continue
        if len(white_space) > MIN_WHITE_PIX:
          info = erase_border(matrix, boundary, \
                 white_space, str(bubble_count))
          bubble, blk_pix_cnt, offsets = info
          yoffset, xoffset = offsets
          if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
            print '\n%dth bubble found' % (bubble_count + 1)
            print 'Bubble found at:', boundary
            bubble_count += 1
            boxes = add_grid_lines(bubble)
            print_to_final_img(final_img, boxes, ymin + yoffset, xmin + xoffset, matrix)
            
  print_image(final_img, 'final_img')
  
  
def print_to_final_img(final_img, boxes, yoffset, xoffset, matrix):
  for row in boxes:
    for box in row:
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
  # test point, save images for debug
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
  bord = [[0 if (i, j) in border_pixels else matrix[i][j] \
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  print_image(bord, 'borders' + idx)
  apply_threshold(bubble, WHITE_COLOR)
  print_image(bubble, 'clean_block' + idx)
  
  return tighten_bubble(bubble)
  
  
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
    boundary[0] = min(boundary[0], y)
    boundary[1] = max(boundary[1], y)
    boundary[2] = min(boundary[2], x)
    boundary[3] = max(boundary[3], x)
    
    for i, j in directions:
      ynext, xnext = y + i, x + j
      next = (ynext, xnext)
      if in_bounds(next, matrix_bounds) and matrix[ynext][xnext] >= WHITE_COLOR and \
            next not in white_space:
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
  
  pixels2 = [(x, x, x) if x != -1 else grn for row in matrix for x in row]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  # im2 = im2.convert("RGB")
  im2.putdata(pixels2)
  im2.save(fname + '.png', "PNG")
  
  
def main():
  global matrix_bounds
  
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
  
  # simulate mouse coordinate
  if len(args) < 2:
    x, y = 114, 319  # corresponds to a text bubble
  else:
    x, y = int(args[1]), int(args[2])
  
  # run flood fill algo
  # search_for_bubble(pixels, y, x)
  search_for_bubble(pixels)


if __name__ == '__main__':
  main()
