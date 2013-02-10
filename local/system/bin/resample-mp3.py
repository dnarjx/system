#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import getopt
import subprocess
import threading
import types
import tempfile

import mutagen
import mutagen.id3
import mutagen.mp3
import mutagen.easyid3

class AudioFile(object):
    def __init__(self, path):
        self.path = path

    def getLameStream(self):
        raise NotImplementedError

    def getLameArgs(self):
        return []

    def getLameFilename(self):
        # Default to just the original name with 'mp3' on the end
        (root, ext) = os.path.splitext(os.path.basename(self.path))
        return '%s.%s' % (root, 'mp3')

    def getMutagenFile(self):
        return mutagen.File(self.path)


class CompatibleAudioFile(AudioFile):
    
    def getLameInput(self):
        fd = open(self.path, 'rb')
        data = fd.read()
        fd.close()
        return data


class Mp3AudioFile(CompatibleAudioFile):
    
    def getLameArgs(self):
        return ['--mp3input']


class FlacAudioFile(AudioFile):
   
    def getLameInput(self):
        print "Decoding FLAC '%s'..." % self.path
        proc = subprocess.Popen( 
            ['flac', '-s', '-c', '-d', self.path], 
            stdout=subprocess.PIPE )

        data = proc.stdout.read()
        proc.wait()
        del(proc)
        return data
	
class M4aAudioFile(AudioFile):

    def getLameInput(self):
	print "Decoding M4A '%s'..." % self.path
	
	# Create a temporary file for 'mplayer' to use
	tmp = tempfile.NamedTemporaryFile(suffix='.wav')
	
	proc = subprocess.Popen(
	    ['mplayer', '-ao', 'pcm', self.path, 
	     '-ao', 'pcm:file=%s' % tmp.name ] )
	proc.wait()
	del(proc)
	
	# Now, read the data from the temporary file
	tmp.seek(0)
	data = tmp.read()
	tmp.close()
	return data


class TranscoderThread(threading.Thread):
    def __init__(self, sem, text, handler, basedir):
        threading.Thread.__init__(self)
        self.sem = sem
        self.text = text
        self.handler = handler
        self.basedir = basedir

    def run(self):
        print "Processing '%s' (%s)" % (self.handler.path, self.text)
        process(self.handler, self.basedir)
        sem.release()

    def __str__(self):
        return "Transcoder(%s)" % self.text


RESAMPLE_EXTENSIONS = {
    'wav': CompatibleAudioFile,
    'mp3': Mp3AudioFile, 
    'flac': FlacAudioFile,
    'm4a': M4aAudioFile,
    } 


def getHandler(path):
    ext = os.path.splitext(path)[1].lower()
    if ext.startswith('.'):
        ext = ext[1:]
    
    if ext in RESAMPLE_EXTENSIONS:
        return RESAMPLE_EXTENSIONS[ext](path)
    return None

def parseFile(path):
    result = []
    
    if os.path.isdir(path):
        for name in os.listdir(path):
            result += parseFile(os.path.join(path,name))
    else:
        handler = getHandler(path)
        if handler != None:
            result.append(handler)
    
    return result
    
def copyTags(sourceHandler, destPath):
    source = sourceHandler.getMutagenFile()
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
        dest.update(source)
    else:
        # On a key-by-key basis, translate to text ID3 tags
        for key in source.keys():
            if key in mutagen.easyid3.Open.valid_keys:
                frameName = mutagen.easyid3.Open.valid_keys[key]
                frameClass = mutagen.id3.Frames[frameName]

                if not issubclass(frameClass, mutagen.id3.TextFrame):
                    print "Skipping frame '%s'; not a text frame" % frameName

                values = source[key]
                if isinstance(values, types.StringTypes):
                    values = [value]

                for value in values:
                    frame = frameClass(encoding=3, text=value)
                    dest.tags.add(frame)

    dest.save()
    
    del(source)
    del(dest)
    
def process(handler, basedir):
    filename = os.path.basename(handler.path)
    print "Processing '%s'..." % filename
    resampleDir = os.path.join(basedir,os.path.dirname(handler.path))
    resamplePath = os.path.join(resampleDir, handler.getLameFilename())
    
    try:
        os.makedirs(resampleDir)
    except os.error:
        pass
    
    # Get the lame stream from the handler
    lameData = handler.getLameInput()
    if lameData == None:
        print "ERROR: LAME input data is empty for '%s'!" % filename
        return

    lameArgs = [ 'lame', '-S', '-v' ]
    args = handler.getLameArgs()
    if args != None:
        lameArgs += args
    lameArgs += ['-', resamplePath]

    lameProc = subprocess.Popen(
        lameArgs, 
        stdin=subprocess.PIPE )

    try:
        lameProc.stdin.write(lameData)
        lameProc.stdin.close()
        lameProc.wait()
    except IOError, inst:
        print "IOError while processing '%s': %s'" % (filename, inst)
        return

    copyTags(handler, resamplePath)
    
    print "Resampled '%s': %d --> %d" % \
        (filename, os.path.getsize(handler.path), 
         os.path.getsize(resamplePath))
    
if __name__ == '__main__':
    try:
        opts, args = getopt.getopt( sys.argv[1:], "o:", ["output="] )
    except getopt.GetoptError, inst:
        print str(inst)
        sys.exit(1)

    output = "./Resample"
    for o, a in opts:
        if o in ( '-o', '--output' ):
            output = a
        else:
            assert False, "unhandled option '%s'" % o

    handlerList = []
    for path in args:
        handlerList += parseFile(path)

    NUM_THREADS = 2
    sem = threading.Semaphore(NUM_THREADS)
        
    print "Resampling %i files..." % len(handlerList)
    for i in range(len(handlerList)):
        path = handlerList[i]
        text = '%i / %i' % ((i+1), len(handlerList))
        sem.acquire()
        t = TranscoderThread(sem, text, path, output)
        t.start()
        
