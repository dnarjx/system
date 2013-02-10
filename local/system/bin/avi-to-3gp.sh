#!/bin/bash
#
# Converts an AVI file to 3GP via 'ffmpeg'
#

if [ ! -f "$1" ]; then
    echo "Missing or invalid input file path"
    exit 1
fi
INPUT_FILE=$1
shift

if [ -z "$1" ]; then
    echo "Missing output file path"
    exit 1
fi
OUTPUT_FILE=$1
shift

if [ -d ${OUTPUT_FILE} ]; then
    # Output file is a directory
    OUTPUT_FILE="${OUTPUT_FILE}/${INPUT_FILE%%.avi}.3gp"
fi

echo "Converting in=[${INPUT_FILE}] to out=[${OUTPUT_FILE}]..."

ffmpeg -i ${INPUT_FILE} -s qcif -vcodec h263 -acodec libfaac -ac 1 -ar 8000 -r 25 -ab 32 -y ${OUTPUT_FILE}

