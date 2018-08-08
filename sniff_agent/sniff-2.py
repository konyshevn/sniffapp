import pcap
import dpkt
import datetime
import socket
import sqlite3
import netifaces
import sys
import os
import shutil
import requests

script_name = os.path.basename(__file__)
script_abspath = os.path.abspath(__file__)
script_dir = (script_abspath[:script_abspath.rfind(script_name)])


def inet_to_str(inet):
    # First try ipv4 and then ipv6
    try:
        return socket.inet_ntop(socket.AF_INET, inet)
    except ValueError:
        return socket.inet_ntop(socket.AF_INET6, inet)


def exec_query(connection, connection_cursor, sql_query, sql_query_arg='', many=False):
    try:
        if many:
            connection_cursor.executemany(sql_query, sql_query_arg)
        else:
            connection_cursor.execute(sql_query, sql_query_arg)
    except sqlite3.DatabaseError as err:
        print("Error: ", err)
    else:
        connection.commit()
        return connection_cursor.fetchall()


create_table_packets = "CREATE TABLE IF NOT EXISTS packets (datetime datetime, src char(50), dst char(50), pkt_size integer)"
create_table_transfer = "CREATE TABLE IF NOT EXISTS transfer (pc_name char(50), mac_addr char(17), date_db datetime, uid char(20))"
insert_values_packets = "INSERT INTO packets values (?, ?, ?, ?)"
insert_values_transfer = "INSERT INTO transfer values (?, ?, ?, ?)"
delete_packets = "DELETE FROM packets"
delete_transfer = "DELETE FROM transfer"

config_ini = open(script_dir + 'config.ini', 'r')

ini_params = {}
intf = None
ts_range = 600
db_path = script_dir + '_sniff.db'
uid = 0
transfer_size = 5120
server_URL = 'http://myhost.com'

for line in config_ini:
    params = line.strip().split('=')
    if len(params) != 2:
        continue
    if params[1] == '':
        continue
    ini_params.update([(params[0], params[1])])

if 'intf' in ini_params:
    intf = ini_params['intf']
if 'ts_range' in ini_params:
    ts_range = float(ini_params['ts_range'])
if 'db_path' in ini_params:
    db_path = ini_params['db_path']
if 'uid' in ini_params:
    uid = ini_params['uid']
if 'transfer_size' in ini_params:
    transfer_size = int(ini_params['transfer_size'])
if 'server_URL' in ini_params:
    server_URL = ini_params['server_URL']

#Listening Flags
if intf is not None:
    for dev in netifaces.interfaces():
        dev_inet = netifaces.ifaddresses(dev).get(netifaces.AF_INET)
        if dev_inet and intf == dev_inet[0]['addr']:
            dev_selected = '\\\\Device\\\\NPF_' + dev
            break
else:
    dev_selected = None

#Connecting DB
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

#Start Listening
print('\n')
print('Start listenig with parameters:')
print('Interface:    ', dev_selected, ' (None means first active)')
print('Interface IP: ', intf, ' (None means first active)')
print('TS_range:     ', ts_range)
print('DB_path:      ', db_path)
print('Uid:          ', uid)
print('transfer_size:', transfer_size)

exec_query(conn, cursor, create_table_packets)
exec_query(conn, cursor, create_table_transfer)

packets_stat = []
ts_start = datetime.datetime.timestamp(datetime.datetime.now())

sniffer = pcap.pcap(name=dev_selected, promisc=True, immediate=True, timeout_ms=50)
iface = sniffer.name
if sys.platform == 'win32':
    iface = iface[iface.find('{'):iface.rfind('}') + 1]
mac_addr = netifaces.ifaddresses(iface)[netifaces.AF_LINK][0]['addr']

for ts, buf in sniffer:
    ts2date = str(datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"))
    eth = dpkt.ethernet.Ethernet(buf)
    if type(eth.data) == dpkt.ip.IP:
        ip = eth.data
        ip_src = inet_to_str(ip.src)
        ip_dst = inet_to_str(ip.dst)
        ip_len = ip.len
        if (ts - ts_start) < ts_range:
            for packets_stat_rec in packets_stat:
                if packets_stat_rec[0] == ip_src and packets_stat_rec[1] == ip_dst:
                    packets_stat_rec[2] += ip_len
                    break
            else:
                packets_stat.append([ip_src, ip_dst, ip_len])
        else:
            print(ts2date, packets_stat)
            packets_stat_tuple = [(ts2date, x[0], x[1], x[2]) for x in packets_stat]
            packets_stat = []
            ts_start = ts
            exec_query(conn, cursor, insert_values_packets, sql_query_arg=packets_stat_tuple, many=True)
            conn.commit()

            if os.path.getsize(db_path) / 1024 > transfer_size:
                pc_name = socket.gethostname()
                date_db = str(datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"))
                cur_date = date_db.replace(':', '-')
                exec_query(conn, cursor, insert_values_transfer, sql_query_arg=[(pc_name, mac_addr, date_db, uid)], many=True)
                conn.commit()

                db_transfer_path = pc_name + '(' + uid + ')' + ' - ' + cur_date + '.db'
                fc = shutil.copyfile(db_path, db_transfer_path)
                print('Transfer: ' + fc)
                client = requests.Session()
                client.get(server_URL)
                csrftoken = client.cookies['csrftoken']
                with open(db_transfer_path, 'rb') as f:
                    payload = {'csrfmiddlewaretoken': csrftoken}
                    files = {'file': f}
                    req = client.post(server_URL, data=payload, files=files)
                    if req.ok:
                        exec_query(conn, cursor, delete_transfer)
                        exec_query(conn, cursor, delete_packets)
                        exec_query(conn, cursor, "VACUUM")
                        conn.commit()
                        print('OK')
                    f.close()
                    os.remove(db_transfer_path)
conn.close()
