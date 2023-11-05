import instaloader, sys, glob
from PIL import Image, ImageDraw, ImageOps
import os, sys, math, random

from img2bin import img2bin
from bin2img import bin2img

if __name__=='__main__':
    usernames = sys.argv[1:]
    if not len(usernames):
        usernames = ['coffeeblossom_gearong']
    L = instaloader.Instaloader()
    for username in usernames:
        profile = instaloader.Profile.from_username(L.context, username)
        for post in profile.get_posts():
            L.download_post(post, username)
        files = glob.glob(f'{username}/*.jpg')
        files.extend(glob.glob(f'{username}/*.png'))
        repeat_img = 1
        padsize = 1288        # number of \0 bytes between frames.
        for imgfile in files:
            if '_crop.' in imgfile or 'converted.' in imgfile or '.bin.png' in imgfile:
                continue
            print("encoding %s ..." % imgfile)
            # im = Image.open(imgfile).convert('RGB')       # make sure it is RGB
            data = img2bin(imgfile)
            # print(len(data))
            binfile = f"{imgfile}.bin"
            o = open(binfile, "wb")
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
            bin2img(binfile)
        