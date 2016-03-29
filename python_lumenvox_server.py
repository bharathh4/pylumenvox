import os
from flask import Flask, request, redirect, url_for
from werkzeug import secure_filename
import shutil


import time
import threading
import Queue
import json
import sys
import ctypes
import SocketServer

UPLOAD_FOLDER = 'uploads'
UPLOAD_FOLDER_GRAMMAR = 'grammars'
ALLOWED_EXTENSIONS = set(['wav', 'grxml', 'txt'])
GRAMMAR_DIR = 'grammars'
NAMES_DIR = 'names'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

LV = ctypes.CDLL("liblv_lvspeechport.so")
port = 0
ipaddr = '10.0.200.9'
#grammar_file = os.path.join(GRAMMAR_DIR, 'command.grxml')
#init_lumenvox_api(ipaddr, grammar_file)  

def lumenvox_recognizer(audio_buffer):  # This version writes phonemes and match alternatives to a file
    audio_format = 1
    LV_SUCCESS = 0
    VOICE_CHANNEL = 1
    LV_ACTIVE_GRAMMAR_SET = -1
    LV_DECODE_BLOCK = 2
    audio_file_length = len(audio_buffer)
    prob = 0
    sentence = 'No response received'
    word = 'Error'
    LV_sema.acquire()
    alternatives = []
    try:                                # put the whole deal inside the semaphore in a try except block to ensure the semaphore always gets released no matter what
        SpeechPortReturnValue = LV.LV_SRE_LoadVoiceChannel(port, VOICE_CHANNEL, audio_buffer, audio_file_length, audio_format)
        if (SpeechPortReturnValue != LV_SUCCESS):
            print "Failed to load voice channel with audio data %s", ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value
            raise Exception('get outta here')
        SpeechPortReturnValue = LV.LV_SRE_Decode(port, VOICE_CHANNEL, LV_ACTIVE_GRAMMAR_SET, LV_DECODE_BLOCK )
        if (SpeechPortReturnValue < LV_SUCCESS):
            print "Decode failed with error string '%s'." % ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value                       
            raise Exception('get outta here')
        NumberOfNBestFromASR = LV.LV_SRE_GetNumberOfNBestAlternatives(port, VOICE_CHANNEL)
        if NumberOfNBestFromASR == 0:
            print "No possible answers, please verify that the grammar contains a possible result"
            raise Exception('get outta here')
        t = time.asctime()
        master_data = []
        out = open('bharath\\speech_debug\\debug.txt', 'a')
        for i in range(NumberOfNBestFromASR):
            SpeechPortReturnValue = LV.LV_SRE_SwitchToNBestAlternative(port, VOICE_CHANNEL, i)
            if (SpeechPortReturnValue != LV_SUCCESS):
                print "Unable to use alternative"
                raise Exception('get outta here')
            sentence = ctypes.c_char_p(LV.LV_SRE_GetInterpretationString(port, VOICE_CHANNEL, i)).value
            prob = LV.LV_SRE_GetInterpretationScore(port, VOICE_CHANNEL, i) / 10
            phonemes = ctypes.c_char_p(LV.LV_SRE_GetInterpretationPhonemes(port, VOICE_CHANNEL, i)).value
            data = [t, str(i), sentence, str(prob), phonemes]
            alternatives.append(data)
            master_data.append((str(i), sentence, str(prob), phonemes))
            out.write('\t'.join(data)+'\n')
    except Exception as ex:
        print 'Lumenvox Exception: %s' % ex.message
    finally:
        LV_sema.release()

    if alternatives:
        first = alternatives[0]
        sentence, prob = first[2], first[3]

    if sentence is not None:
        word = sentence.strip().replace('{', '').replace('}', '').replace(',', ' ').lower()
    
    return word, prob, {'extras': master_data}

def get_lexicon(word):
    print 'Getting the lexicon'
    #int LV_SRE_GetPhoneticPronunciation(const char* Words, const char* Language, int Index, char* PronunicationBuffer, int BufferLength)
    #SpeechPortReturnValue = LV.LV_SRE_LoadVoiceChannel(port, VOICE_CHANNEL, audio_buffer, audio_file_length, audio_format)
        #if (SpeechPortReturnValue != LV_SUCCESS):
    # c_char_p

    buffer_length = ctypes.c_int(250)
    pronounciation_buffer = ctypes.c_char_p('                                                        ')
    language = ctypes.c_char_p('AmericanEnglish')
    word = ctypes.c_char_p(word)

    lexicon_list = []
    for i in range(6):
        index = ctypes.c_int(i)
        val = LV.LV_SRE_GetPhoneticPronunciation(word, language, index, pronounciation_buffer, buffer_length)
    	print (pronounciation_buffer).value.rstrip()
        lexicon_list.append(pronounciation_buffer.value.rstrip())
    return filter(lambda x : x is not '', lexicon_list)
    

def init_lumenvox_api(ipaddr, grammar_file):    # Following translated from Lumenvox example by Gerry.  Steve removed explanatory blocks from this below.
    print 'debug: intializing LumenVox API'
    global port
    # Semaphore to serialize Lumenvox speech recognition because we only have a single port
    global LV_sema 
    global LV
    LV_sema = threading.BoundedSemaphore(value=1)
    LV.LV_SRE_Startup()
    grammar_label = 'bharathhsversion'        # just a label, for us.
    #grammar_file = 'command3.grxml'     # put the two files.. the grxml s
    OpenErrorCode = 0
    LV_SUCCESS = 0
    PROP_EX_TARGET_PORT = 1
    PROP_EX_SAVE_SOUND_FILES = 2
    PROP_EX_VALUE_TYPE_INT = 1
    PROP_EX_MAX_NBEST_RETURNED = 16
    PROP_EX_DECODE_TIMEOUT = 17
    PROP_EX_SRE_SERVERS = 4
    PROP_EX_VALUE_TYPE_STRING = 3
    PROP_EX_TARGET_CLIENT = 4
    PROP_EX_LICENSE_SERVERS = 33
    SpeechPortReturnValue = LV.LV_SRE_SetPropertyEx(None, PROP_EX_LICENSE_SERVERS, PROP_EX_VALUE_TYPE_STRING, ctypes.c_char_p(ipaddr), PROP_EX_TARGET_CLIENT, 0)
    if (SpeechPortReturnValue != LV_SUCCESS):
        print "Failed to set License Server IP Address %i %s" % (SpeechPortReturnValue,ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value)
        sys.exit()    
    SpeechPortReturnValue = LV.LV_SRE_SetPropertyEx(None, PROP_EX_SRE_SERVERS, PROP_EX_VALUE_TYPE_STRING, ctypes.c_char_p(ipaddr), PROP_EX_TARGET_CLIENT, 0)
    if (SpeechPortReturnValue != LV_SUCCESS):
        print "Failed to set SRE Server IP Address %i %s" % (SpeechPortReturnValue,ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value)
        sys.exit()    
    port = LV.LV_SRE_CreateClient(OpenErrorCode, None, None, 0)    
    if (port == None):
        print "Port encountered a problem while opening" 
        print "%s" % ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(OpenErrorCode)).value
        sys.exit()
    SpeechPortReturnValue = LV.LV_SRE_SetPropertyEx(port, PROP_EX_SAVE_SOUND_FILES, PROP_EX_VALUE_TYPE_INT, 1, PROP_EX_TARGET_PORT, 0)
    if (SpeechPortReturnValue != LV_SUCCESS):
        print "Failed to set property to the speech port : %i %s" % (SpeechPortReturnValue, ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value)
        sys.exit()  		
    SpeechPortReturnValue = LV.LV_SRE_SetPropertyEx(port, PROP_EX_MAX_NBEST_RETURNED, PROP_EX_VALUE_TYPE_INT, 1, PROP_EX_TARGET_PORT, 0)
    if (SpeechPortReturnValue != LV_SUCCESS):
        print "Failed to set property to the speech port : %s" % ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value
        sys.exit() 
    SpeechPortReturnValue = LV.LV_SRE_SetPropertyEx(port, PROP_EX_DECODE_TIMEOUT, PROP_EX_VALUE_TYPE_INT, 100000, PROP_EX_TARGET_PORT, 0)
    if (SpeechPortReturnValue != LV_SUCCESS ):
        print "Failed to set property to the speech port : %s" % ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value
        sys.exit()
    print 'Loading %s' % grammar_file	
    SpeechPortReturnValue = LV.LV_SRE_LoadGrammar(port, grammar_label, grammar_file)
    if (SpeechPortReturnValue != LV_SUCCESS):
        print "Failed to load the grammar into the ASR"
        print "%s" % ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value
        sys.exit()
    SpeechPortReturnValue = LV.LV_SRE_ActivateGrammar(port, grammar_label)
    if (SpeechPortReturnValue != LV_SUCCESS):
        print "Failed to activate the grammar"
        print "%s" % ctypes.c_char_p(LV.LV_SRE_ReturnErrorString(SpeechPortReturnValue)).value
        sys.exit()        
    print 'debug: LumenVox API initialization successful'    

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/stop', methods=['GET'])
def stop_lumenvox():
    global LV
    global port
    value = LV.LV_SRE_DestroyClient(port)
    return str(value) + 'Lumenvox port stopped'


@app.route('/start', methods=['GET'])
def start_lumenvox():
    global ipaddr
    grammar_file = os.path.join(GRAMMAR_DIR, 'command.grxml')
    init_lumenvox_api(ipaddr, grammar_file)  
    return 'Lumenvox started'  
    
@app.route('/upload_grammar', methods=['GET', 'POST'])
def upload_grammar():
    if request.method == 'POST':
        file = request.files['file']
        #grammar_file = request.files['grammar_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(GRAMMAR_DIR, filename))
	return 'Grammar uploaded'

@app.route('/upload_names', methods=['GET', 'POST'])
def upload_names():
    if request.method == 'POST':
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(NAMES_DIR, filename))

	with open(os.path.join(NAMES_DIR, filename), 'r') as f:
	    words = [line.rstrip() for line in f]
	    #return str(words)

	names_lexicon = []    	
        for word in words:
	    lexicons = get_lexicon(word)
	    names_lexicon.append((word, lexicons))
	return str(names_lexicon)
        
@app.route('/delete_grammars', methods=['GET'])
def delete_grammar():
    filepaths = [os.path.join(GRAMMAR_DIR, filename) for filename in os.listdir(GRAMMAR_DIR)]
    for filepath in filepaths:
	os.unlink(filepath)
    return 'All grammars deleted'
	

@app.route('/recognize', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        #grammar_file = request.files['grammar_file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	    #grammar_filename = secure_filename(grammar_file.filename)	    
	    #grammar_file.save(os.path.join(app.config['UPLOAD_FOLDER_GRAMMAR '], grammar_filename))

	    wavefilepath = os.path.join('uploads', filename)
	    audio_buffer = open(wavefilepath,'rb').read()
	    word, prob, extra_info = lumenvox_recognizer(audio_buffer)

	    return str((word, prob, extra_info))

@app.route('/lexicon/<word>', methods=['GET'])
def get_lexicon_for_client(word):
	lexicons = get_lexicon(word)
	return str(lexicons)

if __name__ == '__main__':
    app.run(debug=True)
