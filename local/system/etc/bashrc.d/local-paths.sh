#!/bin/bash
#
# Set up paths for 'local' execution directory
#

# System 'bin'
if [ ! -z "${SYSTEM_HOME}" ]; then
    SYSTEM_HOME_BIN="${SYSTEM_HOME}/bin"
    if [ -d ${SYSTEM_HOME_BIN} ]; then
        PATH=${SYSTEM_HOME_BIN}:${PATH}
    fi
fi

# Local 'bin'
if [ ! -z "${LOCAL_HOME}" ]; then
    LOCAL_HOME_BIN="${LOCAL_HOME}/bin"
    if [ -d ${LOCAL_HOME_BIN} ]; then
        PATH=${LOCAL_HOME_BIN}:${PATH}
    fi
fi

