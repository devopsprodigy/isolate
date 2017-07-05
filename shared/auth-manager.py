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
from IsolateCore import IsolateGeoIP, is_valid_ipv6_address, is_valid_ipv4_address, is_valid_fqdn


LOGGER = logging.getLogger('auth-manager')
LOG_FORMAT = '[%(levelname)6s] %(name)s %(message)s'



class AuthManager(object):

    OFFSET_SERVER_ID = 10000

    def __init__(self, params):
        self.params = params
        self.action = self.params['action'][0]
        self.redis = Redis(host=os.getenv('ISOLATE_REDIS_HOST', '127.0.0.1'),
                           port=int(os.getenv('ISOLATE_REDIS_PORT', 6379)),
                           password=os.getenv('ISOLATE_REDIS_PASS', None),
                           db=int(os.getenv('ISOLATE_REDIS_DB', 0)))
        self.validate_params()
        self.geoip = IsolateGeoIP()

    def process_args(self):
        if self.action == 'add-host':
            self.add_host()
        elif self.action == 'del-host':
            self.del_host()
        elif self.action == 'dump-host':
            self.dump_host()
        elif self.action == 'add-project-config':
            self.add_project_config()
        elif self.action == 'del-project-config':
            self.del_project_config()
        elif self.action == 'dump-project-config':
            self.dump_project_config()
        else:
            LOGGER.critical('action "{0}" not found'.format(self.action))

    def validate_params(self):
        self.params['updated_by'] = os.getenv('USER', 'NO_USER_ENV')
        self.params['updated_at'] = int(time())

        if self.params['server_id'] is not None:
            self.params['server_id'] = self.params['server_id'][0]

        # if self.params['action'] is not None:
        #     if re.match('^[A-Za-z,\d\-]*$', self.params['action']) is None:
        #         LOGGER.critical('[action] Validation not passed')
        #         sys.exit(1)

        self.params['project_name'] = self.params['project'][0]
        if self.params['project_name'] is not None:
            if re.match('^[A-Za-z,\d\-]*$', self.params['project_name']) is None and len(self.params['project_name']) < 48:
                LOGGER.critical('[project_name] Validation not passed')
                sys.exit(1)
            self.params['project_name'] = self.params['project_name'].lower()

        self.params['server_name'] = self.params['server_name'][0]

        if self.params['server_name'] is not None:
            if not is_valid_fqdn(self.params['server_name']):
                LOGGER.critical('[server_name] Validation not passed')
                sys.exit(1)
            self.params['server_name'] = self.params['server_name'].lower()

        # SSH Options
        self.params['server_ip'] = self.params['ip'][0]
        if self.params['server_ip']:
            if not is_valid_ipv4_address(self.params['server_ip']) \
                    and not is_valid_ipv6_address(self.params['server_ip']):
                LOGGER.critical('[server_ip] Validation not passed')
                sys.exit(1)

        self.params['server_port'] = self.params['port'][0]
        if self.params['server_port'] is not None:
            if self.params['server_port'] > 65535 or self.params['server_port'] <= 0:
                LOGGER.critical('[port] Validation not passed')
                sys.exit(1)

        self.params['server_user'] = self.params['user'][0]
        if self.params['server_user'] is not None:
            if re.match('^[A-Za-z,\d\-]*$', self.params['server_user']) is None and len(self.params['server_user']) < 48:
                LOGGER.critical('[user] Validation not passed')
                sys.exit(1)

        self.params['proxy_id'] = self.params['proxy_id'][0]
        if self.params['proxy_id'] is not None:
            if self.redis.get('server_' + str(self.params['proxy_id'])) is None:
                LOGGER.critical('proxy with id {} not found!'.format(self.params['proxy_id']))
                sys.exit(1)
        self.params['server_nosudo'] = self.params['nosudo']

        # Meta clean up
        del self.params['action']
        del self.params['project']
        del self.params['ip']
        del self.params['port']
        del self.params['user']
        del self.params['nosudo']
        del self.params['debug']

    def add_host(self):
        # Put params
        if self.redis.get('offset_server_id') is None:
            self.redis.set('offset_server_id', self.OFFSET_SERVER_ID)

        self.params['server_id'] = self.redis.incr('offset_server_id')
        self.params['geoip_asn'] = self.geoip.asn.name_by_addr(self.params['server_ip'])

        redis_key = 'server_' + str(self.params['server_id'])
        self.redis.set(redis_key, json.dumps(self.params))
        LOGGER.info('Database updated: {0}'.format(self.params['server_id']))

    def del_host(self):
        if self.params['server_id'] is None:
            LOGGER.critical('--server-id missing')
        else:
            redis_key = 'server_{0}'.format(self.params['server_id'])
            self.redis.delete(redis_key)
            LOGGER.warn(redis_key + ' deleted')

    def dump_host(self):
        if self.params['server_id'] is not None:
            key = 'server_{0}'.format(self.params['server_id'])
            host = self.redis.get(key)
            print(json.dumps(json.loads(host), indent=4))
        else:
            LOGGER.critical('--server-id not passed')

    def add_project_config(self):
        # add default project wide ssh config
        redis_key = 'ssh_config_{0}'.format(self.params['project_name'])
        if self.redis.get(redis_key) is not None:
            LOGGER.critical('"{}" already exist'.format(redis_key))
            sys.exit(1)
        else:
            self.redis.set(redis_key, json.dumps(self.params))
            LOGGER.info('Config for {0} added'.format(self.params['project_name']))

    def del_project_config(self):
        if self.params['project_name'] is None:
            LOGGER.critical('--project missing')
        else:
            redis_key = 'ssh_config_{0}'.format(self.params['project_name'])
            self.redis.delete(redis_key)
            LOGGER.warn(redis_key + ' deleted')

    def dump_project_config(self):
        if self.params['project_name'] is not None:
            redis_key = 'ssh_config_{0}'.format(self.params['project_name'])
            host = self.redis.get(redis_key)
            print(json.dumps(json.loads(host), indent=4))
        else:
            LOGGER.critical('--project not passed')


def main():
    arg_parser = argparse.ArgumentParser(prog='auth-manager', epilog='------',
                                         description='Auth management shell helper')
    arg_parser.add_argument('action', type=str, nargs=1, default=[None])
    arg_parser.add_argument('--project', type=str, nargs=1,
                            default=[os.getenv('ISOLATE_DEFAULT_PROJECT', 'main')])
    arg_parser.add_argument('--server-name', type=str, nargs=1, default=[None])
    arg_parser.add_argument('--ip', '--server-ip', type=str, nargs=1, default=[None])

    arg_parser.add_argument('--port', '--server-port', type=int, nargs=1, default=[None])
    arg_parser.add_argument('--user', type=str, nargs=1, default=[None])
    arg_parser.add_argument('--nosudo', action='store_true', default=None)

    arg_parser.add_argument('--proxy-id', type=int, nargs=1,
                            default=[None], help="server_id of proxy")
    arg_parser.add_argument('--server-id', type=int, nargs=1, default=[None],
                            help="server_id (for del-host)")

    arg_parser.add_argument('--debug', action='store_true')
    args = arg_parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    am = AuthManager(args.__dict__)
    am.process_args()


if __name__ == '__main__':
    main()
