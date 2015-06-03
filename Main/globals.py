from io_scene_vmodel import *
#from io_scene_vmodel.globals import *

import re
import math
from mathutils import *

# snippets
# ==========

#__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

# constants
# ==========

null = None
false = False
true = True

# linq
# ==========

def Any(collection, matchFunc):
	return len(list(filter(matchFunc, collection))) > 0

# general
# ==========

def Log(message):
	print(message)

s_defaultNumberTruncate = -1
def s(obj, numberTruncate = null):
	global s_defaultNumberTruncate
	numberTruncate = numberTruncate if numberTruncate != null else s_defaultNumberTruncate
	#if numberTruncate != -1:
	#	numberTruncate += 1 # todo: make sure this is correct

	result = ""

	#if obj is int or obj is float: #or obj is long: #or obj is complex:
	if type(obj) == int or type(obj) == float:
		result = ("{:." + str(numberTruncate) + "f}").format(float("%g" % obj)) if numberTruncate != -1 else ("%g" % obj) #str(obj)

		if result.find(".") != -1:
			result = result.rstrip("0")
		if result.endswith("."):
			result = result[0:-1]

		if result.startswith("0."):
			result = result[1:]
		if result.startswith("-0."):
			result = "-" + result[2:]
	
		if result == "-0":
			result = "0"
		if result == ".0" or result == "-.0":
			result = "0"
	elif type(obj) == Vector: #elif obj is Vector:
		result = "[" + s(obj.x, numberTruncate) + " " + s(obj.y, numberTruncate) + " " + s(obj.z, numberTruncate) + "]"
	elif type(obj) == Quaternion:
		result = "[" + s(obj.x, numberTruncate) + " " + s(obj.y, numberTruncate) + " " + s(obj.z, numberTruncate) + " " + s(obj.w, numberTruncate) + "]"
	else:
		result = str(obj)
	
	return result