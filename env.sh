#!/usr/bin/env bash
# Shared environment detection for X11 display + auth.

detect_display() {
    if [[ -n "${DISPLAY:-}" ]]; then
        return 0
    fi
    local pid disp
    for pid in $(pgrep -u "$(id -u)" -x gnome-shell Xorg Xwayland gnome-session 2>/dev/null); do
        disp=$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | grep '^DISPLAY=' | cut -d= -f2- | head -1)
        if [[ -n "$disp" ]]; then
            export DISPLAY="$disp"
            return 0
        fi
    done
    export DISPLAY=":0"
}

detect_xauthority() {
    local path
    for path in \
        "${XAUTHORITY:-}" \
        "/run/user/$(id -u)/gdm/Xauthority" \
        "/run/user/$(id -u)/.mutter-Xwaylandauth."* \
        "$HOME/.Xauthority"
    do
        # shellcheck disable=SC2086
        if [[ -f $path ]]; then
            # shellcheck disable=SC2086
            export XAUTHORITY="$path"
            return 0
        fi
    done
}

detect_display
detect_xauthority