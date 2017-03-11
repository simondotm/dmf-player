#!/usr/bin/env python
# python script to convert & process DMF files for SN76489 PSG
# by simondotm 2017
# Released under MIT license

# http://deflemask.com/DMF_SPECS.txt


import zlib
import struct
import sys
import binascii
import math
from os.path import basename

if (sys.version_info > (3, 0)):
	from io import BytesIO as ByteBuffer
else:
	from StringIO import StringIO as ByteBuffer




#-----------------------------------------------------------------------------


class FatalError(Exception):
	pass




class DmfStream:


    dmf_filename = ''

    # constructor - pass in the filename of the DMF
    def __init__(self, dmf_filename):

        self.dmf_filename = dmf_filename
        print "  Loading DMF file : '" + dmf_filename + "'"

        # open the dmf file and parse it
        dmf_file = open(dmf_filename, 'rb')
        dmf_data = dmf_file.read()

        # Store the DMF data and validate it
        self.dmf_data = ByteBuffer(dmf_data)

        dmf_file.close()

        self.dmf_data.seek(0)
        unpacked = zlib.decompress(dmf_data)
        self.dmf_data = ByteBuffer(unpacked)
        self.dmf_data.seek(0, 2)
        size = self.dmf_data.tell()
        self.dmf_data.seek(0)
        print "  DMF file loaded : '" + dmf_filename + "' (" + str(size) + " bytes)"

        bin_file = open("dmf.bin", 'wb')
        bin_file.write(unpacked)
        bin_file.close()


    def parse(self):
        # Save the current position of the VGM data
        original_pos = self.dmf_data.tell()




        # Seek to the start of the file
        self.dmf_data.seek(0)

        data = self.dmf_data.read(16)

        header = data.decode("utf-8") 
        #header = struct.unpack( 's', data )
        print header

        # Perform basic validation on the given file by checking for the header
        if header != ".DelekDefleMask.":
        	# Could not find the header string
            print "ERROR: not a DMF file"
            return


        def getByte():
            return struct.unpack('B', self.dmf_data.read(1) )[0]

        def getShort():
            return struct.unpack('H', self.dmf_data.read(2) )[0]

        def getInt():
            return struct.unpack('i', self.dmf_data.read(4) )[0]

        def getString(size):
            s = self.dmf_data.read(size)
            return s.decode("utf-8") 

        def skipBytes(n):
            self.dmf_data.read(n)

        version = getByte()
        print " DMF version - " + str(version)
        if version != 24:
            print "ERROR: can only parse DMF version 24 (Deflemask v12)"
            return

        system = getByte()
        print " DMF system - " + str(system)
        # must be 3 - this script only parses SMS tunes (SYSTEM_TOTAL_CHANNELS=4)
        if system != 3:
            print "ERROR: Not an SMS DMF track"
            return

        #//VISUAL INFORMATION
        song_name = getString( getByte() )
        song_author = getString( getByte() )

        highlight_A = getByte()
        highlight_B = getByte()

        #//MODULE INFORMATION
        time_base = getByte()
        tick_time_1 = getByte()
        tick_time_2 = getByte()
        frames_mode = getByte() # (0 = PAL, 1 = NTSC)
        custom_hz = getByte() # (If set to 1, NTSC or PAL is ignored)
        custom_hz_1 = getByte()
        custom_hz_2 = getByte()
        custom_hz_3 = getByte()

        total_rows_per_pattern = getInt()
        total_rows_in_pattern_matrix = getByte()



        print "Song name: " + song_name
        print "Song author: " + song_author
        print "Time base: " + str(time_base)
        print "total_rows_per_pattern " + str(total_rows_per_pattern)
        print "total_rows_in_pattern_matrix " + str(total_rows_in_pattern_matrix)


        SYSTEM_TOTAL_CHANNELS = 4


        pattern_size_0 = total_rows_per_pattern
        pattern_size_n = total_rows_per_pattern*2+total_rows_per_pattern
        pattern_size_t = pattern_size_0+pattern_size_n*3
        print "size of VGM pattern " + str(pattern_size_t) + " bytes"

        total_size_t = total_rows_in_pattern_matrix * pattern_size_t * SYSTEM_TOTAL_CHANNELS
        print "size of VGM song " + str(total_size_t) + " bytes"
        


        pattern_matrix_array = []
        #//PATTERN MATRIX VALUES (A matrix of SYSTEM_TOTAL_CHANNELS x TOTAL_ROWS_IN_PATTERN_MATRIX)        
        for c in range(0, SYSTEM_TOTAL_CHANNELS):
            print "Reading channel " + str(c) + " pattern matrix (" + str(total_rows_in_pattern_matrix) + " rows)"
            pattern_matrix = bytearray()
            o = ""
            for r in range(0, total_rows_in_pattern_matrix):
                pattern_id = getByte()
                o += " " + str(pattern_id)
                pattern_matrix.append( struct.pack('B', pattern_id) )	
            print o
            pattern_matrix_array.append(pattern_matrix)

        #//INSTRUMENTS DATA (.DMP format is similar to this part, but there are some discrepancies, please read DMP_Specs.txt for more details)

        total_instruments = getByte()

        print "total_instruments " + str(total_instruments)

        for i in range(0, total_instruments):
            print "Reading instrument " + str(i)

            instrument_name = getString( getByte() )
            print " instrument_name '" + instrument_name + "'"

            instrument_mode = getByte() # (0 = STANDARD INS, 1 = FM INS)
            if instrument_mode != 0:
                print "ERROR: FM instruments not supported on SMS"
                # todo, should skip remaining data
            
            else:

                #//VOLUME MACRO
                envelope_size = getByte() #                1 Byte: ENVELOPE_SIZE (0 - 127)
                print "  volume envelope size " + str(envelope_size)
                # Repeat this ENVELOPE_SIZE times
                for e in range(0, envelope_size):
                    envelope_value = getInt()  #                    4 Bytes: ENVELOPE_VALUE
                if envelope_size > 0:
                    loop_position = getByte() #         1 Byte: LOOP_POSITION (-1 = NO LOOP)

                #//ARPEGGIO MACRO
                envelope_size = getByte() #                1 Byte: ENVELOPE_SIZE (0 - 127)
                print "  arpeggio envelope size " + str(envelope_size)
                # Repeat this ENVELOPE_SIZE times
                for e in range(0, envelope_size):
                    envelope_value = getInt()  #                    4 Bytes: ENVELOPE_VALUE (signed int, offset=12)
                if envelope_size > 0:
                    loop_position = getByte() #         1 Byte: LOOP_POSITION (-1 = NO LOOP)
                macro_mode = getByte() #            1 Byte: ARPEGGIO MACRO MODE (0 = Normal, 1 = Fixed)

                #//DUTY/NOISE MACRO
                envelope_size = getByte() #                1 Byte: ENVELOPE_SIZE (0 - 127)
                print "  duty/noise envelope size " + str(envelope_size)
                # Repeat this ENVELOPE_SIZE times
                for e in range(0, envelope_size):
                    envelope_value = getInt()  #                    4 Bytes: ENVELOPE_VALUE
                if envelope_size > 0:
                    loop_position = getByte() #         1 Byte: LOOP_POSITION (-1 = NO LOOP)

                #//WAVETABLE MACRO
                envelope_size = getByte() #                1 Byte: ENVELOPE_SIZE (0 - 127)
                print "  wavetable envelope size " + str(envelope_size)

                # Repeat this ENVELOPE_SIZE times
                for e in range(0, envelope_size):
                    envelope_value = getInt()  #                    4 Bytes: ENVELOPE_VALUE
                if envelope_size > 0:                
                    loop_position = getByte() #         1 Byte: LOOP_POSITION (-1 = NO LOOP)

                # per system data, only present for C64


        #//END OF INSTRUMENTS DATA


        #//WAVETABLES DATA
        total_wavetables = getByte()
        if total_wavetables != 0:
            print "ERROR: unexpected wavetables data"
            return


        header_data_size = self.dmf_data.tell()
        print "size of header is " + str(header_data_size) + " bytes"

        #//PATTERNS DATA

        for c in range(0, SYSTEM_TOTAL_CHANNELS):

            print "Reading patterns for channel " + str(c)
            CHANNEL_EFFECTS_COLUMNS_COUNT = getByte()
            print " CHANNEL_EFFECTS_COLUMNS_COUNT " + str(CHANNEL_EFFECTS_COLUMNS_COUNT)

            note_table = [ "", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-", "C-"]
            for n in range(0, total_rows_in_pattern_matrix):

                print "  reading pattern matrix " + str(n)
                for r in range(0, total_rows_per_pattern):

                    note = getShort()
                    octave = getShort()

                    #//Note values:
                    #//01 C#
                    #//02 D-
                    #//03 D#
                    #//04 E-
                    #//05 F-
                    #//06 F#
                    #//07 G-
                    #//08 G#
                    #//09 A-
                    #//10 A#
                    #//11 B-
                    #//12 C-
                    #//Special cases:
                    #//Note = 0 and octave = 0 means empty.
                    #//Note = 100 means NOTE OFF, no matter what is inside the octave value.

                    volume = getShort() #Volume for this index (-1 = Empty)



                    o = "   pattern row " + str(r)
                    if note == 100:
                         o += ", note OFF"
                    else:                       
                        if note != 0 and octave != 0:
                            o += ", note " + note_table[note] + str(octave) #str(note)
                            #o += ", octave " + str(octave)
                        else:
                            o += ", note ---"
                        

                    if volume < 65535:
                        o += ", volume " + str(volume)


                    # effects
                    # http://battleofthebits.org/lyceum/View/DefleMask+Tracker+Effects+Commands/#SEGA Master System (SN76489)

                    # These are the effects commands available for the 6 chips supported thus far by DefleMask Tracker. 
                    # The ones that begin with a 1 are always system-specific (also 2 for the SN76489 and SEGA PCM) so make sure you do not mix them up after switching systems! 


                    # 00xy - Arpeggio; fast note shifting in half steps. 
                    # x = Number of half steps from root note for first shift 
                    # y = Number of half steps from root note for second shift 
                    # 
                    # Ex: 037 = Minor chord. 047 = Major chord. 
                    # View article on arps for more examples. 
                    # 
                    # 
                    # 01xx - Portamento up; smooth pitch glide up. 
                    # 02xx - Portamento down; smooth pitch glide down. 
                    # If xx > 00: Speed 
                    # If xx = 00: Off 
                    # 
                    # 
                    # 03xx - Glissando; pitch glide to next note. 
                    # If xx > 00: Speed 
                    # If xx = 00: Off 
                    # 
                    # 
                    # 04xy - Vibrato; pitch vibration. 
                    # If x > 0: Speed 
                    # If x = 0: Off 
                    # y = Depth 
                    # 
                    # Overridden by YMU759; see below. 
                    # 
                    # 
                    # 05xy - Glissando + Volume slide; see Axy below. 
                    # Continues previous 03xx effect without modifying it. 
                    # 
                    # 
                    # 06xy - Vibrato + Volume slide; see Axy below. 
                    # Continued previous 04xy effect without modifying it. 
                    # 
                    # 
                    # 07xy - Tremolo; volume tremor. 
                    # If x > 0: Speed 
                    # If x = 0: Off 
                    # y = Depth 
                    # 
                    # 
                    # 08xy - L/R output setting. 
                    # If x = 0: Left channel output off 
                    # If x = 1: Left channel output on 
                    # If y = 0: Right channel output off 
                    # If y = 1: Right channel output on 
                    # 
                    # Overridden by HuC6280; see below. 
                    # 
                    # 
                    # 09xx - Speed 1 setting; see 0Fxx below. 
                    # If xx = 01-20: Ticks per row for odd rows 
                    # 
                    # 
                    # 0Axy - Volume slide. 
                    # If x = 0 & y = 0: Halt slide 
                    # If x = 0 & y > 0: Volume slide up x ticks depth 
                    # If x > 0 & y = 0: Volume slide down y ticks depth 
                    # 
                    # Note: Same parameters for effects 05xy and 06xy above. 
                    # 
                    # 
                    # 0Bxx - Jump to frame. 
                    # xx = Destination frame number 
                    # 
                    # 
                    # 0Cxx - Retrigger, works only for current row. 
                    # xx = Rate in ticks 
                    # 
                    # 
                    # 0Dxx - Skip to next frame at row xx. 
                    # xx = Destination row number 
                    # 
                    # 
                    # 0Fxx - Speed 2 setting; see 09xx above. 
                    # If xx = 01-20: Ticks per row for even rows 
                    # 
                    # 
                    # E1xy - Note slide up 
                    # E2xy - Note slide down 
                    # x = speed of slide 
                    # y = semitones to slide 
                    # 
                    # 
                    # E5xx - Channel fine pitch setting. 
                    # If xx = 80: Default 
                    # If xx > 80: Increase pitch 
                    # If xx < 80: Decrease pitch 
                    # 
                    # 
                    # EBxx - Set sample bank to xx. 
                    # If xx = 00-0B: Sample bank 0 to 11 is used. 
                    # If xx > 0B: nothin' 
                    # 
                    # 
                    # ECxx - Delayed note cut. 
                    # xx = number of ticks to delay 
                    # 
                    # 
                    # EDxx - Note delay. 
                    # xx = number of ticks to delay 
                    # 
                    # 
                    # EFxx - Global fine pitch setting. 
                    # If xx = 80: Default 
                    # If xx > 80: Increase pitch 
                    # If xx < 80: Decrease pitch 

                    # 20xy - PSG noise channel setting. 
                    # If x = 0: 3-pitch fixed noise 
                    # If x > 0: Variable-pitch noise 
                    # If y = 0: Periodic noise 
                    # If y > 0: White noise 
                    # This effect is also available when the current system is set to Genesis, via the PSG channels. 


                    for fx in range(0, CHANNEL_EFFECTS_COLUMNS_COUNT ):
                        effect_code = getShort() # Effect Code for this index (-1 = Empty)
                        effect_value = getShort() # Effect Value for this index (-1 = Empty)
                        if effect_code < 65535:
                            o+= ", effect code " + str(effect_code)
                        if effect_value < 65535:
                            o+= ", effect val " + str(effect_value)


                    instrument = getShort() # Instrument for this index (-1 = Empty)

                    if instrument < 65535:
                        o += ", instrument " + str(instrument)

                    print o

                    #print "   pattern row " + str(r) + ", instrument " + str(instrument) + ", note " + str(note) + ", octave " + str(octave) + ", volume " + str(volume)

        pattern_data_size = self.dmf_data.tell() - header_data_size
        print "size of pattern data is " + str(pattern_data_size) + " bytes"

        # //PCM SAMPLES DATA
        TOTAL_SAMPLES = getByte()
        if TOTAL_SAMPLES != 0:
            print "ERROR: Unexpected samples"
            return


        # //END OF DMF FORMAT
        print "All parsed."


#------------------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------------------

# for testing
my_command_line = None
if False:


	# for testing...
	my_command_line = 'vgmconverter "' + filename + '" -t bbc -q 50 -o "test.vgm"'




#------------------------------------------------------------------------------------------

if my_command_line != None:
	argv = my_command_line.split()
else:
	argv = sys.argv

argc = len(argv)

if argc < 2:
	print "DMF Parser Utility for DMF files based on SMS TI SN76849 programmable sound chips"
	print ""
	print " Usage:"
	print "  dmf-parser <dmffile>"
	print ""
	print "   where:"
	print "    <dmffile> is the source DMF file to be processed. Wildcards are not yet supported."
	print ""
	print "   options:"
	exit()

# pre-process argv to merge quoted arguments
argi = 0
inquotes = False
outargv = []
quotedarg = []
#print argv
for s in argv:
	#print "s=" + s
	#print "quotedarg=" + str(quotedarg)
	
	if s.startswith('"') and s.endswith('"'):
		outargv.append(s[1:-1])	
		continue
	
	if not inquotes and s.startswith('"'):
		inquotes = True
		quotedarg.append(s[1:] + ' ')
		continue
	
	if inquotes and s.endswith('"'):
		inquotes = False
		quotedarg.append(s[:-1])
		outargv.append("".join(quotedarg))
		quotedarg = []
		continue
		
	if inquotes:
		quotedarg.append(s + ' ')	
		continue
		
	outargv.append(s)

if inquotes:
	print "Error parsing command line " + str(" ".join(argv))
	exit()

argv = outargv
	
# validate source file	
source_filename = None
if argv[1][0] != '-':
	source_filename = argv[1]


# load the DMF
if source_filename == None:
	print "ERROR: No source <filename> provided."
	exit()



	
dmf_stream = DmfStream(source_filename)
dmf_stream.parse()

# all done
print ""
print "Processing complete."


