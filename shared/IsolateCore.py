#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import socket
import re
import GeoIP

sys.dont_write_bytecode = True

# Common snippets and funcs for use in other scripts (tiny lib)

__version__ = '0.2.0'


def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return True
    except socket.error:
        return False

    return True


def is_valid_ipv6_address(address):
    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:
        return False
    return True


def is_valid_fqdn(hostname):
    hostname = str(hostname).lower()
    if len(hostname) > 255:
        return False
    if hostname[-1] == '.' or hostname[0] == '.':
        return False
    if re.match('^([a-z\d\-.]*)$', hostname) is None:
        return False
    return True


class IsolateGeoIP(object):

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.ASN_DB = os.getenv('ISOLATE_GEOIP_ASN', '/opt/auth/shared/geoip/GeoIPASNum.dat')
        self.asn = GeoIP.open(self.ASN_DB, GeoIP.GEOIP_STANDARD)


class AuthStorage(object):
    pass


class AuthCore(object):
    pass