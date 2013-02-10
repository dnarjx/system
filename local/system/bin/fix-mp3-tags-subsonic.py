#!/usr/bin/env python

"""Scans through song tags and fixes titles that Subsonic (application)
can't use"""

import os
import sys
import optparse
import logging
import unicodedata
import shutil
import mutagen

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger('tag-fix')

def normalize_string(s):
    nfkd_form = unicodedata.normalize('NFKD', unicode(s))
    normalized = u''.join(c for c in nfkd_form if not unicodedata.combining(c))
    return normalized.encode('ascii', 'replace')


def fix_tags(path):
    try:
        id3 = EasyID3(path)
    except ID3NoHeaderError:
        logger.info('File [%s] has no ID3 tag', path)
        id3 = EasyID3()

    changed = False
    for key in id3.valid_keys.keys():
        if not (key in id3):
            continue
        (value,) = id3[key]
        normalizedValue = normalize_string(value)
        if normalizedValue != value:
            logger.info('Found non-ASCII tag [%s] in [%s]: [%s]', 
                    key, path, value)
            id3[key] = normalizedValue
            changed = True

    if changed:
        id3.save(path)


def fix_path(path):
    # Convert the file's unicode path to ASCII
    asciiPath = normalize_string(path)
    if asciiPath != path:
        logger.info('Found non-ASCII path: [%s] => [%s]', path, asciiPath)
        shutil.move(path, asciiPath)
        return asciiPath
    return path


def fix_file(path):
    (root, ext) = os.path.splitext(path)
    if not ext.lower().endswith('.mp3'):
        logger.info('Skipping non-MP3: [%s]', path)
        return

    path = fix_path(path)

    # Update the ID3 tags
    try:
        fix_tags(path)
    except:
        logger.exception('Error while fixing tags for [%s]', path)


def fix_dir(dirPath):
    logger.debug('Entering directory: [%s]', dirPath)

    dirPath = fix_path(dirPath)

    for path in os.listdir(dirPath):
        path = os.path.join(dirPath, path)
        if os.path.isdir(path):
            fix_dir(path)
        elif os.path.isfile(path):
            fix_file(path)
        else:
            logger.debug('Skipping path: [%s]', dirPath)


def main():
    usage = '%prog [options] <source-directory>'
    parser = optparse.OptionParser(usage)
    parser.add_option('-d', '--debug', 
            action='store_true', dest='debug', default=False, 
            help='Enables debug-level logging')

    (opts, args) = parser.parse_args()

    if opts.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if len(args) != 1:
        logger.error('Invalid number of arguments')
        parser.print_usage()
        return 1
    (dirPath,) = args
    
    # Convert 'dirPath' to unicode
    fix_dir(unicode(dirPath))
    return 0


if __name__ == "__main__":
    sys.exit(main())

