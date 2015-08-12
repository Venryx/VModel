from vmodel import *
from vmodel.vglobals import *

import bpy_types

'''def AddMethod(type, method):
	type[method.__name__] = method
	del(method)'''

# Object
# ==========

def GetBounds(s):
	'''result = Box(s.location, s.dimensions)
	for child in s.children:
		result = result.Encapsulate(child.GetBounds())
	return result'''
	result = Box.Null
	for corner in s.bound_box:
		result = result.Encapsulate(s.matrix_world * Vector(corner))
	return result
#AddMethod(bpy_types.Object, GetBounds)
bpy_types.Object.GetBounds = GetBounds
#del(GetBounds)

def GetDescendents(s):
	result = []
	for child in s.children:
		result.append(child)
		result.extend(child.GetDescendents())
	return result
bpy_types.Object.GetDescendents = GetDescendents

# Bone
# ==========

# fix the root-bone matrix, to use the more sensible resting position/orientation (where the rest rotation has the tail-end toward z+, rather than y+)
#if s.parent is null:
#	result = fixMatrixForRootBone(result)

def Bone_GetMatrix_Object(s):
	return s.matrix_local
bpy_types.Bone.GetMatrix_Object = Bone_GetMatrix_Object

def Bone_GetMatrix(s):
	result = s.matrix_local # starts out including parent-matrix
	if s.parent is not null:
		result = s.parent.matrix_local.inverted() * result
	return result
bpy_types.Bone.GetMatrix = Bone_GetMatrix

# PoseBone
# ==========

# note that, as per V heirarchy/parent-and-unit conceptualization standards, matrix_object does not include base-matrix_object (so it's not in object-space--at least not in-the-same-way/with-the-same-units as, say, vertexes are)
def PoseBone_GetMatrix_Object(s, addBaseMatrixes = true):
	baseBone = s.bone

	result = s.matrix # starts out as: base-matrix_object + matrix_object(pose-matrix_object)
	if not addBaseMatrixes:
		result = baseBone.matrix_local.inverted() * result
	#result = baseBone.matrix_local.inverted() * result
	#if addBaseMatrixes:
	#	result = export_vmodel.realBoneRestMatrixes[bone] * result
	
	return result
bpy_types.PoseBone.GetMatrix_Object = PoseBone_GetMatrix_Object

def PoseBone_GetMatrix(s, addBaseMatrixes = true):
	baseBone = s.bone

	result = s.matrix # starts out as: [parent-base-matrix_object + parent-matrix_object] + [base-matrix_object + matrix_object]
	if s.parent is not null: # remove this part: [parent-base-matrix_object + parent-matrix_object]
		result = s.parent.GetMatrix_Object().inverted() * result
	if not addBaseMatrixes: # remove this part: base-matrix_object
		result = baseBone.GetMatrix_Object().inverted() * result
	#result = baseBone.GetMatrix_Object().inverted() * s.matrix
	#if addBaseMatrixes:
	#	result = export_vmodel.realBoneRestMatrixes[bone] * result

	return result
bpy_types.PoseBone.GetMatrix = PoseBone_GetMatrix