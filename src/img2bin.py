import glob
from PIL import Image, ImageDraw
import math, sys, os
import numpy as np
from io import BytesIO

def img2bin(img, imgfile=None):
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
    if type(img) == str:
        imgfile = img
        if '.svg' in imgfile:
            import pyvips
            im = pyvips.Image.new_from_file(imgfile, dpi=300)
        else:
            im = Image.open(imgfile).convert('RGB')
    elif type(img) == bytes: 
        if imgfile is None:
            imgfile = 'imgfile'
        im = Image.open(BytesIO(img))
    else:
        return None
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
        # print(i, a0//42)
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
    # tg.save(f'{imgfile}_converted.png', format='PNG')
    return list(np.array(bb).reshape(-1))

from bin2img import bin2img

if __name__ == '__main__':
    for imgfile in sys.argv[1:]:
        if os.path.isdir(imgfile):
            imgfile = f'{imgfile}/*.jpg'
        if '*' in  imgfile:
            files = glob.glob(imgfile)
        else:
            files = [imgfile]
        repeat_img = 1
        padsize = 1288        # number of \0 bytes between frames.            
        for file in files:
            print(file)
            data = img2bin(file)
            binfile = f"{file}.bin"
            o = open(binfile, "wb")
            header = bytearray([0] * 0x1000)
            header[:10] = [ 0x22, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x00, 0x01 ]
            header[0x10:0x16] = [0x0,0x1,0x0,0x1,0x10,0x01]
            header[0xbd0:0xbd7] = [0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11]
            padding = bytes([0] * padsize)
            o.write(bytes(header))
            for rep in range(repeat_img):
                o.write(bytes(data))
                o.write(padding)
            o.close()
            bin2img(binfile)            