# Main auth startup
# add to /etc/bashrc
# Example:
# if [ -f /opt/auth/shared/bash.sh ]; then
#     source /opt/auth/shared/bash.sh;
# fi

source /opt/auth/shared/bootstrap.sh;
HISTTIMEFORMAT='[%F %T] '
HISTSIZE=10000
HISTFILESIZE=10000
shopt -s histappend # Append history instead of rewriting it
shopt -s cmdhist # Use one command per line
export PS1="[\\[\\033[38;5;75m\\]\\h\\[\\033[0m\\]][\\w]\\$ "


# Only projects completition for S and G
_projects_bash()
{
    local cur_word prev_word projects_list

    cur_word="${COMP_WORDS[COMP_CWORD]}"
    prev_word="${COMP_WORDS[COMP_CWORD-1]}"

    projects_list=$(redis-cli -a ${ISOLATE_REDIS_PASS} get "projects_list")

    if [ "${COMP_CWORD}" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "${projects_list}" -- "${cur_word}") )
    fi

    return 0
}

complete -F _projects_bash s


_project_host_bash()
{
    local cur_word prev_word projects_list

    cur_word="${COMP_WORDS[COMP_CWORD],,}"
    prev_word="${COMP_WORDS[COMP_CWORD-1],,}"

    projects_list=$(redis-cli -a ${ISOLATE_REDIS_PASS} get "projects_list")

    hosts_list=$(redis-cli -a ${ISOLATE_REDIS_PASS} get "complete_hosts_${prev_word}" )


    hosts_list=$(jq -r --arg query "${prev_word}" '.[] | select(.project==$query) | "\(.server_name_pretty)"' "${ITS_HOSTS_DATA}/hosts.json" 2>/dev/null | tr '[:upper:]' '[:lower:]'  2>>/dev/null )

    if [ "${COMP_CWORD}" -eq 1 ]; then
        COMPREPLY=( $(compgen -W "${projects_list}" -- "${cur_word}") )
    elif [ "${COMP_CWORD}" -eq 2 ]; then
        COMPREPLY=( $(compgen -W "${hosts_list}" -- "${cur_word}") )
    fi

    return 0
}

complete -F _project_host_bash g