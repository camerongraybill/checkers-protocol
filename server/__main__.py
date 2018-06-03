from sys import argv

import pyuv

from .server import Server


def start():
    l = pyuv.Loop()
    s = Server(argv[1], argv[2], 8864)
    s.start(l)
    l.run()
