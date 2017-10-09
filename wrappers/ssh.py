#!/usr/bin/env python
import os
import sys
import socket
import errno
import re
import json
import time
import argparse
import logging
import uuid

LOGGER = logging.getLogger('ssh-wrapper')
LOG_FORMAT = '[%(asctime)s] [%(levelname)6s] %(name)s %(message)s'

__version__ = '0.0.24'

# set proper working dir
working_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(working_dir)

# Get user real name
local_sudo_user = os.getenv('SUDO_USER', 'NO_SUDO_USER_ENV')

data_root = '/opt/auth'
ssh_configs_path = data_root + '/configs'
logs_base_path = data_root + '/logs'

# args prepare
# args = sys.argv[1:]

# misc
local_timestamp = int(time.time())

term_colors = {
    'gray': '\033[38;5;249m',
    'blue': '\033[38;5;45m',
    'red': '\033[38;5;160m',
    'green': '\033[38;5;40m',
    'reset': '\033[0m',
    'orange': '\033[38;5;220m',
    'bebe': '\033[38;5;142m'
}


# ssh config
ssh_command = '/usr/bin/ssh' + ' -e none -F ' + os.path.join(ssh_configs_path, 'defaults.conf')


def mkdir(path):
    try:
        os.makedirs(path)
        return True
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            return True
            pass
        else:
            raise


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
    if hostname.startswith('-'):
        return False
    return True


def verify_args(args):

    host = dict()
    host['hostname'] = None
    host['port'] = None
    host['user'] = None
    host['proxy_id'] = args.proxy_id
    host['proxy_host'] = None
    host['proxy_port'] = None
    host['proxy_user'] = None
    host['nosudo'] = bool(args.nosudo)
    host['debug'] = bool(args.debug)

    # host
    hostname = args.hostname[0]

    if is_valid_ipv4_address(hostname) or is_valid_ipv6_address(hostname) or is_valid_fqdn(hostname):
        host['hostname'] = hostname
    else:
        LOGGER.critical('[hostname] Validation not passed')
        sys.exit(1)

    if args.user is not None:
        user = args.user[0]
        if re.match('^[A-Za-z,\d\-]*$', user) is None or \
                                        len(user) > 48 or \
                                        user.startswith('-'):
            LOGGER.critical('[user] Validation not passed')
            sys.exit(1)

        host['user'] = user
        LOGGER.debug('[user] override is set: ' + user)

    if args.port is not None:
        port = int(args.port)
        if port > 65535 or port <= 0:
            LOGGER.critical('[port] Validation not passed')
            sys.exit(1)
        else:
            host['port'] = int(port)
            LOGGER.debug('[port] override is set: ' + str(port))

    # proxy_host
    if args.proxy_host is not None:
        proxy_host = args.proxy_host[0]
        if (is_valid_ipv4_address(proxy_host) or \
                is_valid_ipv6_address(proxy_host) or \
                is_valid_fqdn(proxy_host)) and not proxy_host.startswith('-'):
            host['proxy_host'] = proxy_host
        else:
            LOGGER.critical('[proxy_host] Validation not passed')
            sys.exit(1)

    if args.proxy_user is not None:
        proxy_user = args.proxy_user[0]
        if re.match('^[A-Za-z\d\-]*$', proxy_user) is None or \
                                                   len(proxy_user) > 48 or \
                                                   proxy_user.startswith('-'):
            LOGGER.critical('[proxy_user] Validation not passed')
            sys.exit(1)

        host['proxy_user'] = proxy_user
        LOGGER.debug('[proxy_user] override is set: ' + proxy_user)

    if args.proxy_port is not None:
        proxy_port = int(args.proxy_port)
        if proxy_port > 65535 or proxy_port <= 0:
            LOGGER.critical('[proxy_port] Validation not passed')
            sys.exit(1)
        else:
            host['proxy_port'] = proxy_port
            LOGGER.debug('[proxy_port] override is set: ' + str(proxy_port))

    return host


# make dirs and prepare files
def init_log_file(host):

    host['wrap_ver'] = __version__
    host['uuid'] = str(uuid.uuid4())
    host['auth_user'] = local_sudo_user
    host['auth_ts'] = local_timestamp
    host['sys_argv'] = sys.argv
    host['server_ip'] = args.hostname[0]

    current_user_log_dir = '{0}/{1}'.format(logs_base_path, local_sudo_user)
    mkdir(current_user_log_dir)

    # example: /tmp/root/root_127.0.0.1_22_common_1485110002_<uuid>.log
    current_log_path = '{0}/{1}_{2}_{3}_{4}_{5}.log'.format(current_user_log_dir,
                                                            local_sudo_user,
                                                            host['hostname'],
                                                            host['port'],
                                                            local_timestamp,
                                                            host['uuid'][:12])

    host['log_path'] = current_log_path
    loger_pipe_cmd = 'tee >( awk -f {0}/timecode.awk >> {1} );'.format(working_dir, current_log_path)

    LOGGER.debug(current_log_path)

    # write logfile metadata
    log_meta = '{0}'.format(json.dumps(host, indent=4))
    with open(current_log_path + '.meta', 'w') as log_f:
        log_f.write(log_meta)

    LOGGER.debug(log_meta)

    return loger_pipe_cmd


def run_command(cmd):

    LOGGER.debug(cmd)

    exit_code = os.system(cmd)

    if exit_code != 0:
        msg = 'Exit code: {1}{0}{2}'.format(exit_code, term_colors['red'], term_colors['reset'])
        msg = '\n  {0}\n'.format(msg)
        LOGGER.warn(msg)
    return exit_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='ssh-wrapper', epilog='------',
                                     description='ssh sudo wrapper')
    #
    parser.add_argument('hostname', type=str, help='server address (allowed FQDN,[a-z-],ip6,ip4)', nargs=1)
    parser.add_argument('--user', type=str, help='set target username', nargs=1)
    parser.add_argument('--port', type=int, help='set target port')
    parser.add_argument('--nosudo', action='store_true', help='run connection without sudo terminating command')
    parser.add_argument('--config', help='DEPRECATED', type=str, nargs=1)
    parser.add_argument('--debug', action='store_true')
    #
    parser.add_argument('--proxy-host', type=str, nargs=1)
    parser.add_argument('--proxy-user', type=str, nargs=1)
    parser.add_argument('--proxy-port', type=int)
    parser.add_argument('--proxy-id', type=str, nargs=1, help='just for pretty logs')
    args = parser.parse_args()
    #
    if args.debug:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                            format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
        LOGGER.info('ssh wrapper debug mode on')
        LOGGER.info(sys.argv)
        LOGGER.info(vars(args))
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.WARN,
                            format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    #
    LOGGER.info(__version__)
    LOGGER.debug(working_dir)
    LOGGER.debug(args)
    #
    host_meta = verify_args(args)
    log_pipe = init_log_file(host_meta)
    #
    ssh_args = []
    ssh_proxy_args = []

    # host connection
    if args.debug:
        ssh_args.append('-v')
    if bool(host_meta['user']):
        ssh_args.append('-l ' + str(host_meta['user']))
    if bool(host_meta['port']):
        ssh_args.append('-p ' + str(host_meta['port']))
    if bool(host_meta['hostname']):
        ssh_args.append(host_meta['hostname'])
    if host_meta['nosudo'] is False:  # if nosudo disabled <_<
        ssh_args.append('\'sudo -i\'')
    ssh_args = ' '.join(ssh_args)
    ssh_args += ' 2>&1'

    # ProxyCommand
    # if configs present
    if args.proxy_host:
        # if args.debug:
        #     ssh_proxy_args.append('-v')
        if bool(host_meta['proxy_user']):
            ssh_proxy_args.append('-l ' + str(host_meta['proxy_user']))
        if bool(host_meta['proxy_port']):
            ssh_proxy_args.append('-p ' + str(host_meta['proxy_port']))
        if bool(host_meta['proxy_host']):
            ssh_proxy_args.append(host_meta['proxy_host'])

        ssh_proxy_args = ' '.join(ssh_proxy_args)
        proxy_cmd = '-o ProxyCommand=\'{0} {1} nc %h %p\''.format(ssh_command, ssh_proxy_args)

        cmd = 'bash --norc -c "{0} -t {1} {2} | {3} "'.format(ssh_command, proxy_cmd, ssh_args, log_pipe)
    else:
        cmd = 'bash --norc -c "{0} -t {1} | {2} "'.format(ssh_command, ssh_args, log_pipe)

    LOGGER.debug(cmd)
    LOGGER.debug(host_meta)

    host_meta['cmd'] = cmd
    run_command(cmd)
