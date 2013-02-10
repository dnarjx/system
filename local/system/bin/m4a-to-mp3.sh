#!/bin/bash
#
# Dump m4a to mp3

WORKING_DIR=/tmp

while [ "$1" ]; do
	if [ -f "$1" ]; then
        MP3="${1%.m4a}.mp3"
        echo "Converting [$1] to [${MP3}]..."
        faad -o - "$1" | lame -h -v - "${1%.m4a}.mp3"
	fi
	shift
done

