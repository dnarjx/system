#!/bin/bash

if [ ! -z $1 ]; then
    STR_PATH=$1; shift
else
    echo "ERROR: You must specify a path to stream"
    exit 1
fi

STR_PORT=12345
if [ ! -z $1 ]; then
    STR_PORT="$1"; shift
fi

echo "Connect to this stream using 'mms://localhost:$STR_PORT'"
read -p "Press any key to start..."

cvlc -vv "$STR_PATH" --sout "#transcode{vcodec=DIV3,vb=512,scale=1,acodec=mp3,ab=48,channels=2}:std{access=mmsh,mux=asfh,dst=localhost:$STR_PORT}" -vv

