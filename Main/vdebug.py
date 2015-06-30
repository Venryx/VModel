from io_scene_vmodel import *
from io_scene_vmodel.vglobals import *

import time

# profiling
# ==========

'''
def StartBlock():
{
	stopwatch.Reset();
	stopwatch.Start();
	#Log("Starting timer.");
}
public static void MidBlock(string name)
{
	EndBlock(name);
	StartBlock();
}
public static void EndBlock(string name) { Log("Block_" + name + ") " + (stopwatch.ElapsedTicks / 10000f)); } // ElapsedMilliseconds
public static void Block(string name = null)
{
	if (name != null)
		MidBlock(name);
	else
		StartBlock();
}
'''

'''
sectionStartTime = 0
sectionTotals = {}
def StartSection():
	sectionStartTime = time.clock()
def MidSection(name, mark = false):
	if name not in sectionTotals: #sectionTotals:
		sectionTotals[name] = 0
	sectionTotals[name] += time.clock() - sectionStartTime
	if mark:
		MarkSection(name)
	StartSection()
def EndSection(name, mark = false):
	if name not in sectionTotals:
		sectionTotals[name] = 0
	sectionTotals[name] += time.clock() - sectionStartTime
	if mark:
		MarkSection(name)
def Section(name = null, mark = false):
	if name != null:
		MidSection(name, mark) # or end section; mid-section method works for either (since the next start-section will just ignore the hanging-section timer data)
	else:
		StartSection()
'''

sectionStartTimes_unnamed = []
sectionStartTimes = {}
sectionAddCounts = {}
sectionTotals = {}
def StartSection(name = null):
	if name is null:
		sectionStartTimes_unnamed.append(time.clock())
	else:
		sectionStartTimes[name] = time.clock()
def EndSection(name, mark = false):
	if name not in sectionAddCounts:
		sectionAddCounts[name] = 0
		sectionTotals[name] = 0

	if name not in sectionStartTimes:
		sectionStartTimes[name] = sectionStartTimes_unnamed.pop()

	sectionAddCounts[name] += 1
	sectionTotals[name] += time.clock() - sectionStartTimes[name]
	sectionStartTimes.pop(name)

	if mark:
		MarkSection(name)

def MarkSection(name):
	Log("Section_" + name + ") " + s(sectionTotals[name]) + ", " + s(sectionAddCounts[name]) + " adds")
def MarkSections():
	for name in sectionAddCounts: # maybe todo: add sorting
		MarkSection(name)