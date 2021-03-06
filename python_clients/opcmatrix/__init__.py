from __future__ import division, print_function, absolute_import
import time
import math
import sys
import random

from .opc import Client

#-------------------------------------------------------------------------------
# MatrixDriver

class MatrixDriver(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def getidx(self, x, y):
        if x > self.width or y > self.height:
            raise IndexError
        return x * self.height + y


class TetrisMatrixDriver(MatrixDriver):

    def __init__(self):
        super(TetrisMatrixDriver, self).__init__(10, 20)


class VikTetrisMatrixDriver(TetrisMatrixDriver):

    def getidx(self, x, y):
        if x > self.width or y > self.height:
            raise IndexError
        if x % 2 == 0:
            return x * self.height + y
        else:
            return x * self.height + self.height - y - 1


class FreespaceMatrixDriver(MatrixDriver):

    def __init__(self):
        super(FreespaceMatrixDriver, self).__init__(25, 25)

    def getidx(self, x, y):
        if x > self.width or y > self.height:
            raise IndexError
        if x % 2 == 1:
            return (self.width - x - 1) * self.height + y
        else:
            return (self.width - x) * self.height - y - 1

#-------------------------------------------------------------------------------
# Matrix

class Matrix(object):

    def __init__(self, client, driver, channel=0):
        self.client = client
        self.driver = driver
        self.channel = channel
        self.width = self.driver.width
        self.height = self.driver.height
        self.pixels = [[0, 0, 0] for _ in range(self.width * self.height)]

    def fill(self, rgb):
        for i in range(self.width * self.height):
            self.pixels[i] = rgb

    def getpixel(self, x, y):
        return self.driver.getpixel(x, y)

    def setpixel(self, x, y, pixel):
        return self.driver.setpixel(x, y, pixel)

    def clear(self):
        self.fill([0, 0, 0])

    def render(self):
        self.driver.render(self.client)

    def getpixel(self, x, y):
        return self.pixels[self.driver.getidx(x, y)]

    def setpixel(self, x, y, pixel):
        try:
            self.pixels[self.driver.getidx(x, y)] = pixel
        except IndexError:
            print('IndexError: set pixel {}x{} -> {}'.format(x, y, pixel))
            raise

    def render(self):
        self.client.put_pixels(self.pixels, channel=self.channel)


class AutoMatrix(Matrix):

    def __init__(self, client, driver, fps=0, iframes=0):
        super(AutoMatrix, self).__init__(client, driver)
        self.fps = float(fps)
        self.iframes = iframes
        self.init()

    def init(self):
        pass

    def update(self):
        pass

    def renderloop(self):
        if self.fps <= 0:
            raise Exception('fps <= 0')
        while True:
            if self.iframes == 0:
                starttime = time.time()
                self.update()
                self.render()
                endtime = time.time()
                time.sleep(max(0, 1 / self.fps - (endtime - starttime)))
            else:
                startframe = [list(pixel) for pixel in self.pixels]
                self.update()
                endframe = [list(pixel) for pixel in self.pixels]
                for frame in range(self.iframes):
                    starttime = time.time()
                    self.pixels = [[t1 + ((t2 - t1) * (frame + 1) / (self.iframes + 1))
                                  for t1, t2 in zip(startpixel, endpixel)]
                                  for startpixel, endpixel in zip(startframe, endframe)]
                    self.render()
                    endtime = time.time()
                    time.sleep(max(0, 1 / (self.fps * (1 + self.iframes))
                                      - (endtime - starttime)))
                starttime = time.time()
                self.pixels = endframe
                self.render()
                endtime = time.time()
                time.sleep(max(0, 1 / (self.fps * (1 + self.iframes))
                                  - (endtime - starttime)))

#-------------------------------------------------------------------------------
# Test Matrix


class TestMatrix(Matrix):

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        for i in range(self.width * self.height):
            self.pixels[i] = list((255, 255, 255))
        self.setpixel(0, 0, (255, 0, 0))


#-------------------------------------------------------------------------------
# Image Matrix

from PIL import Image

class ImageMatrix(Matrix):

    rsz_fill = 0
    rsz_adjust = 1
    rsz_crop = 2

    def load(self, filename, rsz_mode=0):
        with Image.open(filename) as im:
            self.feed(im, rsz_mode)

    def getimgsize(self, image, rsz_mode):
        
        # Infos
        #print('display size: {}x{}'.format(self.width, self.height))
        dsp_ratio = self.width / self.height
        #print('display ratio is {}'.format(dsp_ratio))
        (img_width, img_height) = image.size
        #print('image size: {}x{}'.format(img_width, img_height))
        img_ratio = img_width / img_height
        #print('image ratio is {}'.format(img_ratio))

        # Compute new size
        if rsz_mode == ImageMatrix.rsz_fill:
            return (self.width, self.height)
        elif rsz_mode == ImageMatrix.rsz_adjust:
            # Landscape
            if img_ratio > dsp_ratio:
                width = int(self.width)
                height = int(img_height * width / img_width)
            # Portrait
            else:
                height = int(self.height)
                width = int(img_width * height / img_height)
            return (width, height)
        elif rsz_mode == ImageMatrix.rsz_crop:
            # Landscape
            if img_ratio < dsp_ratio:
                width = int(self.width)
                height = int(img_height * width / img_width)
            # Portrait
            else:
                height = int(self.height)
                width = int(img_width * height / img_height)
            return (width, height)
        else:
            raise ValueError

    def feed(self, image, rsz_mode=1):

        # Calculating size
        (width, height) = self.getimgsize(image, rsz_mode)
        #print('mode: {}'.format(rsz_mode))
        #print('image render size: {}x{}'.format(width, height))
        offset_x = int((self.width - width) / 2)
        offset_y = int((self.height - height) / 2)
        #print('offsets: {}x{}'.format(offset_x, offset_y))

        # Feeding data to the internal matrix
        self.clear()
        data = list(image.convert('RGB').resize((width, height), Image.BICUBIC).getdata())

        for y in range(height):
            for x in reversed(range(width)):
                if (0 < x + offset_x < self.width and
                    0 < y + offset_y < self.height):
                    self.setpixel(x + offset_x, y + offset_y, data.pop())
                else:
                    data.pop()


class AnimatedImageMatrix(AutoMatrix, ImageMatrix):

    def __init__(self, *args, **kwargs):
        super(AnimatedImageMatrix, self).__init__(*args, **kwargs)
        self.img = None

    def load(self, filename, rsz_mode=0):
        self.img = Image.open(filename)
        if self.fps == 0:
            self.fps = 1000 / max(self.img.info['duration'], 10)
            print('auto-set fps to {}'.format(self.fps))
        self.frame = 0
        self.rsz_mode = rsz_mode

    def update(self):
        if self.img is None:
            return
        try:
            self.img.seek(self.frame)
            self.frame += 1
        except EOFError:
            self.frame = 0
            self.img.seek(self.frame)
            self.frame += 1
        self.feed(self.img, self.rsz_mode)

#-------------------------------------------------------------------------------
# Text Matrix

from PIL import ImageFont, ImageDraw

class TextMatrix(ImageMatrix):

    def print(self, text):
        font = ImageFont.load_default()
        (width, height) = font.getsize(text)
        print('text {}x{}'.format(width , height))
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        draw.text((width, height), text, font=font, fill=(255, 255, 255))
        draw.point((0, 0), (255, 255, 255))
        self.feed(img, 0)
        img.show()
        img.close()

#-------------------------------------------------------------------------------
# Misc Matrix


class MatrixMatrix(AutoMatrix):

    def update(self):
        for x in range(self.width):
            for y in range(self.height - 1):
               self.setpixel(x, y, self.getpixel(x, y + 1))
               self.setpixel(x, y + 1, [p * 0.8 for p in self.getpixel(x, y + 1)])
            if random.random() > 0.93:
                # Disco Mode
                #self.setpixel(x, self.height - 1, (random.random() * 255, random.random() * 255, random.random() * 255))
                self.setpixel(x, self.height - 1, [0, 255, 0])

#        for x in range(self.width):
#            self.data[x].pop(0)
#            if random.random() > 0.93:
#                self.data[x].append((0, 255, 0))
#            else:
#                trio = self.data[x][-1]
#                new = [int(_ * 0.99 if _ > 250 else _ * 0.70) for _ in trio]
#                self.data[x].append(new)

#class PongMatrix(AutoMatrix):
#
#    class Player(object):
#
#        def __init__(self, y, d):
#            self.y = y
#            self.d = d
#
#    def init(self):
#        self.psize = 4
#        self.players = (PongMatrix.Player(int(self.height / 2 - self.psize / 2), 1),
#                        PongMatrix.Player(int(self.height / 2 - self.psize / 2), -1))
#
#    def update_players(self):
#       for p in self.players:
#            if (p.d > 0 and p.y + self.psize + p.d <= self.height) or (p.d < 0 and p.y + p.d >= 0):
#                p.y += p.d
#            else:
#                p.d = -p.d
#                p.y += p.d
#
#    def update(self):
#
#        self.update_players()
#
#        for y in range(self.height):
#            self.data[0][y] = (0, 0, 0)
#            self.data[-1][y] = (0, 0, 0)
#
#        for y in range(self.psize):
#            self.data[0][self.players[0].y + y] = (255, 255, 255)
#            self.data[-1][self.players[1].y + y] = (255, 255, 255)
