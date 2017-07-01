# isolate

[![Build Status](https://travis-ci.org/itsumma/isolate.svg?branch=master)](https://travis-ci.org/itsumma/isolate)

![Image](main.png)

bastion host setup scripts.

## Supports

* [OTP](https://en.wikipedia.org/wiki/One-time_password) (counter and time based) 2FA algorithms
* SSH sessions logging

## Requirements

* Fresh CentOS 7+ setup
* [Ansible](http://docs.ansible.com/ansible/intro_installation.html) for
install or update

## INSTALL

edit `ansible/hosts.ini` and run:
```
cd ansible
ansible-playbook main.yml
```

and restart server
```
# reboot
```

append to `/etc/bashrc`
```
if [ -f /opt/auth/shared/bash.sh ]; then
    source /opt/auth/shared/bash.sh;
fi
```

append to `/etc/sudoers` or use `visudo`
```
%auth ALL=(auth) NOPASSWD: /opt/auth/wrappers/ssh.py
```

### SSH
edit `/etc/ssh/sshd_config`:
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
append to `/etc/pam.d/sshd`
```
auth    required    pam_oath.so usersfile=/etc/oath/users.oath window=20 digits=6
```

Example:
```
auth    required    pam_sepermit.so
auth    substack    password-auth

auth    required    pam_oath.so usersfile=/etc/oath/users.oath window=20 digits=6

auth    include     postlogin
```

```
sed -i -e 's/ChallengeResponseAuthentication no/ChallengeResponseAuthentication yes/g' /etc/ssh/sshd_config
```
append to `/etc/ssh/sshd_config`

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

auth-add-host --project drugstore --server-name aws-eu-prod --ip 4.1.1.1 --port 25 --user dealer --nosudo
```


### Road Map

* Kibana logging
* Hosts storage plugins (redis, mongo, 24mon)
* ZSH support
* Web-Hooks
* Zabbix support
* NewRelic support
* CI
* GeoIP ASN lookup
* [Ideas?](mailto:ilya.yakovlev@me.com)
