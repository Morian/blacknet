#!/usr/bin/env python
# -*- coding: utf-8 -*-

from threading import Thread, Lock
from signal import signal, SIGINT, SIGTERM
from time import sleep

import json
import logging
import os
import paramiko
import socket
import sys

from blacknet.sensor import BlacknetSensor
from blacknet.master import BlacknetMasterServer
from blacknet.updater import BlacknetGeoUpdater
from blacknet.scrubber import BlacknetScrubber


SCRUBBER_STATS_FILE='tests/generated/stats_general.json'
HONEYPOT_CONFIG_FILE='tests/blacknet-honeypot.cfg'
MASTER_CONFIG_FILE='tests/blacknet.cfg'
CLIENT_SSH_KEY='tests/ssh_key'


# Log paramiko stuff to stdout.
l = logging.getLogger("paramiko")
l.setLevel(logging.WARNING)

c = logging.StreamHandler(sys.stdout)
l.addHandler(c)


def runtests_ssh_serve(bns):
    bns.do_ping()
    bns.serve()


def runtests_main_serve(bns):
    bns.serve()


def runtests_ssh_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 2200))

    t = paramiko.Transport(sock)
    t.start_client()

    try:
        ssh_key = paramiko.RSAKey(filename=CLIENT_SSH_KEY)
        t.auth_publickey('blacknet', ssh_key)
    except:
        pass

    for suffix in ['0', '1', 'a', 'b', 'c', 'é', '&', 'L', ')', '€', '\xfe', '\xa8']:
        try:
            password = 'password_%s' % suffix
            t.auth_password('blacknet', password)
        except Exception as e:
            pass
    t.close()


def runtests_update():
    bnu = BlacknetGeoUpdater(MASTER_CONFIG_FILE)
    bnu.update()


def runtests_scrubber():
    bns = BlacknetScrubber(MASTER_CONFIG_FILE)
    bns.verbosity = 2
    bns.do_fix = True

    bns.check_attackers()
    for table in ['attacker', 'session']:
        bns.check_attempts_count(table)
        bns.check_attempts_dates(table)
    bns.check_geolocations()
    bns.database_optimize()
    bns.generate_targets()
    bns.generate_stats()
    bns.generate_minimaps()
    bns.generate_map_data()


def runtests_checker():
    with open(SCRUBBER_STATS_FILE, 'r') as f:
        d = json.load(f)
        d = d['data'][0]
        print(d)

        return d[0] > 10


def runtests_ssh():
    """ This test launches both servers and run a few login/passwd attempts """
    servers = []
    threads = []

    # Create master server instance
    print("[+] Creating main server instance")
    bn_main = BlacknetMasterServer(MASTER_CONFIG_FILE)
    servers.append(bn_main)

    # Create SSH sensor instance
    print("[+] Creating SSH server instance")
    bn_ssh = BlacknetSensor(cfg_file=HONEYPOT_CONFIG_FILE)
    servers.append(bn_ssh)

    # Check configuration reloading
    for s in servers:
        s.reload()

    # Prepare to serve requests in separate threads
    t = Thread(target = runtests_main_serve, args = (bn_main,))
    threads.append(t)

    t = Thread(target = runtests_ssh_serve, args = (bn_ssh,))
    threads.append(t)

    for t in threads:
        t.daemon = True
        t.start()

    print("[+] Running SSH login attempts")

    # Simulate a SSH client connecting
    runtests_ssh_client()

    # Close servers
    bn_ssh.shutdown()
    bn_main.shutdown()
    print("[+] Closed servers")


if __name__ == '__main__':
    # Update geolocation database with minimal sample
    runtests_update()

    # Main SSH Test
    runtests_ssh()

    # DB scrubber and cache generator
    runtests_scrubber()

    # Check number of attempts from database
    success = runtests_checker()
    if success:
        sys.exit(os.EX_OK)
    sys.exit(os.EX_SOFTWARE)
