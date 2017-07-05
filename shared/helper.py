#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import time
import argparse
import json
import sys
import os
import logging
import operator
from copy import copy
from uuid import uuid4
import socket
import re
from redis import Redis
from operator import itemgetter
from pyzabbix import ZabbixAPI
# from IsolateCore import __version__


LOG_FORMAT = '[%(levelname)s] %(name)s %(message)s'


LOGGER = logging.getLogger('helper')
pyzabbix_LOGGER = logging.getLogger('pyzabbix')
pyzabbix_LOGGER.setLevel(logging.WARN)
pyzabbix_requests_LOGGER = logging.getLogger('requests.packages.urllib3.connectionpool')
pyzabbix_requests_LOGGER.setLevel(logging.WARN)


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        if dictionary is None:
            continue
        else:
            for key in dictionary.keys():
                if dictionary[key] is None:
                    del dictionary[key]
        result.update(dictionary)
    return result


def str2bool(s):
    yes_bools = ['true', 'yes', 'da', 'aga', 'ok', 'yep', 'да', 'ага', 'kk', 'y', 'конечно', 'да, товарищ']

    if str(s).lower() in yes_bools:
        return True
    else:
        return False


def init_args():

    arg_parser = argparse.ArgumentParser(prog='helper', epilog='------',
                                         description='Auth shell helper')
    arg_parser.add_argument('action', type=str, nargs=1, choices=['search', 'go', 'cron'])
    arg_parser.add_argument('sargs', type=str, nargs='+',
                            help='[search server_id | go project | go project server_name]')
    arg_parser.add_argument('--helper-debug', action='store_true')
    arg_parser.add_argument_group('Search', 's <query> [opts]')
    arg_parser.add_argument_group('Go', 'g <project|host> [server_name|server_ip] [opts]')

    # Unknown args bypassed to ssh.py wrapper
    args, unknown_args = arg_parser.parse_known_args()

    if args.helper_debug or '--debug' in sys.argv:
        args.helper_debug = True

        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                            format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
        LOGGER.info('Helper debug mode on')
        LOGGER.info(sys.argv)
        LOGGER.info(vars(args))
        LOGGER.info(unknown_args)

    else:
        logging.basicConfig(stream=sys.stderr, level=logging.WARN, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    return args, unknown_args


class IsolateZabbixHosts(object):
    def __init__(self):
        self.hosts_dump = list()
        self.hosts_dict = dict()
        self.projects = list()
        self.zapi = ZabbixAPI(os.getenv('ISOLATE_ZABBIX_URL'))
        self.zapi.login(os.getenv('ISOLATE_ZABBIX_USER'), os.getenv('ISOLATE_ZABBIX_PASS'))

    def get_hosts(self):
        for h in self.zapi.hostinterface.get(output="extend", selectHosts=["host"], filter={"main": 1, "type": 1}):
            host = dict(
                server_name=h['hosts'][0]['host'],
                server_id=h['hosts'][0]['hostid'],
                server_ip=h['ip']
            )
            self.hosts_dict[str(host['server_id'])] = host

        for g in self.zapi.hostgroup.get(output="extend", selectHosts=["host"], filter={"main": 1, "type": 1}):
            project_name = g['name']
            self.projects.append(project_name)
            for h in g['hosts']:
                server_id = h['hostid']
                host = self.hosts_dict[server_id]
                host['project_name'] = project_name
                self.hosts_dump.append(self.hosts_dict[server_id])
        return self.hosts_dump

    def get_projects(self):
        return list(sorted(set(self.projects)))

    def put_projects_list(self):
        raise Exception('Not implemented')

    def put_hosts_per_project_list(self, key, value):
        pass


class IsolateRedisHosts(object):
    def __init__(self):
        self.projects = list()
        self.hosts_dump = list()
        self.redis = Redis(host=os.getenv('ISOLATE_REDIS_HOST', '127.0.0.1'),
                           port=int(os.getenv('ISOLATE_REDIS_PORT', 6379)),
                           password=os.getenv('ISOLATE_REDIS_PASS', None),
                           db=int(os.getenv('ISOLATE_REDIS_DB', 0)))

    def get_hosts(self):
        for server_key in self.redis.keys('server_*'):
            server_data = self.redis.get(server_key)
            server_data = json.loads(server_data)
            self.projects.append(server_data['project_name'])
            self.hosts_dump.append(server_data)
        return self.hosts_dump

    def get_projects(self):
        return list(sorted(set(self.projects)))

    def get_project_config(self, project):
        redis_key = 'ssh_config_{0}'.format(project)
        res = self.redis.get(redis_key)
        if res is not None:
            return json.loads(res)
        else:
            return None

    def get_server_config(self, server_id):
        redis_key = 'server_{0}'.format(server_id)
        LOGGER.debug('IsolateRedisHosts: get_server_config')
        LOGGER.debug(redis_key)
        res = self.redis.get(redis_key)
        if res is not None:
            return json.loads(res)
        else:
            return None

    def put_projects_list(self):
        self.redis.set('projects_list', ' '.join(self.projects))

    def put_hosts_per_project_list(self, key, value):
        self.redis.set(key, value)


class ServerConnection(object):
    #
    helper = None
    #
    arg_type = None
    search_results = []
    project_name = None
    server_name = None
    server_id = None
    #
    # host config
    #
    host = None
    port = None
    user = None
    nosudo = None
    proxy_id = None
    #
    proxy_host = None
    proxy_port = None
    proxy_user = None
    #
    session_exports = list()
    ISOLATE_SESSION = os.getenv('ISOLATE_SESSION', None)
    session_exports.append('ISOLATE_CALLBACK="{}";'.format(ISOLATE_SESSION))
    ssh_wrapper_cmd = os.getenv('ISOLATE_WRAPPER', 'sudo -u auth /opt/auth/wrappers/ssh.py')

    #
    def __init__(self, helper=None, unknown_args=None):
        self.helper = helper
        self.unknown_args = unknown_args

    #
    # perform connection structure checks
    #
    def _validate(self):
        if len(self.search_results) > 1:
            raise Exception('passed more that one host in search_results')
        elif len(self.search_results) == 0:
            LOGGER.debug('ServerConnection.resolve: No hosts in search_results passed')


    #
    # resolve host configuratin
    #
    def resolve(self):
        project_config = self._get_project_config()
        host_config = self._get_host_config()
        final_config = merge_dicts(project_config, host_config)

        self.host = final_config.get('server_ip', None)
        self.port = final_config.get('server_port', None)
        self.user = final_config.get('server_user', None)
        self.nosudo = final_config.get('server_nosudo', None)
        self.proxy_id = final_config.get('proxy_id', None)

        proxy_config = merge_dicts(self._get_proxy_config())  # drop null/None fields
        if proxy_config is not None:
            self.proxy_host = proxy_config.get('server_ip')
            self.proxy_port = proxy_config.get('server_port', None)
            self.proxy_user = proxy_config.get('server_user', None)

        # LOGGER.critical(json.dumps(project_config, indent=4))
        # LOGGER.critical(json.dumps(host_config, indent=4))
        # LOGGER.critical(json.dumps(proxy_config, indent=4))
        # LOGGER.debug(json.dumps(final_config, indent=4))


    #
    # project wide ssh_config [low]
    #
    def _get_project_config(self):
        project_config = self.helper.db.get_project_config(self.project_name)
        if project_config is None:
            LOGGER.debug('_get_project_config: Not found')
            return None
        LOGGER.debug('_get_project_config')
        LOGGER.debug(json.dumps(project_config, indent=4))
        return project_config

    #
    # host ssh_config [high]
    #
    def _get_host_config(self):
        if len(self.search_results) != 1:
            return

        host_config = self.search_results[0]
        LOGGER.debug('_get_host_config')
        LOGGER.debug(json.dumps(host_config, indent=4))
        return host_config

    #
    # proxy ssh_config
    #
    def _get_proxy_config(self):
        proxy_config = self.helper.db.get_server_config(self.proxy_id)
        if proxy_config is None:
            LOGGER.debug('_get_proxy_config: Not found "{}"'.format(self.proxy_id))
            return None
        LOGGER.debug('_get_proxy_config')
        LOGGER.debug(json.dumps(proxy_config, indent=4))
        return proxy_config

    #
    # build commands
    #
    def build_cmd(self):

        if self.host:
            self.ssh_wrapper_cmd += ' {}'.format(self.host)
        if self.port:
            self.ssh_wrapper_cmd += ' --port {}'.format(self.port)
        if self.user:
            self.ssh_wrapper_cmd += ' --user {}'.format(self.user)
        if self.nosudo:
            self.ssh_wrapper_cmd += ' --nosudo'

        if self.proxy_id:
            self.ssh_wrapper_cmd += ' --proxy-id {}'.format(self.proxy_id)
        if self.proxy_host:
            self.ssh_wrapper_cmd += ' --proxy-host {}'.format(self.proxy_host)
        if self.proxy_port:
            self.ssh_wrapper_cmd += ' --proxy-port {}'.format(self.proxy_port)
        if self.proxy_user:
            self.ssh_wrapper_cmd += ' --proxy-user {}'.format(self.proxy_user)

        if bool(self.unknown_args):
            self.ssh_wrapper_cmd += ' ' + ' '.join(self.unknown_args)

        self.session_exports.append('ISOLATE_CALLBACK_CMD="{}"'.format(self.ssh_wrapper_cmd))

    def _write_session(self):
        if self.ISOLATE_SESSION is None:
            return None

        with open(self.ISOLATE_SESSION, 'w') as sess_f:
            for line in self.session_exports:
                    sess_f.write(line + '\n')

    def start(self):
        self._validate()
        self.resolve()
        self.build_cmd()
        self._write_session()

        # debug
        self.__dict__.pop('helper', None)
        self.__dict__.pop('host_ssh_config', None)
        self.__dict__.pop('project_config', None)
        self.__dict__.pop('search_results', None)

        LOGGER.debug(self.__dict__)


class AuthHelper(object):

    def __init__(self, args, unknown_args):
        self.uuid = str(uuid4())
        self.time_start = time()
        self.args = args
        self.unknown_args = unknown_args
        self._init_env_vars()
        self.hosts_dump = []
        self.projects = []

        if self.ISOLATE_BACKEND == 'redis':
            self.db = IsolateRedisHosts()
        elif self.ISOLATE_BACKEND == 'zabbix':
            self.db = IsolateZabbixHosts()
        else:
            LOGGER.critical('Incorrect backend')
            sys.exit(1)

        self._load_data()
        LOGGER.debug('AuthHelper init done')

    @staticmethod
    def print_p(arg, stderr=False):
        try:
            if not stderr:
                sys.stdout.write(str(arg) + '\n')
                sys.stdout.flush()
            else:
                sys.stderr.write(str(arg) + '\n')
                sys.stderr.flush()
        except IOError:
            try:
                sys.stdout.close()
            except IOError:
                pass
            try:
                sys.stderr.close()
            except IOError:
                pass
                exit(0)

    @staticmethod
    def is_valid_ipv4(address):
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except socket.error:
                return False
            return True
        except socket.error:  # not a valid address
            return False

        return True

    @staticmethod
    def is_valid_ipv6(address):
        try:
            socket.inet_pton(socket.AF_INET6, address)
        except socket.error:  # not a valid address
            return False
        return True

    @staticmethod
    def is_valid_fqdn(hostname):
        # FQDN must be pretty, without dots at start/end
        # and have one minimum
        hostname = str(hostname).lower()
        if len(hostname) > 255:
            return False
        if hostname[-1] == '.' or hostname[0] == '.' or '.' not in hostname:
            return False
        if re.match('^([a-z\d\-.]*)$', hostname) is None:
            return False
        return True

    def _init_env_vars(self):
        # Main config options
        self.ISOLATE_BACKEND = os.getenv('ISOLATE_BACKEND', 'redis')
        self.ISOLATE_DATA_ROOT = os.getenv('ISOLATE_DATA_ROOT', '/opt/auth')
        self.ISOLATE_DEBUG = str2bool(os.getenv('ISOLATE_DEBUG', False))

        self.USER = os.getenv('USER', 'USER_ENV_NOT_SET')
        self.SUDO_USER = os.getenv('SUDO_USER', 'SUDO_USER_ENV_NOT_SET')
        self.ISOLATE_WRAPPER = os.getenv('ISOLATE_WRAPPER', 'sudo -u auth /mnt/data/auth/wrap/ssh.py')

        # User interface options
        # search print fields seporator
        self.ISOLATE_SPF_SEP = os.getenv('ISOLATE_SPF_SEP', ' | ')

        # Go to server immediately if only one server in group
        self.ISOLATE_BLINDE = str2bool(os.getenv('ISOLATE_BLINDE', True))

        # Colorize interface
        self.ISOLATE_COLORS = str2bool(os.getenv('ISOLATE_COLORS', False))

        # Search Print Line: fields names and order, not template
        self.ISOLATE_SPF = os.getenv('ISOLATE_SPF', 'server_id server_ip server_name').strip().split(' ')

    def _load_data(self):
        self.hosts_dump = sorted(self.db.get_hosts(), key=itemgetter('project_name', 'server_name'))
        self.projects = list(sorted(set(self.db.get_projects())))
        self.projects = [x.lower() for x in self.projects]
        self.projects_configs = self.db
        LOGGER.debug('_load_data')
        LOGGER.debug(json.dumps(self.hosts_dump, indent=4))
        LOGGER.debug(json.dumps(self.projects, indent=4))

    @staticmethod
    def _search_in_item(**kwargs):
        item = kwargs.get('item')
        item_keys = item.keys()
        # query_src = kwargs.get('query_src')
        query_lower = kwargs.get('query_lower')

        # project_id - is bad idea
        fields = kwargs.get('fields', ['project_name',
                                       'project_id',
                                       'server_name',
                                       'server_id',
                                       'server_ip',
                                       'os_version',
                                       'geoip_asn'])  # 'alerts'

        exact_match = kwargs.get('exact_match', False)

        if exact_match:
            for key in fields:
                if key not in item_keys:
                    continue
                if query_lower == str(item[key]).lower():
                    item['exact_match'] = key
                    return item
        else:
            for key in fields:
                if key not in item_keys:
                    continue
                if query_lower in str(item[key]).lower():
                    item['match_by'] = key
                    return item
        return False

    def search(self, query, **kwargs):
        time_search_start = time()
        source = kwargs.pop('source', self.hosts_dump)
        project_name = kwargs.pop('project_name', False)
        kwargs.update(query_src=str(query), query_lower=query.lower())

        result = list()

        for item in source:
            # project filter
            if project_name:
                if item['project_name'] != project_name:
                    continue

            item_query = copy(kwargs)
            item_query['item'] = item

            res = self._search_in_item(**item_query)
            if bool(res):
                result.append(res)

        kwargs.pop('query_lower')
        kwargs.update(search_time=float(time() - time_search_start))

        if kwargs.get('sort'):
            result = sorted(result, key=operator.itemgetter(kwargs.get('sort')))

        LOGGER.debug((query, kwargs))

        return result

    def colorize(self, text, color=None):
        colors = dict(
            header='\033[95m',
            okblue='\033[94m',
            okgreen='\033[92m',
            warning='\033[93m',
            fail='\033[91m',
            reset='\033[0m',
            bold='\033[1m',
            underline='\033[4m',
            # fields colors
            project_name='\033[38;5;45m',
            group_name='\033[38;5;45m',
            blue='\033[38;5;45m',
            critical='\033[38;5;160m',
            green='\033[38;5;40m',
            old='\033[38;5;142m',
            warn='\033[38;5;142m',
            status='\033[38;5;40m',
            os_version='\033[38;5;220m'
        )

        if not self.ISOLATE_COLORS or not colors.get(color, False):
            return text
        else:
            return '{0}{1}{2}'.format(colors.get(color), text, colors.get('reset'))

    def ljust_algin(self, host):
        # Minimum field size (add spaces)
        ljust_size = {
            'project_name': 8,
            'server_name': 24,
            'server_id': 6,
            'server_ip': 16,
            'ssh_config_ip': 16
        }

        host = copy(host)
        for key in self.ISOLATE_SPF:
            if key not in host.keys():
                continue
            if host[key] in [None, True, False]:
                continue
            if len(str(host[key])) > 0 and key in self.ISOLATE_SPF:
                if key in ljust_size:
                    host[key] = str(host[key]).ljust(ljust_size[key], ' ')
                if host[key][-1] != ' ':
                    host[key] += ' '
        return host

    def append_virtual_fields(self, host, **kwargs):
        # Some helpful fields hook
        ambiguous = kwargs.get('ambiguous', False)
        host_keys = host.keys()

        if ambiguous:
            self.ISOLATE_SPF = ['server_id', 'match_info', 'exact_match', 'server_id', 'project_name',
                             'server_ip', 'server_name']

        # matching debug field
        if 'match_info' in self.ISOLATE_SPF:
            match_info = list()
            if 'match_by' in host_keys:
                match_info.append('by: {}'.format(host['match_by']))
            if 'exact_match' in host_keys:
                match_info.append('exact: {}'.format(host['exact_match']))

            host['match_info'] = self.colorize(', '.join(match_info), color='okgreen')

        host['geoip_asn'] = host['geoip_asn'][:32]

        return host

    def print_hosts(self, hosts, **kwargs):
        title = kwargs.get('title', True)  # Print project title by default
        total = kwargs.get('total', True)
        current_project = None  # stub
        counter = 0

        if len(hosts) == 0:
            ambiguous = True
        else:
            ambiguous = kwargs.get('ambiguous', False)  # Hosts list is ambiguous

        if ambiguous:
            if len(hosts) == 0:
                self.print_p(self.colorize('\n  No servers found by this query: ', color='warn')
                             + ' '.join(self.args.sargs))
            else:
                self.print_p(self.colorize('\n  Ambiguous, more than one server found '
                                           'by this query: \n', color='warn'))

        if not title:
            self.print_p('')

        for host in hosts:
            # project_name
            # ------
            # Title
            if current_project != host['project_name'] and title and not ambiguous:
                current_project = host['project_name']
                title_tpl = '\n{0}\n------'.format(self.colorize(current_project, color='project_name'))
                self.print_p(title_tpl)

            # Fields print prepare
            host = self.append_virtual_fields(host, ambiguous=ambiguous)
            host = self.ljust_algin(host)

            # Concat strings
            host_line = []

            for field in self.ISOLATE_SPF:
                if field in host.keys():
                    host_line.append(host[field])

            if ambiguous or not title:
                line = '  ' + self.ISOLATE_SPF_SEP.join(host_line)
            else:
                line = self.ISOLATE_SPF_SEP.join(host_line)

            self.print_p(line)
            counter += 1

        if ambiguous:
            total_tpl = '\n  Total: {0}\n'.format(counter)
            self.print_p(total_tpl)

        elif total:
            total_tpl = '\n------\nTotal: {0}\n'.format(counter)
            self.print_p(total_tpl)
        else:
            self.print_p('')

    def autocomplete_update(self):
        self.db.put_projects_list()
        for project in self.projects:
            hosts = self.search(project, fields=['project_name'])
            hosts_names = ' '.join([d['server_name'] for d in hosts if 'server_name' in d]).lower()
            redis_key = 'complete_hosts_' + project
            self.db.put_hosts_per_project_list(redis_key, hosts_names)


def main():
    args, unknown_args = init_args()
    helper = AuthHelper(args, unknown_args)

    conn = ServerConnection(helper=helper, unknown_args=unknown_args)

    if args.action[0] == 'search':
        LOGGER.debug('its global search action')
        LOGGER.debug(args)
        LOGGER.debug(unknown_args)

        if len(args.sargs) == 1 and args.sargs[0] in helper.projects:
            search_results = helper.search(args.sargs[0], fields=['project_name'], exact_match=True)
        elif len(args.sargs) == 2 and args.sargs[0] in helper.projects:
            search_results = helper.search(args.sargs[1], project_name=args.sargs[0])
        else:
            search_results = helper.search(' '.join(args.sargs))

        helper.print_hosts(search_results)

    elif args.action[0] == 'go':

        if len(args.sargs) > 2:
            LOGGER.critical('Unknown sargs, see --help in --helper-debug for details')
            sys.exit(1)

        #
        # Only one arg
        #
        # if its some ID (only digits) search in server_id fields
        if len(args.sargs) == 1 and args.sargs[0].isdigit():
            conn.arg_type = 'server_id_only'
            conn.search_results = helper.search(args.sargs[0], fields=['server_id'], exact_match=True)

            if len(conn.search_results) == 1:
                conn.project_name = conn.search_results[0]['project_name']
                conn.server_id = args.sargs[0]
                conn.start()
            else:
                helper.print_hosts(conn.search_results, ambiguous=True)

        elif len(args.sargs) == 1 and args.sargs[0] in helper.projects:
            conn.arg_type = 'project_only'
            conn.project_name = args.sargs[0]
            conn.search_results = helper.search(args.sargs[0], fields=['project_name'], exact_match=True)

            if len(conn.search_results) == 1 and helper.ISOLATE_BLINDE:
                conn.server_id = conn.search_results[0]['server_id']
                conn.start()
            else:
                helper.print_hosts(conn.search_results)

        # if arg is ipv4 or fqdn
        elif len(args.sargs) == 1 and helper.is_valid_ipv4(args.sargs[0]):
            conn.arg_type = 'ipv4_only'
            conn.host = args.sargs[0]
            conn.start()

        elif len(args.sargs) == 1 and helper.is_valid_fqdn(args.sargs[0]):
            LOGGER.debug('is_valid_fqdn')
            conn.arg_type = 'fqdn_only'
            conn.host = args.sargs[0]
            conn.start()

        #
        # Two arguments
        #
        # if first arg is project and second ... shit
        elif len(args.sargs) == 2 and args.sargs[0] in helper.projects:
            conn.arg_type = 'project_with_some_shit'
            conn.project_name = args.sargs[0]
            conn.search_results = helper.search(args.sargs[1], project_name=conn.project_name,
                                                fields=['server_name', 'server_id', 'server_ip'],
                                                exact_match=True)

            if len(conn.search_results) == 1:
                if args.sargs[1].isdigit():
                    conn.arg_type = 'project_with_server_id_found'
                    conn.server_id = conn.search_results[0]['server_id']

                elif helper.is_valid_ipv4(args.sargs[1]):
                    conn.arg_type = 'project_with_ipv4_found'
                    conn.server_id = conn.search_results[0]['server_id']
                    conn.host = conn.search_results[0]['server_ip']
                elif helper.is_valid_fqdn(args.sargs[1]):
                    conn.arg_type = 'project_with_fqdn_found'
                    conn.server_id = conn.search_results[0]['server_id']
                    conn.host = conn.search_results[0]['server_name']
                else:
                    conn.arg_type = 'project_with_server_name_found'
                    conn.server_id = conn.search_results[0]['server_id']
                    conn.server_name = conn.search_results[0]['server_name']
                conn.start()

            elif len(conn.search_results) == 0 and len(args.sargs[1]) >= 2:
                if helper.is_valid_ipv4(args.sargs[1]):
                    conn.arg_type = 'project_with_ipv4_host_not_found'
                    conn.start()
                elif helper.is_valid_fqdn(args.sargs[1]) and not args.sargs[1].isdigit() and '.' in args.sargs[1]:
                    conn.arg_type = 'project_with_fqdn_host_not_found'
                    conn.start()
                else:
                    helper.print_hosts(conn.search_results, ambiguous=True)
            else:
                helper.print_hosts(conn.search_results, ambiguous=True)
        else:
            LOGGER.critical('args not match')

    elif args.action[0] == 'cron':
        # update autocomplete projects_list
        LOGGER.debug(helper.projects)
        helper.autocomplete_update()
    else:
        LOGGER.critical('Unknown action: ' + args.action[0])

    done_delta = round(time() - helper.time_start, 3)
    LOGGER.debug('run time: ' + str(done_delta) + ' sec')

if __name__ == '__main__':
    main()
