#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import re
import json
from time import time
import argparse
from redis import Redis
import logging
import socket

LOGGER = logging.getLogger('ssh-wrapper')
LOG_FORMAT = '[%(asctime)s] [%(levelname)6s] %(name)s %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

USER = os.getenv('USER', 'NO_USER_ENV')

params = None


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


def main():
    arg_parser = argparse.ArgumentParser(prog='auth-manager', epilog='------',
                                         description='Auth shell helper')

    arg_parser.add_argument('action', type=str, nargs=1)
    arg_parser.add_argument('--project', type=str, nargs=1,
                            default=[os.getenv('ISOLATE_DEFAULT_PROJECT', 'default')])
    arg_parser.add_argument('--server-name', type=str, nargs=1)
    arg_parser.add_argument('--ip', type=str, nargs=1)
    arg_parser.add_argument('--port', type=int, nargs=1, default=[None])
    arg_parser.add_argument('--user', type=str, nargs=1, default=[None])
    arg_parser.add_argument('--nosudo', action='store_true')
    arg_parser.add_argument('--proxy-id', type=int, nargs=1,
                            default=[None], help="server_id of proxy")
    arg_parser.add_argument('--server-id', type=int, nargs=1, default=[None],
                            help="server_id (for del-host)")

    arg_parser.add_argument('--debug', action='store_true')

    args = arg_parser.parse_args()
    params = args.__dict__

    redis = Redis(host=os.getenv('ISOLATE_REDIS_HOST'),
                  port=int(os.getenv('ISOLATE_REDIS_PORT', 6379)),
                  password=os.getenv('ISOLATE_REDIS_PASS'),
                  db=int(os.getenv('ISOLATE_REDIS_DB', 0)))

    # Management info
    action = params['action'][0]

    if action == 'add-host':

        # Validate Args/Params
        params['action'] = params['action'][0]
        if params['action'] is not None:
            if re.match('^[A-Za-z,\d\-]*$', params['action']) is None and len(params['action']) < 48:
                LOGGER.critical('[action] Validation not passed')
                sys.exit(1)

        params['project_name'] = params['project'][0]
        if params['project_name'] is not None:
            if re.match('^[A-Za-z,\d\-]*$', params['project_name']) is None and len(params['project_name']) < 48:
                LOGGER.critical('[project_name] Validation not passed')
                sys.exit(1)

        params['server_name'] = params['server_name'][0]
        if not is_valid_fqdn(params['server_name']):
            LOGGER.critical('[server_name] Validation not passed')
            sys.exit(1)

        # SSH Options
        params['server_ip'] = params['ip'][0]

        if not is_valid_ipv4_address(params['server_ip']) \
                and not is_valid_ipv6_address(params['server_ip']):
            LOGGER.critical('[server_ip] Validation not passed')
            sys.exit(1)

        params['server_port'] = params['port'][0]
        if params['server_port'] is not None:
            if params['server_port'] > 65535 or params['server_port'] <= 0:
                LOGGER.critical('[port] Validation not passed')
                sys.exit(1)

        params['server_user'] = params['user'][0]
        if params['server_user'] is not None:
            if re.match('^[A-Za-z,\d\-]*$', params['server_user']) is None and len(params['server_user']) < 48:
                LOGGER.critical('[user] Validation not passed')
                sys.exit(1)

        params['server_nosudo'] = params['nosudo']
        params['proxy_id'] = params['proxy_id'][0]

        # Meta
        params['updated_by'] = USER
        params['updated_at'] = int(time())

        del params['action']
        del params['project']
        del params['ip']
        del params['port']
        del params['user']
        del params['nosudo']
        del params['debug']

        # Put params
        if redis.get('offset_server_id') is None:
            redis.set('offset_server_id', 100000)

        params['server_id'] = redis.incr('offset_server_id')
        redis_key = 'server_' + str(params['server_id'])
        redis.set(redis_key, json.dumps(params))
        print('Database updated')

    elif action == 'del-host':

        key = 'server_{0}'.format(params['server_id'][0])
        redis.delete(key)
        print(key + ' deleted')

if __name__ == '__main__':
    main()
