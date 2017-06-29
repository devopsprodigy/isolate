SUPPORT_USER="support"
KEY="{{ support_key }}"

set -e;
set -x;

useradd -m ${SUPPORT_USER}
mkdir /home/${SUPPORT_USER}/.ssh
echo ${KEY} >> /home/${SUPPORT_USER}/.ssh/authorized_keys
chmod 600 /home/${SUPPORT_USER}/.ssh/authorized_keys
chmod 700 /home/${SUPPORT_USER}/.ssh/
chown -R ${SUPPORT_USER}:${SUPPORT_USER} /home/${SUPPORT_USER}/.ssh/
echo "${SUPPORT_USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
