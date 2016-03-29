import os
import time
import threading
import Queue
import json
import sys
import ctypes
import SocketServer
import time

def get_lexicon(word):
    print 'Getting the lexicon'
    #int LV_SRE_GetPhoneticPronunciation(const char* Words, const char* Language, int Index, char* PronunicationBuffer, int BufferLength)
    #SpeechPortReturnValue = LV.LV_SRE_LoadVoiceChannel(port, VOICE_CHANNEL, audio_buffer, audio_file_length, audio_format)
        #if (SpeechPortReturnValue != LV_SUCCESS):
    # c_char_p

    buffer_length = ctypes.c_int(12)
    pronounciation_buffer = ctypes.c_char_p('                         ')
    index = ctypes.c_int(0)
    language = ctypes.c_char_p('AmericanEnglish')
    word = ctypes.c_char_p(word)

    for i in range(2):
        index = ctypes.c_int(i)
        val = LV.LV_SRE_GetPhoneticPronunciation(word, language, index, pronounciation_buffer, buffer_length)
    	print (pronounciation_buffer).value


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
        out = open('S:\\steve_lucy\\speech_debug\\debug.txt', 'a')
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

    return word, prob

def init_lumenvox_api(ipaddr):    # Following translated from Lumenvox example by Gerry.  Steve removed explanatory blocks from this below.
    print 'debug: intializing LumenVox API'
    global port
    # Semaphore to serialize Lumenvox speech recognition because we only have a single port
    global LV_sema 
    global LV
    LV_sema = threading.BoundedSemaphore(value=1)
    LV.LV_SRE_Startup()
    grammar_label = 'bharathhsversion'        # just a label, for us.
    grammar_file = 'command3.grxml'     # put the two files.. the grxml s
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

LV = ctypes.CDLL("liblv_lvspeechport.so")
port = 0
ipaddr = '10.0.200.9'
init_lumenvox_api(ipaddr)    

'''
wavefilepaths = ['test2.wav', 'test2.wav', 'test2.wav', 'test2.wav', 'test2.wav', 'test2.wav', 'test2.wav', 'test2.wav']

for wavefilepath in wavefilepaths:
	audio_buffer = open(wavefilepath,'rb').read()
	word, prob = lumenvox_recognizer(audio_buffer)
	print word, prob
'''
get_lexicon('africa')

