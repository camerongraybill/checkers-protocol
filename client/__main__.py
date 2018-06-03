from socket import socket, AF_INET, SOCK_DGRAM
from sys import argv

import pyuv

from .Interface import Interface
from .client import Client


def listen_for_addr():
    s = socket(AF_INET, SOCK_DGRAM)
    s.bind((' ', 8864))
    data = s.recvfrom(1024)


def start():
    print(listen_for_addr())
    ui = Interface()
    l = pyuv.Loop()
    s = Client(argv[1], 8864, str.encode(argv[2]), str.encode(argv[3]), ui)
    s.start(l)
    l.run()
