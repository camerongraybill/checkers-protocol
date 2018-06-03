from sys import argv

import pyuv

from .server import Server


def start():
    l = pyuv.Loop()
    if len(argv) < 3:
        argv[2] = None
    s = Server(argv[1], argv[2], 8864)
    s.start(l)
    l.run()
