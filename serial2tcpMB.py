# -*- coding: utf-8 -*-

import serial
import socket
import struct
from datetime import datetime

#bad but working
import sys
sys.path.insert(0, 'd:\\Azat\\PycharmProjects\\first')
from crc16 import checkCRC
#from ttcpServer import simpleCheck

ser = serial.Serial()

ser.baudrate = 19200
ser.port = 'COM2'
ser.bytesize = 8
ser.parity = 'N'
ser.stopbits = 1
ser.timeout = None
ser.xonxoff = 0
ser.rtscts = 0

print ser.is_open
ser.open()
print ser.is_open
ser.write("hello!!!")
ser.close()

print ser.is_open
ser.open()
print ser.is_open
ser.write("hello!!!")
ser.close()

#[addr of rtu slave, addr of tcp slave, ip, port]
settings = [
    [17, 17, "192.168.0.117", 502],
    [11, 11, "192.168.0.111", 502],
    [14, 4, "192.168.0.69", 502],
]


def column(matrix, i):
    return [row[i] for row in matrix]

allowed_id = column(settings,0)


class ErrorResp():
    """errors here!!!"""

    def __init__(self):
        pass

    crc_fail = "\x81\x99"
    no_id = "\x81\x100"

    cant_open_tcp_port = "\x81\x101"
    tcp_timeout_reached = "\x81\x102"


request_frm = ">bbHHbb"


def get_addr_port(id):
    return addr, port


def change_req_rtu2tcp(req_as_list):
    return req_as_list, get_addr_port()


def change_req_tcp2rtu(req_as_str):
    return req_as_str


if __name__ == '__main__':
    exit()

    for _ in range(100):
        if ser.is_open:
            print "waiting for input request"
            req_raw = ser.read(size=8)
            if checkCRC(req_raw):
                print "Error in CRC"
                ser.write(ErrorResp.crc_fail)
                continue
            req_list, addr, port = struct.unpack(request_frm, req_raw)
            req_id = req_list[1]

            if req_id not in allowed_id:
                print "ID is not allowed"
                ser.write(ErrorResp.no_id)
                continue
            req_tcp = change_req_rtu2tcp(req_as_list=req_list)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2.0)
            try:
                sock.connect((addr, port))
            except socket.error, e:
                print "Connection to %s on port %s failed: %s" % (addr, port, e)
                sock.close()
                ser.write(ErrorResp.cant_open_tcp_port)
                continue
            sock.send(req_tcp)
            res_tcp = sock.recv(1024)
            if res_tcp is None:
                print "Timeout reached"
                sock.close()
                ser.write(ErrorResp.tcp_timeout_reached)
                continue
            sock.close()
            res_rtu = change_req_tcp2rtu(req_as_str=res_tcp)
            ser.write(res_rtu)
            print "data sended OK!"

        else:
            ser.close()
            ser.open()

