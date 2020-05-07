FROM ubuntu:xenial

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y \
        vim \
        sudo \
        python \
        python-dev \
        python-pip \
        openssh-server \
        libpam-oath \
        liboath0 \
        liboath-dev \
        oathtool \
        libgeoip-dev \
        caca-utils \
        qrencode \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/* \
    && mkdir /var/run/sshd \
    && useradd auth \
    && echo "%auth ALL=(auth) NOPASSWD: /opt/auth/wrappers/ssh.py" >> /etc/sudoers \
    && echo "[ -f /opt/auth/shared/bash.sh ] && source /opt/auth/shared/bash.sh" >> /etc/bash.bashrc

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

EXPOSE 22

ENTRYPOINT ["/usr/sbin/sshd", "-D", "-e"]
