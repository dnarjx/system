#!/bin/bash
#
# Join multiple movie files together
#

MENCODER=mencoder

# Local Variables
TFILE=

function usage()
{
  echo "Usage: movie-join.sh <outfile> <movies...>"
  echo
}

function cleanup()
{
  if [ ! -z "${TFILE}" ]; then
    echo "Removing temporary file [${TFILE}]"
    rm "${TFILE}"
    TFILE=
  fi
}

# Initialize traps
trap cleanup EXIT

# Argument #1: The output file
OUTFILE=$1
shift
if [ -z "${OUTFILE}" ]; then
  usage
  exit 1
fi

# Make sure all of the paths are valid
for P in $@; do
  if [ ! -f "$P" ]; then
    echo "Path [$1] does not exist!"
    usage
    exit 1
  fi
done

# Create a temporary file 
TFILE=`mktemp`
if [ ! -f "${TFILE}" ]; then
  echo "Failed to create temporary file [$?]"
  exit 1
fi

# Combine the movies together via regular "cat"
echo "Combining movies [$@] at [${TFILE}]"
cat $@ > ${TFILE}

# Join them together with 'mencoder'
${MENCODER} -forceidx -oac copy -ovc copy "${TFILE}" -o "${OUTFILE}"

# Make sure a file was created
if [ ! -f ${OUTFILE} ]; then
  echo "Failed to create output file!"
  exit 1
fi

exit 0
