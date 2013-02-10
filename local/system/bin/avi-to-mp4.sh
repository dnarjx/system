#!/bin/bash
#
# Converts an AVI file to MP4 via 'ffmpeg'
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
    OUTPUT_FILE="${OUTPUT_FILE}/${INPUT_FILE%%.avi}.mp4"
fi

echo "Converting in=[${INPUT_FILE}] to out=[${OUTPUT_FILE}]..."

ffmpeg -i "${INPUT_FILE}" -s 432x320 -b 384k -vcodec libx264 -flags +loop+mv4 -cmp 256 -partitions +parti4x4+parti8x8+partp4x4+partp8x8+partb8x8 -subq 7 -trellis 1 -refs 5 -bf 0 -flags2 +mixed_refs -coder 0 -me_range 16 -g 250 -keyint_min 25 -sc_threshold 40 -i_qfactor 0.71 -qmin 10 -qmax 51 -qdiff 4 -acodec libfaac "${OUTPUT_FILE}"

#echo "Rebuilding index..."
#mv "${OUTPUT_FILE}" "${OUTPUT_FILE}.noidx"
#mencoder -forceidx -oac copy -ovc copy "${OUTPUT_FILE}.noidx" -o "${OUTPUT_FILE}"
#rm "${OUTPUT_FILE}.noidx"


