umask 0077;
USER="${USER:-NO_USER_ENV}"
AUTH_DATA_ROOT="${AUTH_DATA_ROOT:-/opt/auth}";
AUTH_SHARED="${AUTH_DATA_ROOT}/shared";
AUTH_HELPER="${AUTH_SHARED}/helper.py";
DEPLOY_LOCK="${AUTH_DATA_ROOT}/.deploy";
AUTH_COLORS=true

export USER;
export AUTH_DATA_ROOT;
export AUTH_SHARED;
export AUTH_HELPER;
export AUTH_COLORS;

export LANG="en_US.UTF-8"
export LC_COLLATE="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
export LC_MESSAGES="en_US.UTF-8"
export LC_MONETARY="en_US.UTF-8"
export LC_NUMERIC="en_US.UTF-8"
export LC_TIME="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

deploy_lock () {
    while [ -f "${DEPLOY_LOCK}" ]; do
        echo "Lock found: ${DEPLOY_LOCK} awaiting deploy end...";
        sleep 1;
    done
}

auth_callback_cleanup () {
    # cat "${AUTH_SESSION}" 2>/dev/null;
    rm -f "${AUTH_SESSION}" > /dev/null 2>&1 || /bin/true;
}

auth_callback () {
    if [[ $# -eq 0 ]] ; then
        return
    fi
    SESS_DIR="${HOME}/.auth_sess";
    if [[ ! -d "${SESS_DIR}" ]] ; then
        mkdir -p "${SESS_DIR}";
    fi

    AUTH_SESSION=$(mktemp "${SESS_DIR}/ssh_XXXXXXXXX");
    trap auth_callback_cleanup SIGHUP SIGINT SIGTERM EXIT;

    "${@}";

    source "${AUTH_SESSION}" > /dev/null 2>&1;
    auth_callback_cleanup;

    if [ "${AUTH_CALLBACK}" == "${AUTH_SESSION}" ]; then
        ${AUTH_CALLBACK_CMD:-/bin/false};
    fi
}

g () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\n  Usage: g <project|host> [server_name] [ --user | --port | --nosudo | --debug ] \n";
        return
    elif [[ $# -gt 0 ]] ; then
        deploy_lock
        auth_callback "${AUTH_HELPER}" go "${@}";
    fi
}

s () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\n  Usage: s <query> \n";
        return
    elif [[ $# -gt 0 ]] ; then
        deploy_lock
        "${AUTH_HELPER}" search "${@}";
    fi
}

auth-add-user () {
    useradd "${1}" -m --groups auth;
    passwd "${1}";
}

auth-add-host () {
    "${AUTH_DATA_ROOT}/shared/auth-manager.py" "add-host"  "${@}";
}

auth-del-host () {
    "${AUTH_DATA_ROOT}/shared/auth-manager.py" "del-host" --server-id "${@}";
}