import sys, os
import Queue
from PIL import Image

'''
TO DO:
  1. Determine if mouse is hovering over bubble or over nothing

'''


WHITE_COLOR = 245
BLACK_COLOR = 20
MIN_WHITE_PIX = 625
THRES = 128
BUBBLE_MARGIN = 5
CHAR_MARGIN = 2
RATIO_THRES = 0.85
directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
matrix_bounds = None

def max_black_sq(matrix):
  return
  
  
def tighten_bubble(matrix):
  print "Cropping extra white space..."
  xmin = len(matrix[0])
  xmax = -1
  ymin = len(matrix)
  ymax = -1
    
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] <= BLACK_COLOR:
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
    
  print_image(box, 'box_lines')
  
  return [[matrix[i][j] for j in xrange(xmin, xmax + 1)] for i in xrange(ymin, ymax + 1)]

  
def add_grid_lines(matrix):
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
  print_image(box_img_thick, 'thick grids')
  
  # approach 1: make thin grid lines
  center_grids(vert_has_word)
  center_grids(horz_has_word)
      
  box_img = [list(x) for x in matrix]
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if vert_has_word[i] == 0 or horz_has_word[j] == 0:
        box_img[i][j] = 100
  print_image(box_img, 'thin grids')
  
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
        yend = min(len(matrix), ymax + 1 + CHAR_MARGIN)
        xstart = max(0, xmin - CHAR_MARGIN)
        xend = min(len(matrix[0]), xmax + 1 + CHAR_MARGIN)
        for i in xrange(ystart, yend):
          merged_box_img[i][xstart] = 0
          merged_box_img[i][xend - 1] = 0
        for j in xrange(xstart, xend):
          merged_box_img[ystart][j] = 0
          merged_box_img[yend - 1][j] = 0
  print_image(merged_box_img, 'boxes_merged')
  
  
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
        
  # for x in boxes:
    # print x
    
  return boxes


def merge_boxes(boxes, ycoord, xcoord, matched):
  matched[ycoord][xcoord] = 1
  curr_box = boxes[ycoord][xcoord]
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, has_word = curr_box
  if ylen > xlen:
    # merge boxes to the right
    for j in xrange(xcoord + 1, min(xcoord + 3, len(boxes[0]))):
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
    # merge boxes below
    for i in xrange(ycoord + 1, min(ycoord + 3, len(boxes))):
      next_box = boxes[i][xcoord]
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, has_word1 = next_box
      new_ratio = box_ratio(ylen + ymax1 - ymax, xlen)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        ylen += ymax1 - ymax
        ymax = ymax1
        has_word |= has_word1
        matched[i][xcoord] = 1
  
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
  ylen, xlen = i - 1 - ycoord, j - 1 - xcoord
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

'''
Returns the image within the text bubble that encloses the coordinate of the cursor

'''
def crop_bubble(matrix, ycoord, xcoord):
  # records the max and min of x/y for copying to another list later
  # ymin, ymax, xmin, xmax
  boundary = [ycoord, ycoord, xcoord, xcoord]
  
  # stores the coordinates of pixels that should be cropped
  white_space = set()
  white_space.add((ycoord, xcoord))
  
  white_pix_count = 0
  
  # 1st pass, find white pixels using bfs
  # keep doing bfs and run flood fill until some minimum amount
  # of pixels are filled
  # TODO: set upper limit for amount of pixels on bfs for invalid mouse positions
  print "Running BFS + flood fill..."
  q = Queue.Queue()
  visited = set()
  q.put((ycoord, xcoord))
  visited.add((ycoord, xcoord))
  
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
  
  print boundary
  ymin, ymax, xmin, xmax = boundary
  
  # test point, save image for debug
  print "Saving debug images"
  test_image1 = [[matrix[i][j] \
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  print_image(test_image1, 'original_text_block')
  
  test_image2 = [[100 if (i, j) in white_space else matrix[i][j] 
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  print_image(test_image2, 'text_block')
  
  # 2nd pass, find all enclosed areas
  # check all adjacent pixels that are filled, run another
  # flood fill to find if that area is enclosed by white space
  print "Running 2nd flood fill from corners"
  border_pixels = find_border(matrix, white_space, boundary)
  
  # 3rd pass
  # copy all pixels within text bubble to a new 2D list
  print "Saving debug image 2 and 3"
  bubble = [[255 if (i, j) in border_pixels else matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]

  # print images for debug
  bord = [[0 if (i, j) in border_pixels else matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  print_image(bord, 'borders')
  apply_threshold(bubble, WHITE_COLOR)
  print_image(bubble, 'clean_block')
  
  return bubble

  
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
  
  pixels2 = [(matrix[i][j], matrix[i][j], matrix[i][j]) for i in xrange(len(matrix)) \
              for j in xrange(len(matrix[0]))]
  
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
  bubble = crop_bubble(pixels, y, x)
  
  # tighten boundaries and try drawing grid lines
  text_image = tighten_bubble(bubble)
  
  add_grid_lines(text_image)


if __name__ == '__main__':
  main()
