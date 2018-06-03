from socket import socket, AF_INET, SOCK_DGRAM
from sys import argv

import pyuv

from .Interface import Interface
from .client import Client


def listen_for_addr():
    s = socket(AF_INET, SOCK_DGRAM)
    s.bind(('0.0.0.0', 8864))
    data = s.recvfrom(1024)
    s.close()
    return data[1][0]


def start():
    print(listen_for_addr())
    ui = Interface()
    l = pyuv.Loop()
    if len(argv) < 4:
        argv[3] = listen_for_addr()
    s = Client(argv[3], 8864, str.encode(argv[1]), str.encode(argv[2]), ui)
    s.start(l)
    l.run()
