umask 0077;
USER="${USER:-NO_USER_ENV}";
ISOLATE_DATA_ROOT="${ISOLATE_DATA_ROOT:-/opt/auth}";
ISOLATE_SHARED="${ISOLATE_DATA_ROOT}/shared";
ISOLATE_HELPER="${ISOLATE_SHARED}/helper.py";
ISOLATE_DEPLOY_LOCK="${ISOLATE_DATA_ROOT}/.deploy";
ISOLATE_COLORS=true;
ISOLATE_DEFAULT_PROJECT="${ISOLATE_DEFAULT_PROJECT:-main}";

export USER;
export ISOLATE_DATA_ROOT;
export ISOLATE_SHARED;
export ISOLATE_HELPER;
export ISOLATE_COLORS;
export ISOLATE_DEPLOY_LOCK;
export ISOLATE_COLORS;
export ISOLATE_DEFAULT_PROJECT;


export LANG="en_US.UTF-8";
export LC_COLLATE="en_US.UTF-8";
export LC_CTYPE="en_US.UTF-8";
export LC_MESSAGES="en_US.UTF-8";
export LC_MONETARY="en_US.UTF-8";
export LC_NUMERIC="en_US.UTF-8";
export LC_TIME="en_US.UTF-8";
export LC_ALL="en_US.UTF-8";

PYTHONDONTWRITEBYTECODE=1;
export PYTHONDONTWRITEBYTECODE;

gen-oath-safe () {
    bash --norc "${ISOLATE_DATA_ROOT}/shared/gen-oath-safe.sh";
}

}
redis-dev () {
    redis-cli -a "${ISOLATE_REDIS_PASS}" "${@}";
}

deploy_lock () {
    while [ ! -d "${ISOLATE_DATA_ROOT}" ]; do
        echo "ISOLATE Git root not found: ${ISOLATE_DATA_ROOT} awaiting deploy...";
        sleep 1;
    done

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
    export ISOLATE_SESSION;
    trap auth_callback_cleanup SIGHUP SIGINT SIGTERM EXIT;

    "${@}";

    source "${ISOLATE_SESSION}" > /dev/null 2>&1;
    auth_callback_cleanup;

    if [ "${ISOLATE_CALLBACK}" == "${ISOLATE_SESSION}" ]; then
        "${ISOLATE_CALLBACK_CMD:-/bin/false}";
    fi
}

g () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: g <project|host> [server_name] [ --user | --port | --nosudo | --debug ] \\n";
        return
    elif [[ $# -gt 0 ]] ; then
        deploy_lock
        auth_callback "${ISOLATE_HELPER}" go "${@}";
    fi
}

s () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: s <query> \\n";
        return
    elif [[ $# -gt 0 ]] ; then
        deploy_lock
        "${ISOLATE_HELPER}" search "${@}";
    fi
}

auth-add-user () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-add-user <username> \\n";
        return
    elif [[ $# -gt 0 ]] ; then
        useradd "${1}" -m --groups auth -s /bin/bash;
        passwd "${1}";
    fi
}

auth-add-host () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-add-host --project <project_name> --server-name <server_name> --ip 1.2.3.4 --port 22 --user root --nosudo \\n";
        return
    elif [[ $# -gt 0 ]] ; then
        "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "add-host" "${@}";
    fi
}

auth-dump-host () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-dump-host <server_id>\\n";
        return
    elif [[ $# -gt 0 ]] ; then
        "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "dump-host" --server-id "${@}";
    fi
}

auth-del-host () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-del-host <server_id>\\n";
        return
    elif [[ $# -gt 0 ]] ; then
        "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "del-host" --server-id "${@}";
    fi
}

auth-add-project-config () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-add-project-config <project_name> --port 3222 --user root3 --nosudo \\n";
        return
    elif [[ $# -gt 0 ]] ; then
        "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "add-project-config" --project "${@}";
    fi
}

auth-del-project-config () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-del-project-config <project_name>\\n";
        return
    elif [[ $# -gt 0 ]] ; then
        "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "del-project-config" --project "${@}";
    fi
}

auth-dump-project-config () {
    if [[ $# -eq 0 ]] ; then
        echo -e "\\n  Usage: auth-dump-project-config <project_name>\\n";
        return
    elif [[ $# -gt 0 ]] ; then
        "${ISOLATE_DATA_ROOT}/shared/auth-manager.py" "dump-project-config" --project "${@}";
    fi
}