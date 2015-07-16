from vmodel import *
'''moduleNamesToNiceNames = {"v": "V", "vdebug": "VDebug", "vglobals": "VGlobals", "vmodelexport": "VModelExport"}
for name, niceName in enumerate(moduleNamesToNiceNames):
	exec(niceName + " = " + name)'''
moduleNiceNames = ["V", "VDebug", "VClassExtensions", "VGlobals", "VModel", "VModelExport"]
for niceName in moduleNiceNames:
	if niceName.lower() in locals() or niceName.lower() in globals():
		exec(niceName + " = " + niceName.lower())

import bpy
import math
from mathutils import *
import re

# snippets
# ==========

#__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

# constants
# ==========

null = None
false = False
true = True

# Blender: general
# ==========

def Objects():
	return bpy.data.objects
def Obj(name):
	for obj in bpy.data.objects:
		if obj.name == name:
			return obj
	return null
def Selected(includeActive = true):
	result = bpy.context.selected_objects
	if not includeActive:
		result = [a for a in result if a != Active()]
	return result
def Active():
	return bpy.context.scene.objects.active
def SelectedVertexes():
	return Active().Vertexes().Where("a.select")
def SelectedVertex():
	return SelectedVertexes()[0]
def ActiveVertex():
	return SelectedVertex()

def SaveMesh():
	oldMode = bpy.context.object.mode
	bpy.ops.object.mode_set(mode = "OBJECT")
	bpy.ops.object.mode_set(mode = oldMode)

def Get3DCursorPosition():
	return bpy.context.scene.cursor_location

# general
# ==========

def Log(message):
	print(message)

s_defaultNumberTruncate = -1
def S(obj, numberTruncate = null):
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
		#result = "[" + S(vec[0]) + " " + S(vec[1]) + " " + S(vec[2]) + "]"
		result = "[" + S(obj.x, numberTruncate) + " " + S(obj.y, numberTruncate) + " " + S(obj.z, numberTruncate) + "]"
	elif type(obj) == Quaternion:
		result = "[" + S(obj.x, numberTruncate) + " " + S(obj.y, numberTruncate) + " " + S(obj.z, numberTruncate) + " " + S(obj.w, numberTruncate) + "]"
	#elif type(obj) == Color:
	#	result = str(c) #"%d" % c
	else:
		result = str(obj)
	
	return result
def st(obj, numberTruncate = null):
	return S(obj, numberTruncate)

# blender constants/shortcuts
# ==========

'''import bpy
def PostSceneLoad(unknown):
	Log("Handler called")
	global C, D
	C = bpy.context
	D = bpy.data

	if PostSceneLoad in bpy.app.handlers.scene_update_post:
		bpy.app.handlers.scene_update_post.remove(PostSceneLoad)

if PostSceneLoad not in bpy.app.handlers.scene_update_post:
	Log("Adding handler")
	bpy.app.handlers.scene_update_post.append(PostSceneLoad)'''

# linq
# ==========

def Any(collection, matchFunc):
	return len(list(filter(matchFunc, collection))) > 0

# bounds class
# ==========

RareFloat = -9876.54321

class Box:
	'''_Null = null
	@classmethod
	@property
	def Null():
		return Box(Vector((RareFloat, RareFloat, RareFloat)), Vector((RareFloat, RareFloat, RareFloat)))'''
	Null = null

	def __init__(s, position, size):
		s.position = Vector(position)
		s.size = Vector(size)
	#def GetMin():
	#	return position
	def GetMax(s):
		return s.position + s.size
	def Encapsulate(s, point_orBox):
		result = Box(s.position, s.size)
		if type(point_orBox) is Box:
			box = point_orBox
			if result.position == Box.Null.position and result.size == Box.Null.size: #s is Box.Null:
				result.position = box.position
				result.size = box.size
			else:
				result.position.x = min(result.position.x, box.position.x)
				result.position.y = min(result.position.y, box.position.y)
				result.position.z = min(result.position.z, box.position.z)
				result.size.x = max(result.GetMax().x, box.GetMax().x) - result.position.x
				result.size.y = max(result.GetMax().y, box.GetMax().y) - result.position.y
				result.size.z = max(result.GetMax().z, box.GetMax().z) - result.position.z
		else:
			point = point_orBox
			if result.position == Box.Null.position and result.size == Box.Null.size: #s is Box.Null:
				result.position = point
				result.size = (0, 0, 0)
			else:
				result.position.x = min(result.position.x, point.x)
				result.position.y = min(result.position.y, point.y)
				result.position.z = min(result.position.z, point.z)
				result.size.x = max(result.GetMax().x, point.x) - result.position.x
				result.size.y = max(result.GetMax().y, point.y) - result.position.y
				result.size.z = max(result.GetMax().z, point.z) - result.position.z
		return result
	def Intersects(s, point_orBox):
		if type(point_orBox) is Box:
			box = point_orBox
			xIntersects = s.position.x < box.GetMax().x and box.x < s.GetMax().x
			yIntersects = s.position.y < box.GetMax().y and box.y < s.GetMax().y
			zIntersects = s.position.z < box.GetMax().z and box.z < s.GetMax().z
			return xIntersects and yIntersects and zIntersects
		else:
			point = point_orBox
			xIntersects = s.position.x < point.x and point.x < s.GetMax().x
			yIntersects = s.position.y < point.y and point.y < s.GetMax().y
			zIntersects = s.position.z < point.z and point.z < s.GetMax().z
			return xIntersects and yIntersects and zIntersects

Box.Null = Box(Vector((RareFloat, RareFloat, RareFloat)), Vector((RareFloat, RareFloat, RareFloat)))