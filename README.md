# isolate

[![Build Status](https://travis-ci.org/itsumma/isolate.svg?branch=master)](https://travis-ci.org/itsumma/isolate)
[![Gitter chat](https://badges.gitter.im/gitterHQ/gitter.png)](https://gitter.im/isolate_bastion/Lobby)

![Image](main.png)

bastion host setup scripts.

## Supports

* [OTP](https://en.wikipedia.org/wiki/One-time_password) (counter and time based) 2FA algorithms
* SSH sessions logging

## Requirements

* Fresh CentOS 7+ setup
* [Ansible](http://docs.ansible.com/ansible/intro_installation.html) 2.3+ for
install or update

## INSTALL

edit

`ansible/hosts.ini`

and run:
```
cd ansible
ansible-playbook main.yml
```

and restart server
```
# reboot
```

append to

`/etc/bashrc`
```
if [ -f /opt/auth/shared/bash.sh ]; then
    source /opt/auth/shared/bash.sh;
fi
```

append to

`/etc/sudoers` or use `visudo`
```
%auth ALL=(auth) NOPASSWD: /opt/auth/wrappers/ssh.py
```

### SSH
edit

`/etc/ssh/sshd_config`:
```
# AuthorizedKeysFile /etc/keys/%u_authorized_keys
PermitRootLogin without-password
PasswordAuthentication yes
GSSAPIAuthentication no
AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
UseDNS no
MaxStartups 48:20:300
TCPKeepAlive yes
ClientAliveInterval 36
ClientAliveCountMax 2400
```

```
systemctl restart sshd
systemctl status sshd
```

### OTP
append to

`/etc/pam.d/sshd`
```
auth       required     pam_oath.so usersfile=/etc/oath/users.oath window=20 digits=6
```

Example:
```
#%PAM-1.0
auth	   required     pam_sepermit.so
auth	   substack     password-auth
auth       required     pam_oath.so usersfile=/etc/oath/users.oath window=20 digits=6
auth	   include	    postlogin
...>
```

```
sed -i -e 's/ChallengeResponseAuthentication no/ChallengeResponseAuthentication yes/g' /etc/ssh/sshd_config
```

append to

`/etc/ssh/sshd_config`

```
Match Group auth
    AuthenticationMethods keyboard-interactive
```
```
systemctl restart sshd
systemctl status sshd
```

## Management

#### load auth environment
```
# source /opt/auth/shared/bash.sh;
```

#### add user
```
# auth-add-user username
```

#### generate otp
```
# Time-Based (Mobile and Desktop apps)
gen-oath-safe username totp

# Counter-Based (Yubikey and Mobile apps)
gen-oath-safe username hotp

# and append user secret to /etc/oath/users.oath
# Example: HOTP username - d7dc876e503ec498e532c331f3906153318ec565
```

#### local user ssh config template

append to

top of

 `~/.ssh/config`
```
Host auth
    HostName 1.2.3.4
    Port 22
    User <username>
    ForwardAgent no
    ControlPath ~/.ssh/%r@%h:%p
    ControlMaster auto
    ControlPersist 3h
```

Persistent connection - for easy connection reopen without OTP and password prompt. (3h hours inactive timeout)

### Data sources

append to

`/etc/bashrc`
```
ISOLATE_BACKEND=redis; # or zabbix
export ISOLATE_BACKEND;
```

#### Redis

```
ISOLATE_REDIS_HOST="127.0.0.1";
ISOLATE_REDIS_PORT="6379";
ISOLATE_REDIS_DB=0;
ISOLATE_REDIS_PASS="te2uth4dohLi8i"; # /etc/redis.conf
export ISOLATE_REDIS_HOST;
export ISOLATE_REDIS_PORT;
export ISOLATE_REDIS_PASS;
export ISOLATE_REDIS_DB;
```

#### Zabbix

```
ISOLATE_ZABBIX_URL="http://zabbix.95.213.200.160.xip.name"
ISOLATE_ZABBIX_USER="isolate"
ISOLATE_ZABBIX_PASS="aZ1eil2ooz4Iefah"
export ISOLATE_ZABBIX_URL;
export ISOLATE_ZABBIX_USER;
export ISOLATE_ZABBIX_PASS;
```


#### add server
```
$ auth-add-host --project starwars --server-name sel-msk-prod --ip 1.1.1.1
Database updated
```

#### del server
```
$ auth-del-host <server_id>
```

#### test data
```
auth-add-host --project starwars --server-name sel-msk-prod --ip 1.1.1.1
auth-add-host --project starwars --server-name sel-spb-reserve --ip 1.1.1.2
auth-add-host --project starwars --server-name sel-spb-dev --ip 1.1.1.3

auth-add-host --project tinyfinger --server-name do-ams3-prod --ip 2.1.1.1
auth-add-host --project tinyfinger --server-name do-nyc-dev --ip 2.1.1.3

auth-add-host --project powerrangers --server-name aws-eu-prod --ip 3.1.1.1
auth-add-host --project powerrangers --server-name aws-eu-reserve --ip 3.1.1.2

# custom host/port/user options
auth-add-host --project drugstore --server-name aws-eu-prod --ip 4.1.1.1 --port 25 --user dealer --nosudo
```


### Host behind ssh proxy (client side bastion)

`nc`/`netcat` need to be installed to bastion host.
Or you can try use `-W host:port` options for ssh,
but on old Centos/Ubuntu it not work (old sshd versions).

You can use insecure proxy host for connections to other servers safely
(not need private keys on client side bastion host),
Over `ProxyCommand` established sub ssh session with all authentication steps.

```
## add proxy
auth-add-host --project bigcorp --server-name au-prod-bastion --ip 45.45.45.45 --port 2232
Database updated: 10001

# and use this id (10001) as proxy to other hosts

## add hosts in network
auth-add-host --project bigcorp --proxy-id 10001 --server-name au-prod-web1 --ip 192.168.1.1
auth-add-host --project bigcorp --proxy-id 10001 --server-name au-prod-web2 --ip 192.168.1.2
auth-add-host --project bigcorp --proxy-id 10001 --server-name au-prod-web3 --ip 192.168.1.3
```

This ability useful for `Amazon VPC`
or other `VPC` provider with limited global internet ips and internal networking setup.

Also you can setup separate VPN host and use it as next hop, to ablie login to hosts over VPN.

### Project/Group default settings

```
$ auth-add-project-config --project NewProject --proxy-id 10001 --port 2222
```

Host config override per project setting.

### S - aka search

```
[auth1][~]# s aws

drugstore
------
100009  | 4.1.1.1          | aws-eu-prod

powerrangers
------
100007  | 3.1.1.1          | aws-eu-prod
100008  | 3.1.1.2          | aws-eu-reserve

------
Total: 3

[auth1][~]#
```


### G - aka go

simple usage (just go to any server by ip with default user/port/key):
```
$ g 1.2.3.4
```

if connection not established as expected use `--debug`:
```
$ g 1.2.3.4 --port 3232 --user cheburajhka --debug
```

it puts `-v` option for `ssh` and show all helper/wrapper debug logs.

`--nosudo` - by default, ssh session opened with `sudo -i` (become root).
But on old FreeBSD or systems without `sudo` it not working as expected.
```
$ g 1.2.3.4 --nosudo
```


#### G with two arguments

example:
```
$ g bigcorp au-prod-web2
# g bigcorp 192.168.1.1
```

more complex example:
```
s bigcorp

bigcorp
------
100012  | 192.168.1.2      | au-prod-web2
100013  | 192.168.1.3      | au-prod-web3
100010  | 45.45.45.45      | au-prod-bastion
100011  | 192.168.1.1      | au-prod-web1

------
Total: 4
```

Use exist proxy by server_id (proxy_id == server_id):
```
# this line override all project and global defaults
$ g bigcorp 192.168.1.2 --user root --nosudo --port 4322 --proxy-id 100010
```

Set any accessable host as proxy:
```
g bigcorp 192.168.1.2 --proxy-host 33.22.44.88 --proxy-port 8022 --proxy-user pfwd
```

## Logs

```
/opt/auth/logs/${USER}/${USER}_${SSH_HOST}_${SSH_PORT}_${SSH_CONFIG}_1485110002_<uuid>.log
```

also with all logs, `ssh.py` creates `*.meta` files with JSON object.

## SSH Client configuration

`configs/defaults.conf`
```
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    TCPKeepAlive yes
    ServerAliveInterval 40
    ServerAliveCountMax 3
    ConnectTimeout 180
    ForwardAgent no
    UseRoaming no
    User support
    Port 22
    IdentityFile /home/auth/.ssh/id_rsa
```


### Autocomplete

BASH and ZSH, both have a completition support.

Simple search (project) completition:
```
$ g tiny<tab><tab>
...
$ g tinyfinger
```
If you try `g project_name` without `host` argument:

 `a)` in project >1 servers. Action: show hosts list for this project.

 `b)` in project == 1 server. (only one server at project/group)

In `b` variant, helper lookups hosts list, and if only
one host in project/group -> just login to it.

You can disable blind mode by setting in you global/local `bashrc`:

```
export ISOLATE_BLINDE=false;
```

## User settings

This options can be added to local user `~/.bashrc`

```
ISOLATE_COLORS='true'
export ISOLATE_COLORS

# Search & Print fields for servers list
ISOLATE_SPF='server_id server_ip server_name'
export ISOLATE_SPF

# if only one server in project/group
ISOLATE_BLIND='false'
export ISOLATE_BLIND
```

### Road Map

* Kibana logging
* Web-Hooks (for add/remove servers and alerting)
* NewRelic support
* Ansible inventory generate script
* SELinux Support
* Encrypted block device setup How-To
* Paranoic setup
* [Ideas?](mailto:ilya.yakovlev@me.com)
