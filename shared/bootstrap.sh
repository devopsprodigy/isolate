umask 0077;
USER="${USER:-NO_USER_ENV}";
ISOLATE_DATA_ROOT="${ISOLATE_DATA_ROOT:-/opt/auth}";
ISOLATE_SHARED="${ISOLATE_DATA_ROOT}/shared";
ISOLATE_HELPER="${ISOLATE_SHARED}/helper.py";
ISOLATE_DEPLOY_LOCK="${ISOLATE_DATA_ROOT}/.deploy";
ISOLATE_COLORS=true;

export USER;
export ISOLATE_DATA_ROOT;
export ISOLATE_SHARED;
export ISOLATE_HELPER;
export ISOLATE_COLORS;

export LANG="en_US.UTF-8";
export LC_COLLATE="en_US.UTF-8";
export LC_CTYPE="en_US.UTF-8";
export LC_MESSAGES="en_US.UTF-8";
export LC_MONETARY="en_US.UTF-8";
export LC_NUMERIC="en_US.UTF-8";
export LC_TIME="en_US.UTF-8";
export LC_ALL="en_US.UTF-8";

deploy_lock () {
    while [ -f "${ISOLATE_DEPLOY_LOCK}" ]; do
        echo "Lock found: ${ISOLATE_DEPLOY_LOCK} awaiting deploy end...";
        sleep 1;
    done
}

auth_callback_cleanup () {
    # cat "${ISOLATE_SESSION}" 2>/dev/null;
    rm -f "${ISOLATE_SESSION}" > /dev/null 2>&1 || /bin/true;
}

auth_callback () {
    if [[ $# -eq 0 ]] ; then
        return
    fi
    SESS_DIR="${HOME}/.auth_sess";
    if [[ ! -d "${SESS_DIR}" ]] ; then
        mkdir -p "${SESS_DIR}";
    fi

    ISOLATE_SESSION=$(mktemp "${SESS_DIR}/ssh_XXXXXXXXX");
    trap auth_callback_cleanup SIGHUP SIGINT SIGTERM EXIT;

    "${@}";

    source "${ISOLATE_SESSION}" > /dev/null 2>&1;
    auth_callback_cleanup;

    if [ "${ISOLATE_CALLBACK}" == "${ISOLATE_SESSION}" ]; then
        ${ISOLATE_CALLBACK_CMD:-/bin/false};
    fi
}

g () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\n  Usage: g <project|host> [server_name] [ --user | --port | --nosudo | --debug ] \n";
        return
    elif [[ $# -gt 0 ]] ; then
        deploy_lock
        auth_callback "${ISOLATE_HELPER}" go "${@}";
    fi
}

s () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\n  Usage: s <query> \n";
        return
    elif [[ $# -gt 0 ]] ; then
        deploy_lock
        "${ISOLATE_HELPER}" search "${@}";
    fi
}

auth-add-user () {
    useradd "${1}" -m --groups auth;
    passwd "${1}";
}

auth-add-host () {
    "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "add-host"  "${@}";
}

auth-del-host () {
    "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "del-host" --server-id "${@}";
}