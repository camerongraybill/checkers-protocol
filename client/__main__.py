from sys import argv

import pyuv

from .Interface import Interface
from .client import Client


def start():
    ui = Interface()
    l = pyuv.Loop()
    s = Client(argv[1], 1234, str.encode(argv[2]), str.encode(argv[3]), ui)
    s.start(l)
    l.run()
