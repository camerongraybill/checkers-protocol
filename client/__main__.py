from sys import argv

import pyuv

from .Interface import Interface
from .client import Client


def start():
    ui = Interface()
    l = pyuv.Loop()
    s = Client("0.0.0.0", 1234, str.encode(argv[1]), str.encode(argv[2]), ui)
    s.start(l)
    l.run()
