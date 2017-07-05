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

export PS1="\[\033[38;5;75m\][\h]\[\033[0m\][\w]\$ "
