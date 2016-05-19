# -*- coding: utf-8 -*-

import serial
import socket
import struct
from datetime import datetime
hexString = lambda byteString: " ".join(x.encode('hex') for x in byteString)
import yaml

with open("serial2tcpMB.yaml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

for section in cfg:
    print(section)
serial_settings = cfg['serial']
print serial_settings
s = cfg['rtu2tcp']
print s['settings']
settings = s['settings']


#bad but working
import sys
try:
    sys.path.insert(0, 'd:\\Azat\\PycharmProjects\\first')
    from crc16 import checkCRC, addCRC
    #from ttcpServer import simpleCheck
except:
    print "Smth is wrong in import"

ser = serial.Serial()
# set up serial settings
ser.baudrate = serial_settings["baudrate"] if "baudrate" in serial_settings else 115200
ser.port = serial_settings["port"] if "port" in serial_settings else 'COM5'
ser.bytesize = serial_settings["bytesize"] if "bytesize" in serial_settings else 8
ser.parity = serial_settings["parity"] if "parity" in serial_settings else'N'
ser.stopbits = serial_settings["stopbits"] if "stopbits" in serial_settings else 1
ser.xonxoff = serial_settings["xonxoff"] if "xonxoff" in serial_settings else 0
ser.rtscts = serial_settings["rtscts"] if "rtscts" in serial_settings else 0
if "timeout" in serial_settings:
    if serial_settings["timeout"]=="None":
        ser.timeout = None
    else:
        ser.timeout = serial_settings["timeout"]
else:
    ser.timeout = None
print "Serial settings:", ser

"""
#[addr of rtu slave, addr of tcp slave, ip, port]
settings = [
    [7, 17, "192.168.0.117", 502],
    [1, 11, "192.168.0.111", 502],
    [14, 4, "192.168.0.69", 502],
]
"""

def vlook_up(value, matrix, col):
    for m in matrix:
        if m[col] is value:
            return m
    return None

def column(matrix, i):
    return [row[i] for row in matrix]

allowed_id = column(settings,0)


def res_error_str(msg, _id):
    res = struct.pack(">BBB", _id, *msg)
    res = addCRC(res)
    res = str(res)
    print "Error code:", hexString(res)
    return res

class ErrorResp():
    """errors here!!!"""

    def __init__(self):
        pass

    crc_fail = "\x51\x99"
    no_id = (129, 1)

    cant_open_tcp_port = "\x51\x12"
    tcp_timeout_reached = "\x81\x13"


req_frm_rtu = ">BBHHBB"     # 17, 3, 40960, 100, crc1, crc2
req_frm_tcp = ">BBHHBBHH"   # 10, 0, 0, 6, 17, 3, 40960, 100

def change_req_rtu2tcp(req_rtu_as_list, new_id):
    """:param    """
    req_tcp_as_list = req_rtu_as_list[:-2]  # cut CRC
    req_tcp_as_list[0] = new_id             # change id
    _req = struct.pack(req_frm_tcp, 10, 0, 0, 6, *req_tcp_as_list)
    return _req


def change_req_tcp2rtu(req_as_str, old_id):
    req_as_str = req_as_str[7:]   # cut tcp header=9 plus 1 to id
    req_as_str = struct.pack(">B", old_id) + req_as_str
    req_as_str = addCRC(req_as_str) # byte array
    return str(req_as_str)


if __name__ == '__main__':
    #exit()

    #for _ in range(100):
    while 1:
        if ser.is_open:
            print "waiting for input request"
            req_raw = ser.read(size=8)
            print "get rtu:", hexString(req_raw)
            if checkCRC(req_raw):
                print "Error in CRC"
                ser.write(ErrorResp.crc_fail)
                continue
            req_list = struct.unpack(req_frm_rtu, req_raw)
            req_list = list(req_list)
            req_id = req_list[0]

            if req_id not in allowed_id:
                print "ID is not allowed"
                ser.write(res_error_str(ErrorResp.no_id, req_id))
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
            print "send tcp:", hexString(req_tcp), "to", addr, port
            sock.send(req_tcp)
            res_tcp = sock.recv(1024)
            print "get tcp:", hexString(res_tcp), "from", addr, port
            if res_tcp is None:
                print "Timeout reached"
                sock.close()
                ser.write(ErrorResp.tcp_timeout_reached)
                continue
            sock.close()
            res_rtu = change_req_tcp2rtu(req_as_str=res_tcp, old_id=rtu_id)
            print "send rtu:", hexString(res_rtu)
            ser.write(res_rtu)
            print "data sended OK!"

        else:
            ser.close()
            ser.open()

