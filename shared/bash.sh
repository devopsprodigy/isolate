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
export PS1="\\[\\033[38;5;75m\\][\\h]\\[\\033[0m\\][\\w]\\$ "


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

complete -F _projects_bash s g