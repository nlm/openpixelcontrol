#!/usr/bin/env python

"""A demo client for Open Pixel Control
http://github.com/zestyping/openpixelcontrol

Creates a shifting rainbow plaid pattern by overlaying different sine waves
in the red, green, and blue channels.

To run:
First start the gl simulator using the included "wall" layout

    make
    bin/gl_server layouts/wall.json

Then run this script in another shell to send colors to the simulator

    python_clients/raver_plaid.py

"""

from __future__ import print_function, division
import time
import math
import sys
import random
import argparse

import opcmatrix

#-------------------------------------------------------------------------------
# handle command line

choices = ['matrix', 'image', 'anim', 'test']
drivers = {
    'tetris': opcmatrix.TetrisMatrixDriver,
    'viktetris': opcmatrix.VikTetrisMatrixDriver,
    'freespace': opcmatrix.FreespaceMatrixDriver,
}

parser = argparse.ArgumentParser()
parser.add_argument('-H', dest='IP_PORT', default="127.0.0.1:7890",
                    help='IP:PORT to connect to')
parser.add_argument('-t', dest='type', metavar='type', required='True',
                    choices=choices, help='the feature to show')
parser.add_argument('-F', dest='fps', metavar='fps', type=float,
                    help='number of frames per second', default=0)
parser.add_argument('-I', dest='iframes', metavar='frames', type=int,
                    help='interpolation frames', default=0)
parser.add_argument('-d', dest='driver', metavar='driver', type=str,
                    default='freespace', choices=drivers.keys(),
                    help='the screen driver')
parser.add_argument('-f', dest='file', metavar='file', type=str,
                    default='image.jpg', help='image file to load')
parser.add_argument('-R', dest='resize', metavar='mode', type=int,
                    default=2, help='resize mode (0=fill, 1=adj, 2=crop')
args = parser.parse_args()

#-------------------------------------------------------------------------------
# connect to server

client = opcmatrix.Client(args.IP_PORT)
if client.can_connect():
    print('connected to {}'.format(args.IP_PORT))
else:
    print('error: could not connect to {}'.format(args.IP_PORT))
    sys.exit(1)

#-------------------------------------------------------------------------------
# start processing

print('using {} driver'.format(args.driver))
driver = drivers[args.driver]()
matrix = None
animated = False

if args.type == 'matrix':
    animated = True
    matrix = opcmatrix.MatrixMatrix(client, driver,
                                    args.fps + 1, args.iframes)
elif args.type == 'anim':
    animated = True
    matrix = opcmatrix.AnimatedImageMatrix(client, driver,
                                           args.fps, args.iframes)
    matrix.load(args.file, args.resize)
elif args.type == 'image':
    matrix = opcmatrix.ImageMatrix(client, driver)
    matrix.load(args.file, args.resize)
elif args.type == 'test':
    matrix = opcmatrix.TestMatrix(client, driver)


if animated:
    try:
        matrix.renderloop()
    except BaseException as e:
        print(e)
        matrix.clear()
        matrix.render()
    finally:
        client.disconnect()
        sys.exit(0)
else:
    try:
        matrix.render()
    except BaseException as e:
        print(e)
        matrix.clear()
        matrix.render()
    finally:
        client.disconnect()
        sys.exit(0)
