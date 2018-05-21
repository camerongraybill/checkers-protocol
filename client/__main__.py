import pyuv

from .client import Client


def start():
    l = pyuv.Loop()
    s = Client("0.0.0.0", 1234)
    s.start(l)
    l.run()
