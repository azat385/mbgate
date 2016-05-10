# -*- coding: utf-8 -*-

import socket
import struct
from datetime import datetime
from time import sleep
hexString = lambda byteString: " ".join(x.encode('hex') for x in byteString)

from transliterate import translit, get_available_language_codes

alive_sec = 300

int16 = 'h'
int32 = 'i'
float32 = 'f'
flt32 = 'f'
bool0 = '?'
doNotSave = 0
onChange = 1            #saveAttr:(delta, 3min)
percentChange = 2       #3%
onSpecialChange = 3     #otherTagID=value

from spiderSettings import pixel_std_map, form_std_settings, aktanishSettings
first10 = aktanishSettings[0]

#left just for example
req_str = struct.pack(">bbHHbbHH", 10, 0, 0, 6, 17, 3, 40960, 100 )
#print hexString(req_str)

def create_std_settings(address=1):
    mtcp_settings = [form_std_settings(pixel_std_map[0], modbus_set=(address, 3, 40960), prepend_name=""),
                       form_std_settings(pixel_std_map[1], modbus_set=(address, 3, 41065), prepend_name="")]
    #rtu to tcp header -crc16
    for mtcp in mtcp_settings:
        mtcp['settings']['request'] = struct.pack(">bbHH", 10, 0, 0, 6)+ mtcp['settings']['request'][:-2]
        print hexString(mtcp['settings']['request'])
    return mtcp_settings

mtcp_settings17 = create_std_settings(address=17)
mtcp_settings11 = create_std_settings(address=11)

first10['settings']['request'] = struct.pack(">bbHH", 10, 0, 0, 6)+ first10['settings']['request'][:-2]
print hexString(first10['settings']['request'])
print first10


def rearrangeData(_data,_unpackStr):
    import struct
    if len(_data) == struct.calcsize(_unpackStr):
        iBegin = 0
        iEnd = 0
        dataNew = ''
        for s in _unpackStr:
            iEnd = iBegin + struct.calcsize(s)
            if s in 'fiIlL':
                addData = _data[iBegin:iEnd][2:] + _data[iBegin:iEnd][:2]
            else:
                addData = _data[iBegin:iEnd]
            dataNew += addData
            iBegin = iEnd
        return dataNew


def printTuple(mc, dataT, valT, strT, prependStr='', key_str_separater='.', val_str_separater=';'):
    #import memcache
    #mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    #mc.flush_all()


    onlineStr = "online"
    lastSavedStr = "lastSaved"
    archiveStr = "archive"

    def form_key_str(base_str, adding_str):
        return "{}_{}".format(adding_str, base_str)


    minIndex = min([len(dataT), len(valT)])
    i = 0
    for i in xrange(minIndex):
        value = valT[i]
        #online values
        formKeyStr = "{}{}{}".format(prependStr, key_str_separater, dataT[i]['name'])
        formKeyStr = formKeyStr.replace(" ", "_")   #no blanks in key

	formKeyStr = translit(formKeyStr.decode("utf-8"), 'ru', reversed=True)
	#formKeyStr = formKeyStr.decode("utf-8")

        formValStr = "{}{}{}".format(value,val_str_separater, strT)
        print "{}={}".format(formKeyStr, formValStr)
        mc.set(form_key_str(formKeyStr,onlineStr), formValStr, alive_sec)
        #last saved values and append archiving
        if dataT[i]['saveTrigger']==onChange:
            #get last saved value
            keyLastSaved = form_key_str(formKeyStr,lastSavedStr)
            #print "key: {}".format(keyLastSaved)
            lastSavedValue = mc.get(keyLastSaved)
            #print "value: {}".format(lastSavedValue)
            if lastSavedValue is None:
                mc.set(keyLastSaved,formValStr)
                #print "Set {}={}".format(keyLastSaved,formValStr)
                continue
            else:
                vT = tuple(lastSavedValue.split(";"))
                lastSaved_value,lastSaved_time = vT[:2]
                lastSaved_value = float(lastSaved_value)
                if not dataT[i].has_key('saveAttr'):
                    continue
                delta_value, delta_time = dataT[i]['saveAttr']
                if (abs(lastSaved_value-value)>delta_value) or \
                        (check_time_passed(t1=lastSaved_time, t2=strT, deltaSec=delta_time*60)):
                    mc.set(keyLastSaved,formValStr)
                    appendKey = form_key_str(formKeyStr,archiveStr)
                    if mc.append(appendKey,';;;'+formValStr) is False:
                        mc.set(appendKey,formValStr)


def check_time_passed(t1,t2,deltaSec=180):
    t1 = datetime.strptime(t1,"%Y-%m-%d %H:%M:%S.%f")
    t2 = datetime.strptime(t2,"%Y-%m-%d %H:%M:%S.%f")
    dif = t2-t1
    dif_sec = abs(dif.total_seconds())
    return dif_sec >= deltaSec
    #print "dif time= {} delta= {}".format(dif_sec,deltaSec)


def infinite_loop(addr, port, settings, prepend, delay_sec=1.0):
    #from ttcpServer import rearrangeData, printTuple
    #unique for each process
    import memcache
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    for _ in range(10):
            pass
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.connect((addr, port))

            data = []
            strTimeStamp_t = []
            for mtcp in settings:
                sock.send(mtcp['settings']['request'])
                data.append(sock.recv(1024))
                strTimeStamp_t.append(str(datetime.now()))

            val_t = []
            for d, mtcp in zip(data, settings):
                #print hexString(d)
                d1 = rearrangeData(d[9:], mtcp['settings']['unpackStr'])
                val = struct.unpack(mtcp['settings']['unpackStr'], d1)
                name_t = [i['name'] for i in mtcp['data'] ]
                #print " ".join("{}={}\n".format(n,v) for n,v in zip(name_t, val))
                val_t.append(val)

                sock.close()
                #send_data to mc
                for v, mtcp, t in zip(val_t, settings, strTimeStamp_t):
                   printTuple(mc, mtcp['data'] ,v, t, prependStr=prepend)
        #except:
        #    print "Exiting"
        #    sock.close()
        #    #exit()
        #finally:
            sleep(delay_sec)
            sock.close()


def infinite_loop_star(a_b):
    """Convert `f([1,2])` to `f(1,2)` call."""
    return infinite_loop(*a_b)



if __name__ == '__main__':

    first10 = [first10,]
    #infinite_loop("192.168.0.117", 502, mtcp_settings17, "pixel_17", 2)
    #exit()

    from multiprocessing import Pool, freeze_support

    common_settings = [
        ("192.168.0.117", 502, mtcp_settings17, "pixel_17", 1),
        ("192.168.0.111", 502, mtcp_settings11, "pixel_11", 1),
        ("192.168.0.69", 502, first10, "mb_slave64", 0.5),
        ("192.168.0.69", 502, first10, "mb_slave32", 1),
        ("192.168.0.69", 502, first10, "mb_slave16", 2),
    ]

    freeze_support()
    pool = Pool(processes=3)
    pool.map(infinite_loop_star, iter(common_settings))
    pool.close()
    pool.join()

