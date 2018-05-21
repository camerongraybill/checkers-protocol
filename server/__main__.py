import pyuv

from .server import Server


def start():
    l = pyuv.Loop()
    s = Server("0.0.0.0", 1234)
    s.start(l)
    l.run()
