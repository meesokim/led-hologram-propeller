import streamlit as st
import os, sys
sys.path.append('src')

title = '커피블라썸-개롱역'
st.set_page_config(page_title=title, page_icon = 'favicon.png', initial_sidebar_state = 'auto')
st.header(f':coffee: {title} :cake:', divider='rainbow')
st.title('홀로그램 팬 파일 변환')

import glob
from io import BytesIO
from img2bin import img2bin
from bin2img import bin2img
from pathlib import Path
import instaloader

if not os.path.exists('./static'):
    os.mkdir('./static')

uploaded_files = st.file_uploader('Image', accept_multiple_files=True, type=['png','jpg'])
if len(uploaded_files):
    for file in uploaded_files:
        data = img2bin(file.getvalue(), file.name)
        if data is not None:
            binfile = f"{file.name}.bin"
            if not os.path.exists(binfile):
                repeat_img = 1
                padsize = 1288        # number of \0 bytes between frames.           
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
            st.download_button("Download", open(binfile, 'rb').read(), binfile)
            st.image(f'{binfile}.png')
else:
    L = instaloader.Instaloader()
    cnt = 10
    usernames = ['coffeeblossom_gaerong']
    for username in usernames:
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            for post in profile.get_posts():
                L.download_post(post, username)
                cnt -= 1
                if cnt==0:
                    break
        except:
            import traceback 
            traceback.print_exc()
        files = glob.glob(f'{username}/*.jpg')
        repeat_img = 1
        padsize = 1288        # number of \0 bytes between frames.        
        for imgfile in files[::-1]:
            if '_crop.' in imgfile or 'converted.' in imgfile or '.bin.png' in imgfile:
                continue
            binfile = f'{imgfile}.bin'
            if not os.path.exists(binfile):
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
            file = imgfile.replace('jpg','txt')
            if os.path.exists(file):
                st.markdown(open(file, encoding='utf-8').read())
            st.download_button("Download", open(binfile, 'rb').read(), binfile)
            st.image(f'{binfile}.png')        