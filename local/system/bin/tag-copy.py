#!/usr/bin/python

import os, sys, optparse, logging, types
import mutagen, mutagen.id3, mutagen.mp3, mutagen.mp4, mutagen.ogg
import mutagen.easyid3

__all__ = ['TagCopyError', 'copyTags']

class TagCopyError(Exception):
    pass

M4A_TRANSLATIONS = { \
    '\xa9alb': 'album', '\xa9nam': 'title', '\xa9ART': 'artist', \
    '\xa9wrt': 'composer', '\xa9gen': 'genre' }


def copyTags(sourcePath, destPath):
    # Make sure the files are valid
    for f in (sourcePath, destPath):
        if not os.path.isfile(f):
            raise TagCopyError("File [%s] is invalid", f)
    
    source = mutagen.File(sourcePath)
    logging.debug("Using 'mutagen' source object [%s]", str(source))

    dest = mutagen.mp3.MP3(destPath)
    try:
        dest.add_tags()
        dest.delete()
    except mutagen.id3.error:
        # Already has tags
        pass

    # Add any tags that are supported
    if isinstance(source, mutagen.mp3.MP3):
        # Copy directly from the source to the destination
        copyTagsDirect(source, dest)
    else:
        copyTagsTranslate(source, dest)

    dest.save()
    del(dest)
    del(source)


def copyTagsDirect(source, dest):
    logging.debug( "Copying tags from MP3 to MP3..." )
    dest.update(source)


def copyTagsTranslate(source, dest):
    # On a key-by-key basis, translate to text ID3 tags
    for key in source.keys():
        id3Key = translateTagKey(source, key)

        if id3Key in mutagen.easyid3.Open.valid_keys:
            frameName = mutagen.easyid3.Open.valid_keys[id3Key]
            frameClass = mutagen.id3.Frames[frameName]

            if not issubclass(frameClass, mutagen.id3.TextFrame):
                logging.debug("Skipping frame '%s'; not a text frame", \
                        frameName)
                continue

            values = source[key]
            if isinstance(values, types.StringTypes):
                values = [value]

            for value in values:
                frame = frameClass(encoding=3, text=value)
                logging.debug("Appending frame [%s] = [%s]", \
                        frameName, str(frame))
                dest.tags.add(frame)
    

def translateTagKey(obj, key):
    if isinstance(obj, mutagen.mp4.MP4):
        tdict = M4A_TRANSLATIONS
    else:
        tdict = None

    if (tdict != None) and (key in tdict):
        return tdict[key]
    return key


def main():
    usage = 'Usage: %prog [options] <source-file> <dest-file>'
    parser = optparse.OptionParser(usage)

    parser.add_option('-d', '--debug', \
            action='store_true', dest='debug', default=False, \
            help='Enable debug logging')

    (options, args) = parser.parse_args()

    # Handle the 'debug' flag
    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle the arguments
    if len(args) != 2:
        logging.error("Incorrect number of arguments (%d)", len(args))
        parser.print_usage()
        sys.exit(2)
    (sourcePath, destPath) = args
    
    # Perform the copy    
    copyTags(sourcePath, destPath)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    try:
        main()
    except TagCopyError, e:
        logging.error("TagCopyException caught: %s", e)
        sys.exit(1)
    sys.exit(0)

