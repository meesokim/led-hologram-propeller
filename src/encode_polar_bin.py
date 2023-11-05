#! /usr/bin/python3
#
# encode_polar_bin.py -- fun with polar coordinates.
#
# rgb_bit_columns() implements the pattern described in the README.
# It seems correct!
#
# Usage:
#  env HOLO_REP_IMG=1 $0 image1.jpg [image2.jpg ...]
#
# output file: rgb_enc_01.bin
#
# 2020-03-20, jw v0.4 -- using ordered dither instead of error diffusion to reduce color noise.
#

version = '0.4'

from PIL import Image, ImageDraw, ImageOps
import os, sys, math, random

debug = False    # use small test values
verbose = False  # print everthing...

diam_def = 360        # input png image width
n_rays = 2700         # 113400 / 42
padsize = 1288        # number of \0 bytes between frames.
leds = 224            # That is what the device says, (I did not count them :-))
repeat_img = 1        # 1: full speed 10fps, 30: show each image 3sec

try:
  repeat_img = max(repeat_img, int(os.environ.get('HOLO_REP_IMG')))
except:
  pass


def quad_avg(pix_acc, x, y):
  """
     pix_acc is a https://pillow.readthedocs.io/en/latest/reference/PixelAccess.html
     x,y must be in range. E.g. Image width=360, x in [0..359],
     A small epsilon is allowed beyond the last element, as x and y are expected as
     floating point coordinates. quad_avg() returns a weighted average pixel color from
     the four neighboring pixels.
     Each channel is averaged indepently. Good for RGB, but may not work as well for HLS)
     Any number of channels.
     A tuple of rounded integer values is returned.
  """
  x0 = int(x)
  xd = x - x0
  y0 = int(y)
  yd = y - y0
  r = []
  d_eps = 0.0001
  # expect 3 colors, but any is fine.
  for col in range(len(pix_acc[0,0])):
    if xd <= d_eps:
      y0_avg = pix_acc[x0,y0][col]
      if yd > d_eps:
        y1_avg = pix_acc[x0,y0+1][col]
    else:
      y0_avg = pix_acc[x0,y0][col]   * (1-xd) + pix_acc[x0+1,y0][col]   * xd
      if yd > d_eps:
        y1_avg = pix_acc[x0,y0-1][col] * (1-xd) + pix_acc[x0+1,y0+1][col] * xd
    if yd <= d_eps:
      r.append(int(y0_avg + 0.5))
    else:
      r.append(int(y0_avg * (1-yd) + y1_avg * yd + 0.5))
  return tuple(r)


def polar2cart(cx, cy, r, phi):
  """
      clock position    phi
        3h              math.radians(0) = 0
        1h30            math.radians(45)
        12h             math.radians(90)
        9h              math.radians(180)
        6h              math.radians(270)
        4h30            math.radians(315)
   """
  x = cx + r * math.cos(phi)
  y = cy + r * math.sin(phi)
  return (x, y)


def rgb_bit_columns(x, width):
  #            0   1   2   3   4   5   6   7
  #           ---+---+---+---+---+---+---+---
  zigzag_r = [ 16, 19, 22, 9,  12, 15, 2,  5 ]
  zigzag_g = [ 17, 20, 23, 10, 13, 0,  3,  6 ]
  zigzag_b = [ 18, 21, 8,  11, 14, 1,  4,  7 ]
  o = width - 24 - x // 8 * 8 * 3
  m = x % 8
  return (o + zigzag_r[m], o + zigzag_g[m], o + zigzag_b[m])


def ordered_dith(x, y, val):
  """ val is expected in 0...255
      x is used modulo 2
      y is used modulo 12

      The dither pattern has 13 different values. We duplicate the first and the last value to
      stretch the typical video range of [16..240] back into [0..255]
  """
  dith = (
    ( 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0 ),
    ( 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0 ),
    ( 1, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0 ),
    ( 1, 0, 0, 0, 0, 0,  1, 0, 0, 0, 0, 0 ),
    ( 1, 1, 0, 0, 0, 0,  1, 0, 0, 0, 0, 0 ),
    ( 1, 1, 0, 0, 0, 0,  1, 1, 0, 0, 0, 0 ),
    ( 1, 1, 1, 0, 0, 0,  1, 1, 0, 0, 0, 0 ),
    ( 1, 1, 1, 0, 0, 0,  1, 1, 1, 0, 0, 0 ),
    ( 1, 1, 1, 1, 0, 0,  1, 1, 1, 0, 0, 0 ),
    ( 1, 1, 1, 1, 0, 0,  1, 1, 1, 1, 0, 0 ),
    ( 1, 1, 1, 1, 1, 0,  1, 1, 1, 1, 0, 0 ),
    ( 1, 1, 1, 1, 1, 0,  1, 1, 1, 1, 1, 0 ),
    ( 1, 1, 1, 1, 1, 1,  1, 1, 1, 1, 1, 0 ),
    ( 1, 1, 1, 1, 1, 1,  1, 1, 1, 1, 1, 1 ),
    ( 1, 1, 1, 1, 1, 1,  1, 1, 1, 1, 1, 1 )
  )
  val = max(0, min(255, int(val)))      # clamp and
  v14 = int(val / 17.01)                # squeeze into [0..14]
  d = dith[v14]
  y += 6 * (int(x) % 2)
  return d[int(y) % 12]


def encode_polar_bin(im, diam=diam_def, c_x=None, c_y=None):
  if c_x == None: c_x = (diam-1.)/2
  if c_y == None: c_y = (diam-1.)/2
  pix = im.load()
  # prepare a frame polar distortion
  po_width = leds // 2 * 3
  po = []
  for i in range(po_width):
    po.append([])

  for n in range(n_rays):
    phi = math.radians(360.*(n_rays-n)/n_rays)
    sca = float(diam-1)/float(leds-1)
    print(n)
    if verbose:
      print("n=%d\t" % n, end='')
    for led in range(leds//2):
      (x,y) = polar2cart(c_x, c_y, (0.5+led) * sca, phi)
      print(int(x),int(y))
      if verbose:
        print("(%.2f, %.2f) " % (x,y), end="")
      rgb = quad_avg(pix, x, y)
      ### bit interleaved in 24 bits for 8 rings.
      (cr,cg,cb) = rgb_bit_columns(led, po_width)
      print(cr,cg,cb)
      po[cr].append(rgb[0])
      po[cg].append(rgb[1])
      po[cb].append(rgb[2])

    if verbose:
      print("")

  ## prepare a frame for the binary format
  out = []
  for n in range(n_rays):
    out.append([0] * (3*leds//16))      # number of bytes = po_width / 8 = 42

  for column in range(len(po)):
    byte   =       column // 8
    bitval = 1 << (column % 8)
    for n in range(n_rays):
      val = po[column][n]
      if ordered_dith(column, n, val):
        out[n][byte] |= bitval
  return out

import numpy as np
def encode_polar_bin2(imgfile):
    leds = 224
    ledh = leds//2
    n_rays = 2700//6
    # tg = Image.new('RGB',(ledh, n_rays))
    R = 0
    G = 1
    B = 2
    m = [(2,G),(2,B),(1,R),(1,G),(1,B),(0,R),(0,G),(0,B),(5,B),(4,R),(4,G),(4,B),(3,R),(3,G),(3,B),(2,R),(7,R),(7,G),(7,B),(6,R),(6,G),(6,B),(5,R),(5,G)]
    am = np.array(m).reshape(3, 8, 2)
    num = 0
    if '.svg' in imgfile:
        import pyvips
        im = pyvips.Image.new_from_file(imgfile, dpi=300)
    else:
        im = Image.open(imgfile).convert('RGB')
    width, height = im.size   # Get dimensions
    r = min(im.size)
    left = (width - r)/2
    top = (height - r)/2
    right = (width + r)/2
    bottom = (height + r)/2
    bb = []
    # Crop the center of the image
    im = im.crop((left, top, right, bottom))    
    image = im.resize((leds,leds))
    image.save(f'{imgfile}_crop.png', format='PNG')
    tg = Image.new('RGB',(ledh,n_rays))
    dith = np.array([[0,0,0,0,0,0],
            [1,0,0,0,0,0],
            [1,1,0,0,0,0],
            [1,1,1,0,0,0],
            [1,1,1,1,0,0],
            [1,1,1,1,1,0],
            [1,1,1,1,1,1]])
    for i in range(n_rays):
        part = image.rotate(-360/n_rays*i).crop((ledh,ledh,leds,ledh+1))
        tg.paste(part, (0,i))
        a0 = np.array(part)[0][::-1,:3]
        print(i, a0//42)
        a = (a0//42)
        b = [[],[],[],[],[],[]]
        for block in range(0, ledh, 8):
            for each_byte in am:
                c=np.array([0,0,0,0,0,0])
                for ix, each_bit in enumerate(each_byte):
                    c += (dith[a[block:][tuple(each_bit)]]<<ix)
                # print(block, num, c)
                b[0].append(c[5])
                b[1].append(c[4])
                b[2].append(c[3])
                b[3].append(c[2])
                b[4].append(c[1])
                b[5].append(c[0])
                num += 1
        bb.append(b)
        # tg.paste(part, (0, i))
    # display(tg)
    tg.save(f'{imgfile}_converted.png', format='PNG')
    return list(np.array(bb).reshape(-1))

def polar_bin_test(x=-1):
  ## prepare a frame for the binary format
  bytes_per_column = 3*leds//16
  out = []
  for n in range(n_rays):
    out.append([0] * bytes_per_column)
  out[0] = [255] * bytes_per_column

  for n in range(n_rays-20):
    if (n//20) < 128:
      out[n][24] = n//20
      out[n][26] = 128 + n//20
    if (n//100) < 8:
      out[n][10] = 1 << (n//100)
      out[n][0] = 1 << (n//100)
      out[n][1] = 1 << (n//100)
      out[n][2] = 1 << (n//100)
      out[n][3] = 1 << (n//100)
      out[n][4] = 1 << (n//100)
  return out



# for i in range(20):
#   data = polar_bin_test(i)
import glob
files = sys.argv[1:]
for imgfile in files:
    if '*' in imgfile:
        imgfiles = glob.glob(imgfile)
    else:
        imgfiles = [imgfile]
    # print(imgfiles)
    for imgfile in imgfiles:
        if '.crop.' in imgfile or 'converted.' in imgfile:
            continue
        if repeat_img > 1:
            print("encoding %s (%d)..." % (imgfile, repeat_img))
        else:
            print("encoding %s ..." % imgfile)
        # im = Image.open(imgfile).convert('RGB')       # make sure it is RGB
        data = encode_polar_bin2(imgfile)
        # print(len(data))
        o = open(f"{imgfile}.bin", "wb")
        header = bytearray([0] * 0x1000)
        header[:10] = [ 0x22, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x00, 0x01 ]
        header[0x10:0x16] = [0x0,0x1,0x0,0x1,0x10,0x01]
        header[0xbd0:0xbd7] = [0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11]
        # header = [ 0x00, 0x00, 0x00, 0x3c, 0x18 ]               # seen with Gif-Anims
        # header = [ 0x00, 0x00, 0x00, 0x01, 0x18 ]             # seen with mp4
        padding = bytes([0] * padsize)
        # for i in range(len(header), 0x1000):
        #     header.append(0)
        o.write(bytes(header))
        for rep in range(repeat_img):
            # for row in data:
                # print(row)
            o.write(bytes(data))
            o.write(padding)
        o.close()

