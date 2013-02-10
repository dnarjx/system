#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, types, string, threading
import optparse
import subprocess
import logging
import StringIO
import mutagen, mutagen.id3, mutagen.mp3, mutagen.mp4, mutagen.ogg
import mutagen.easyid3

THREAD_MAX = 3

class AudioFile(object):
    def __init__(self, path, t):
        self.path = path
        self.t = t

        if not os.path.exists(self.path):
            raise Exception, "AudioFile created from non-existent path [%s]" % \
                self.path

    def getMutagenFile(self):
        return mutagen.File(self.path)

    def convert(self, v):
        raise NotImplementedError


class Mp3CompatibleAudioFile(AudioFile):

    def getRawStream(self):
        raise NotImplementedError

    def getLameFilename(self):
        # Default to just the original name with 'mp3' on the end
        (root, ext) = os.path.splitext(self.path)
        return '%s.%s' % (root, 'mp3')

    def convert(self, v):
        (root, ext) = os.path.splitext(self.path)
        outpath = self.getLameFilename()

        logging.info("Converting %s [%s] to MP3 [%s]...", \
            self.t, self.path, outpath)
        if os.path.exists(outpath):
            logging.warning("Output path [%s] already exists!", outpath)
            v.deletePath(outpath)

        logging.info("Converting [%s] to [%s]...", self.path, outpath)
        if v.isSimulation():
            return

        src = self.getRawStream(v)
        args = ['lame', '-h', '-v', '-', outpath]
        lame = subprocess.Popen(args, stdin=src)
        lame.wait()

        src.close()

        if lame.returncode != 0:
            logging.error( "Recieved return code [%d] after conversion!", \
            lame.returncode )
            return
        
        # Copy the original tags over, if possible
        self.copyTagsTo(outpath, v)

        # Delete the original file
        v.deletePath(self.path)
      

    def copyTagsTo(self, destPath, v):
        source = self.getMutagenFile()
        logging.debug("Using 'mutagen' source object [%s]", str(source))
        
        if not v.isSimulation():
            if not os.path.exists(destPath):
                raise Exception, "Destination path [%s] does not exist!" % \
                        destPath
        
        dest = mutagen.mp3.MP3(destPath)
        try:
            dest.add_tags()
            dest.delete()
        except mutagen.id3.error:
            # Already has tags
            pass

        # Add any tags that are supported
        if source == None:
            logging.debug("No tag source provided!")
        elif isinstance(source, mutagen.mp3.MP3):
            # Copy directly from the source to the destination
            logging.debug( "Copying tags from MP3 to MP3..." )
            if not v.isSimulation():
                dest.update(source)
        else:
            # On a key-by-key basis, translate to text ID3 tags
            for key in source.keys():
                id3Key = self.translateTagKey(key)

                if id3Key in mutagen.easyid3.Open.valid_keys:
                    frameName = mutagen.easyid3.Open.valid_keys[id3Key]
                    if not frameName in mutagen.id3.Frames:
                        continue

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
                        if not v.isSimulation():
                            dest.tags.add(frame)

        if not v.isSimulation():
            dest.save()
        del(dest)
        del(source)

    def translateTagKey(self, key):
        # Default implementation: no translation
        return key


class FlacAudioFile(Mp3CompatibleAudioFile):
    def __init__(self, path):
        super(FlacAudioFile, self).__init__(path, 'FLAC')

    def getRawStream(self, v):
        args = ['flac']
        if not v.isVerbose():
            args.append('-s')
        args += ['-c', '-d', self.path]

        flac = subprocess.Popen(args, stdout=subprocess.PIPE)    
        return flac.stdout

class WavAudioFile(Mp3CompatibleAudioFile):
    def __init__(self, path):
        super(WavAudioFile, self).__init__(path, 'WAV')

    def getRawStream(self, v):
        return open(self.path, 'r')


class M4aAudioFile(Mp3CompatibleAudioFile):
    KEY_TRANSLATIONS = { \
        '\xa9alb': 'album', '\xa9nam': 'title', '\xa9ART': 'artist', \
        '\xa9wrt': 'composer', '\xa9gen': 'genre' }
      
    def __init__(self, path):
        super(M4aAudioFile, self).__init__(path, 'M4A')

    def getRawStream(self, v):
        args = ['faad']
        if not v.isVerbose():
            args.append('-q')
        args += ['-o', '-', self.path]

        faad = subprocess.Popen(args, stdout=subprocess.PIPE)    
        return faad.stdout

    def translateTagKey(self, key):
        if key in M4aAudioFile.KEY_TRANSLATIONS:
            return M4aAudioFile.KEY_TRANSLATIONS[key]
        else:
            return key


class OggAudioFile(Mp3CompatibleAudioFile):
    def __init__(self, path):
        super(OggAudioFile, self).__init__(path, 'OGG')

    def getRawStream(self, v):
        args = ['oggdec']
        if not v.isVerbose():
            args.append('-Q')
        args += ['-o', '-', self.path]

        oggdec = subprocess.Popen(args, stdout=subprocess.PIPE)
        return oggdec.stdout
    

class FileProcessorThread(threading.Thread):
    VALID_EXTENSIONS = {
        'mp3': None,
        'wav': WavAudioFile,
        'flac': FlacAudioFile,
        'm4a': M4aAudioFile,
        'ogg': OggAudioFile,
        }

    def __init__(self, v, path):
        super(FileProcessorThread, self).__init__()
        self.v = v
        self.sem = None
        self.path = path

    def setSem(self, sem):
        self.sem = sem

    def run(self):
        self.process()

        # Release the semaphore
        if self.sem != None:
            self.sem.release()

    def process(self):
        # Parse the path name
        base = os.path.basename(self.path)
        (root, ext) = os.path.splitext(base)
        logging.debug("Basename=[%s]; root=[%s]; ext=[%s];", base, root, ext)

        ext = ext.lower()[1:]
        if ext in FileProcessorThread.VALID_EXTENSIONS:
            convType = FileProcessorThread.VALID_EXTENSIONS[ext]
            if convType != None:
                conv = convType(self.path)

                # Run the converter
                logging.info("Running converter [%s] on file [%s]...", \
                    conv.t, self.v.nameForPath(self.path))
                conv.convert(self.v)
        else:
            self.v.deletePath(self.path)


class Validator(object):
  
    def __init__(self):
        self.fullPaths = False
        self.preserveFiles = False
        self.verbose = False
    
    def isSimulation(self):
        raise NotImplementedError
        
    def setVerbose(self, value):
        self.verbose = value
        
    def setFullPaths(self, value):
        self.fullPaths = value
        
    def setPreserveFile(self, value):
        self.preserveFiles = value
        
    def isFullPaths(self):
        return (self.fullPaths)

    def isVerbose(self):
        return (self.verbose)
        
    def isPreservingFiles(self):
        return self.preserveFiles

    def operate(self, files, threads=1):
        if type(files) in types.StringTypes:
            # Turn a single string into a list
            files = [files]

        # Build the thread list
        threadList = []
        for f in files:
            if not os.path.exists(f):
                logging.warning("Provided path [%s] does not exist!", f)
                continue
            elif os.path.isfile(f):
                threadList += self.buildThread(f)
            else:
                threadList += self.processDir(f)

        logging.debug("Validating over %d threads...", threads)
        sem = threading.Semaphore(threads)
        for t in threadList:
            sem.acquire()
            t.setSem(sem)
            if threads > 1:
                t.start()
            else:
                t.run()
    

    def processDir(self, d):
        logging.debug( "Processing directory [%s]...", d)

        threads = []
        for (dirpath, dirnames, filenames) in os.walk(d):
            for name in filenames:
                path = os.path.join(dirpath, name)
                threads += self.buildThread(path)

        return threads

    def buildThread(self, path):
        logging.debug( "Processing path [%s]", path )

        # Expand and resolve the path
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            logging.error("Unknown file type for [%s]", path)
            return []

        return [FileProcessorThread(self, path)]
      
    def deletePath(self, path):
        if not self.isPreservingFiles():
            logging.info("Deleting file: [%s]", self.nameForPath(path))
            if not self.isSimulation():
                os.remove(path)

    def nameForPath(self, path):
        if self.isFullPaths():
            return path
        else:
            return os.path.basename(path)
            

class SimulatedValidator(Validator):
    
    def isSimulation(self):
        return True
        

class RealValidator(Validator):
    
    def isSimulation(self):
        return False
  
def main():
    usage = '%prog: [options] dirs...'
    parser = optparse.OptionParser(usage)
    
    parser.add_option('-v', '--verbose', \
            action='store_true', dest='verbose', default=False, \
            help='Enables verbose debug output')
    parser.add_option('-g', '--go', \
            action='store_true', dest='go', default=False, \
            help='Performs real file operations, as opposed to simulated')
    parser.add_option('-f', '--full', \
            action='store_true', dest='full', default=False, \
            help='Prints full pathnames (as opposed to the file name)')
    parser.add_option('-p', '--preserve', \
            action='store_true', dest='preserve', default=False, \
            help='Causes no files to be deleted')
    parser.add_option('-t', '--threads', metavar='COUNT', \
            action='store', dest='threads', default=1, \
            help='Distributes processing among COUNT threads')
            
    (opts, args) = parser.parse_args()
    
    # Bump up the logging if we're using verbose
    if opts.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    
    if len(args) == 0:
        logging.error( "You must specify at least one file to process!" )
        parser.print_usage()
        sys.exit(1)
        
    logging.debug( "Operating on files: %s", ','.join(args) )

    if not opts.go:
        logging.warning( "This is a simulated run; " \
                "use the '-g' option to operate!" )

    if opts.go:
        v = RealValidator()
    else:
        v = SimulatedValidator()
        
    # Configure the instance
    v.setFullPaths(opts.full)
    v.setPreserveFile(opts.preserve)
    v.setVerbose(opts.verbose)
    
    v.operate(args, threads=int(opts.threads))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
