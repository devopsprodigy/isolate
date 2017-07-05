# Main auth startup
# add to /etc/zshrc
# Example:
# if [ -f /opt/auth/shared/zsh.sh ]; then
#     source /opt/auth/shared/zsh.sh;
# fi

source /opt/auth/shared/bootstrap.sh;

_project_zsh () {
    # project complete
    local -a _1st_arguments
    _1st_arguments=(
        $(cat /mnt/data/auth/Shared/hosts/projects.txt)
        )

    _arguments '*:: :->subcmds' && return 0

    if (( CURRENT == 1 )); then
        _describe -t commands "ng projects" _1st_arguments -V1
        return
    fi
}

_stub_comp () { return }


autoload -U history-search-end
# zle -N history-beginning-search-backward-end history-search-end
# bindkey "^[[A" history-beginning-search-backward-end

autoload -U up-line-or-beginning-search
autoload -U down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search
bindkey "^[[A" up-line-or-beginning-search # Up
bindkey "^[[B" down-line-or-beginning-search # Down


autoload -U compinit && compinit

compdef _project_zsh s g

# Main ZSH options
# History
HISTFILE="$HOME/.zsh_history"
HISTSIZE=10000
SAVEHIST=10000
setopt share_history            # share hist between sessions
setopt hist_ignore_all_dups     # no duplicate
unsetopt hist_ignore_space      # ignore space prefixed commands

setopt auto_cd                  # if command is a path, cd into it
setopt auto_remove_slash        # self explicit
setopt chase_links              # resolve symlinks
# setopt correct                # try to correct spelling of commands
# setopt print_exit_value         # print return value if non-zero

unsetopt beep                   # no bell on error
unsetopt nomatch                # asterisk * fix
# unsetopt hup                  # no hup signal at shell exit (fuck yeah)
unsetopt rm_star_silent         # ask for confirmation for `rm *' or `rm path/*'

zstyle ':completion::complete:*' use-cache off
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|=*' 'l:|=* r:|=*'

zstyle -e ':completion:*:default' list-colors 'reply=("${PREFIX:+=(#bi)($PREFIX:t)(?)*==01=01}:${(s.:.)LS_COLORS}")'

PROMPT='[%F{cyan}%m%f %F{yellow}%1~%f]# '

bindkey  "^[[H"   beginning-of-line
bindkey  "^[[F"   end-of-line
bindkey    "^[[3~"          delete-char
bindkey    "^[3;5~"         delete-char