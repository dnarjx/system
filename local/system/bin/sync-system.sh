#!/bin/bash
#
# Synchronizes specific system directories with a backup using "rsync"
#

# Setup basic environment
RSYNC=${RSYNC-`which rsync`}

# Read the destination folder
DEST=$1
shift

if [ -z "${DEST}" ]; then
    echo "Missing argument: destination directory"
    exit 1
fi

if [ ! -d ${DEST} ]; then
    echo "Creating destination directory [${DEST}]..."
    mkdir -p ${DEST}
    if [ 0 != $? ]; then
        echo "Error creating directory ($?)"
        exit 1
    fi
fi
echo "Using destination directory [${DEST}]"

# Functon to add a target to our source list
declare -a SOURCES

function append_source()
{
    if [ -z "$1" ]; then
        echo "append_source: Empty source!"
        exit 1
    fi

    if [ ! -r "$1" ]; then
        echo "append_source: Invalid source [$1]"
        exit 1
    fi

    echo "Adding source [`file \"$1\"`]"
    SOURCES=( ${SOURCES[@]} $1 )
}

append_source "/etc"
append_source "/home"

${RSYNC} -av ${SOURCES[@]} ${DEST}




