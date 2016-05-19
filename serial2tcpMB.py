# -*- coding: utf-8 -*-

import serial
import socket
import struct
from datetime import datetime
hexString = lambda byteString: " ".join(x.encode('hex') for x in byteString)

#bad but working
import sys
try:
    sys.path.insert(0, 'd:\\Azat\\PycharmProjects\\first')
    from crc16 import checkCRC, addCRC
    #from ttcpServer import simpleCheck
except:
    print "Smth is wrong in import"

ser = serial.Serial()

ser.baudrate = 19200
ser.port = 'COM5'
ser.bytesize = 8
ser.parity = 'N'
ser.stopbits = 1
ser.timeout = None
ser.xonxoff = 0
ser.rtscts = 0

"""
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
"""

#[addr of rtu slave, addr of tcp slave, ip, port]
settings = [
    [17, 17, "192.168.0.117", 502],
    [11, 11, "192.168.0.111", 502],
    [14, 4, "192.168.0.69", 502],
]

def vlook_up(value, matrix, col):
    for m in matrix:
        if m[col] is value:
            return m
    return None

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


req_frm_rtu = ">bbHHbb"     # 17, 3, 40960, 100, crc1, crc2
req_frm_tcp = ">bbHHbbHH"   # 10, 0, 0, 6, 17, 3, 40960, 100

def change_req_rtu2tcp(req_rtu_as_list, new_id):
    """:param    """
    req_tcp_as_list = req_rtu_as_list[:-2]  # cut CRC
    req_tcp_as_list[0] = new_id             # change id
    _req = struct.pack(req_frm_tcp, 10, 0, 0, 6, *req_tcp_as_list)
    return _req


def change_req_tcp2rtu(req_as_str, old_id):
    req_as_str = req_as_str[10:]   # cut tcp header=9 plus 1 to id
    req_as_str = struct.pack(">b", old_id) + req_as_str
    req_as_str = addCRC(req_as_str) # byte array
    return str(req_as_str)


if __name__ == '__main__':
    r = change_req_tcp2rtu("\x01\x02\x03"+'\n\x00\x00\x00\x00\x06\x11\x03\xa0\x00\x00d', 7)
    print r
    exit()

    for _ in range(100):
        if ser.is_open:
            print "waiting for input request"
            req_raw = ser.read(size=8)
            if checkCRC(req_raw):
                print "Error in CRC"
                ser.write(ErrorResp.crc_fail)
                continue
            req_list = struct.unpack(req_frm_rtu, req_raw)
            req_list = list(req_list)
            req_id = req_list[0]

            if req_id not in allowed_id:
                print "ID is not allowed"
                ser.write(ErrorResp.no_id)
                continue

            rtu_id, tcp_id, addr, port = vlook_up(value=req_id, matrix=settings, col=0)

            req_tcp = change_req_rtu2tcp(req_rtu_as_list=req_list, new_id=tcp_id)

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
            res_rtu = change_req_tcp2rtu(req_as_str=res_tcp, old_id=rtu_id)
            ser.write(res_rtu)
            print "data sended OK!"

        else:
            ser.close()
            ser.open()

