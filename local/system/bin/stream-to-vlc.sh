#!/bin/bash

if [ ! -z "$1" ]; then
    STR_PATH=$1; shift
else
    echo "ERROR: You must specify a path to stream"
    exit 1
fi

STR_PORT=12345
if [ ! -z $1 ]; then
    STR_PORT="$1"; shift
fi

echo "Connect to this stream using 'http://localhost:$STR_PORT'"
read -p "Press any key to start..."

cvlc "$STR_PATH" --sout "#transcode{vcodec=VP80,vb=800,scale=1,acodec=vorbis,ab=128}:std{access=http,mux=ffmpeg{mux=webm},dst=localhost:$STR_PORT}" 
#cvlc -vv "$STR_PATH" --sout "#std{access=http,mux=ogg,dst=localhost:$STR_PORT}" 

