import csv
import sys
import os
import argparse
from collections import defaultdict

# todo:
# 	- always encode percussions if percussions are present
# 	- if specified, encode channels given. if not, encode all.

parser = argparse.ArgumentParser(description='Generates C arrays from MIDI file channels')
parser.add_argument('--file', help='The MIDI file to use', required=True)
parser.add_argument('--vocal', nargs='+', help='List of the channels to use for vocals. Supports only one frequency at a time', required=False, type=int)
parser.add_argument('--transpose', help='Transpose all channels by a number of notes', required=False, type=int)
parser.add_argument('--encoding', help='Decide how time is encoded; frequency (Hz) or period (us). Default: frequency', required=False, choices=['frequency', 'period'])
args = parser.parse_args()

midiFileName 	= args.file
vocalChannels 	= args.vocal
transposeBy		= args.transpose

# convert MIDI note numbers to frequency or period depending on user input
a 		= 440
notes 	= []
for x in range(0, 127):
	f = ((a / 32.0) * (2 ** ((x - 9) / 12.0)))
	if args.encoding is 'period':
		notes.append(1e6/f)
	else:
		notes.append(f)

# convert midi to csv using midicsv
scorename, _, _ = midiFileName.partition('.')
os.system("./midicsv " + midiFileName + " > " + scorename + ".csv" )
csvfd = open(scorename + ".csv")
reader = csv.reader(csvfd)

# sort csv by tick stamps
reader_sorted = sorted(reader, key=lambda row: int(row[1]))

# keep track of relevant MIDI data
MIDIChannelData = defaultdict(list)
tempo 			= 0
division 		= 0
usPerTick 		= 0

# go through csv rows and extract relevant information
for row in reader_sorted:
	evt = row[2]
	tick = int(row[1])
	
	if "Header" in evt:
		division = int(row[5])

	if "Tempo" in evt:
		tempo 		= int(row[3])
		usPerTick 	= float(tempo) / division

	if "Note_" in evt:
		ch 			= int(row[3])
		velocity 	= int(row[5])
		note 		= int(row[4])
		if transposeBy:
			note += transposeBy

		# treat note on with zero velocity as note off
		if "Note_on" in evt and velocity == 0:
			evt = "Note_off"

		# first iteration edge case
		if not MIDIChannelData[ch]:
			MIDIChannelData[ch].append( [tick * usPerTick, evt, note] )
			continue

		if ch in vocalChannels:
			# escape chords on same channel, i.e. consecutive "Note_on" events -- we 
			# can only play one frequency at a time per channel. Opt to play the 
			# highest note in the chord to preserve melody.
			if "Note_on" in evt and "Note_on" in MIDIChannelData[ch][-1][1]:
				if note < MIDIChannelData[ch][-1][2]:
					MIDIChannelData[ch][-1][2] = note
				continue
			elif "Note_off" in evt and "Note_on" in MIDIChannelData[ch][-1][1]:
				if note != MIDIChannelData[ch][-1][2]:
					continue
			elif "Note_off" in evt and "Note_off" in MIDIChannelData[ch][-1][1]:
				continue

		# store information about tick number, event and note number for all channels
		MIDIChannelData[ch].append( [tick * usPerTick, evt, note] )		
		
MIDIChannelStrings = defaultdict(str)

# print C-formatted MIDI information
for ch, data in MIDIChannelData.items():

	if 
	if ch in vocalChannels:
		entries = len(data) / 2 # note on -> note off counts as one entry
		print("// period (us)," if args.encoding == 'period' else "// frequency (Hz),", end='')
		print("delay before this note (us), duration (us)")
		print("const int ch" + str(ch) + "_length = " + str(entries) + ";\n", end='')
		print("const double ch" + str(ch) + "[" + str(entries) + "][3] = {\n", end='')

		for row in range(0, int(entries * 2)):
			
			dt = data[row][0] if row == 0 else data[row][0] - data[row - 1][0]
			if dt < 0:
				print("//Got negative dt on row " + str(row) + " clamping to 0")
				dt = 0

			timeInfo = notes[data[row][2]]
			if args.encoding == 'period':
				timeInfo = 1e6 / notes[data[row][2]]
					
			if "Note_on" in data[row][1]:
				print("\t{%8.2f, %8d, " % (timeInfo, dt), end='')

			elif "Note_off" in data[row][1]: 
				print("%8d},\n" % dt if (row < 2*entries - 1) else "%8d}\n" % (dt), end='')

		print("};\n\n", end='')


	if ch in 9: # percussion channel
		entries = len(data)
		
		print("// note number, delay before this note")
		print("const int chd_length = " + str(entries) + ";\n", end='')
		print("const double chd[" + str(entries) + "][2] = {\n", end='')

		dt = data[0][0]
		prevpercussionEvtTime = dt
		for row in range(0, entries):
			if "Note_on" in data[row][1]:
				dt = data[row][0] if row == 0 else data[row][0] - prevpercussionEvtTime
				prevpercussionEvtTime = data[row][0]
				percussionch = data[row][2]
				if data[row][2] is 46:	# open hi hat
					percussionch = 0
				if data[row][2] is 35 or 36: # bass percussion
					percussionch = 1
				if data[row][2] is 38:	# snare
					percussionch = 2
				if data[row][2] is 42:	# closed hi hat
					percussionch = 3
				if data[row][2] is 41 or 47 or 48 or 57: # toms and crashes
					percussionch = 4
				print("\t{%2d, %8d},\n" % (percussionch, dt) if (row < entries - 1) else "\t{%5d, %8d}\n" % (percussionch, dt), end='')
		print("};")

# clean up
#os.system("rm " + scorename + ".csv")
