import glob
from PIL import Image, ImageDraw
import math, sys, os
import numpy as np

def bin2img(file):
    print(file)
    b = open(file, 'rb').read()
    s = []
    c = b[0x1000:]
    for ix in range(0, 42 * 2700, 42):
        s.append(np.array([int(y) for y in ''.join([f'{x:08b}' for x in c[ix:ix+42]])]))
    w = 1024
    r = w/500
    img = Image.new('RGB', size=(w,w),color='white')
    draw = ImageDraw.Draw(img)
    draw.ellipse((0,0,w,w),fill='black')
    for ix in range(0, 2700, 6):
        cls = np.array(s[ix:ix+6]).sum(axis=0).reshape((112,3))*42
        for l, cl in enumerate(cls):
            x = w/2 + (112 - l) * math.cos(math.pi * 2 * ix / 2700) * w/2/112
            y = w/2 - (112 - l) * math.sin(math.pi * 2 * ix / 2700) * w/2/112
            draw.ellipse((x-r,y-r,x+r,y+r),fill=(cl[2],cl[1],cl[0]),outline=(int(cl[2]*.8),int(cl[1]*.8),int(cl[0]*.8)))
    img.save(f'{file}.png', format='PNG')

if __name__ == '__main__':
    for binfile in sys.argv[1:]:
        if '*' in  binfile:
            files = glob.glob(binfile)
        else:
            files = [binfile]
        for file in files:
            bin2img(file)
            