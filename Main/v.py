from io_scene_vmodel import *
from io_scene_vmodel.vglobals import *

import re
import math
from mathutils import *

# snippets
# ==========

#__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

# console helpers
# ==========

def GetObjByName(name):
	for obj in data["objects"]:
		if obj.name == name:
			return obj
	return null

# general
# ==========

def indentLines(str, count = 1, indentFirstLine = true):
	for i in range(0, count):
		if indentFirstLine:
			str = "\t" + str
		return re.sub('\n', '\n\t', str)

def toDegrees(radians): #math.degrees
	return radians * (180 / math.pi) # radians * degrees-in-a-radian
def toRadians(degrees): #math.radians
	return degrees / (180 / math.pi) # degrees / degrees-in-a-radian

def Vector_toDegrees(v):
	if len(v) == 3:
		return Vector((toDegrees(v.x), toDegrees(v.y), toDegrees(v.z))) #return {"x": toDegrees(v.x), "y": toDegrees(v.y), "z": toDegrees(v.z)}
	else:
		return  Vector((toDegrees(v.x), toDegrees(v.y), toDegrees(v.z), toDegrees(v.w))) #return {"x": toDegrees(v.x), "y": toDegrees(v.y), "z": toDegrees(v.z), "w": toDegrees(v.w)}
def Quaternion_toDegrees(q):
	return Quaternion((toDegrees(q.w), toDegrees(q.x), toDegrees(q.y), toDegrees(q.z)))

'''def matrixParts_toDegrees(pos, rot, scale):
	return Vector_toDegrees(pos), Quaternion_toDegrees(rot) if type(rot) == Quaternion else Vector_toDegrees(rot), Vector_toDegrees(scale)
def matrixParts_toRadians(pos, rot, scale):
	return Vector_toRadians(pos), Quaternion_toRadians(rot) if type(rot) == Quaternion else Vector_toRadians(rot), Vector_toRadians(scale)'''

# utils
# ==========

def veckey3(x,y,z):
	return round(x, 6), round(y, 6), round(z, 6)

def veckey3d(v):
	return veckey3(v.x, v.y, v.z)

def veckey2d(v):
	return round(v[0], 6), round(v[1], 6)

def get_faces(obj):
	if hasattr(obj, "tessfaces"):
		return obj.tessfaces
	else:
		return obj.faces

def get_normal_indices(v, normals, mesh):
	n = []
	mv = mesh.vertices

	for i in v:
		normal = mv[i].normal
		key = veckey3d(normal)

		n.append(normals[key])

	return n

def get_color_indices(face_index, colors, mesh):
	c = []
	color_layer = mesh.tessface_vertex_colors.active.data
	face_colors = color_layer[face_index]
	face_colors = face_colors.color1, face_colors.color2, face_colors.color3, face_colors.color4
	for i in face_colors:
		c.append(colors[hexcolor(i)])
	return c

def rgb2int(rgb):
	color = (int(rgb[0] * 255) << 16) + (int(rgb[1] * 255) << 8) + int(rgb[2] * 255)
	return color

# utils - files
# ==========

def write_file(fname, content):
	out = open(fname, "w", encoding="utf-8")
	out.write(content)
	out.close()

def ensure_folder_exist(foldername):
	"""Create folder (with whole path) if it doesn't exist yet."""

	if not os.access(foldername, os.R_OK | os.W_OK | os.X_OK):
		os.makedirs(foldername)

def ensure_extension(filepath, extension):
	if not filepath.lower().endswith(extension):
		filepath += extension
	return filepath

def generate_mesh_filename(meshname, filepath):
	normpath = os.path.normpath(filepath)
	path, ext = os.path.splitext(normpath)
	return "%s.%s%s" % (path, meshname, ext)

# utils - alignment
# ==========

def bbox(vertices):
	"""Compute bounding box of vertex array.
	"""

	if len(vertices) > 0:
		minx = maxx = vertices[0].co.x
		miny = maxy = vertices[0].co.y
		minz = maxz = vertices[0].co.z

		for v in vertices[1:]:
			if v.co.x < minx:
				minx = v.co.x
			elif v.co.x > maxx:
				maxx = v.co.x

			if v.co.y < miny:
				miny = v.co.y
			elif v.co.y > maxy:
				maxy = v.co.y

			if v.co.z < minz:
				minz = v.co.z
			elif v.co.z > maxz:
				maxz = v.co.z

		return { 'x':[minx,maxx], 'y':[miny,maxy], 'z':[minz,maxz] }

	else:
		return { 'x':[0,0], 'y':[0,0], 'z':[0,0] }

def translate(vertices, t):
	"""Translate array of vertices by vector t.
	"""

	for i in range(len(vertices)):
		vertices[i].co.x += t[0]
		vertices[i].co.y += t[1]
		vertices[i].co.z += t[2]

def center(vertices):
	"""Center model (middle of bounding box).
	"""

	bb = bbox(vertices)

	cx = bb['x'][0] + (bb['x'][1] - bb['x'][0]) / 2.0
	cy = bb['y'][0] + (bb['y'][1] - bb['y'][0]) / 2.0
	cz = bb['z'][0] + (bb['z'][1] - bb['z'][0]) / 2.0

	translate(vertices, [-cx,-cy,-cz])

	return [-cx,-cy,-cz]

def top(vertices):
	"""Align top of the model with the floor (Y-axis) and center it around X and Z.
	"""

	bb = bbox(vertices)

	cx = bb['x'][0] + (bb['x'][1] - bb['x'][0]) / 2.0
	cy = bb['y'][1]
	cz = bb['z'][0] + (bb['z'][1] - bb['z'][0]) / 2.0

	translate(vertices, [-cx,-cy,-cz])

	return [-cx,-cy,-cz]

def bottom(vertices):
	"""Align bottom of the model with the floor (Y-axis) and center it around X and Z.
	"""

	bb = bbox(vertices)

	cx = bb['x'][0] + (bb['x'][1] - bb['x'][0]) / 2.0
	cy = bb['y'][0]
	cz = bb['z'][0] + (bb['z'][1] - bb['z'][0]) / 2.0

	translate(vertices, [-cx,-cy,-cz])

	return [-cx,-cy,-cz]

# 3d position/rotation/scale
# ==========

def getBoneLocalMatrix(poseBoneOrBone, includeBaseMatrix = true, includePoseMatrix = true): # accepts either a pose-bone or a bone
	poseBone = poseBoneOrBone if type(poseBoneOrBone).__name__ == "PoseBone" else null
	bone = poseBone.bone if poseBone is not null else poseBoneOrBone

	# get local matrix, using Blender's system
	# ----------
	
	if poseBone is null or not includePoseMatrix:
		if bone.parent is null:
			localMatrix = bone.matrix_local
		else:
			localMatrix = bone.parent.matrix_local.inverted() * bone.matrix_local
	else:
		if bone.parent is null:
			if not includeBaseMatrix:
				localMatrix = bone.matrix_local.inverted() * poseBone.matrix
			else:
				localMatrix = poseBone.matrix
		else:
			if not includeBaseMatrix:
				#localMatrix = (bone.parent.matrix_local.inverted() * poseBone.parent.matrix).inverted() * (bone.matrix_local.inverted() * poseBone.matrix)
				localMatrix = (bone.parent.matrix_local.inverted() * bone.matrix_local).inverted() * (poseBone.parent.matrix.inverted() * poseBone.matrix)
			else:
				localMatrix = poseBone.parent.matrix.inverted() * poseBone.matrix

	# fix the local matrix, to use the more sensible resting position/orientation (where the rest rotation has the tail-end toward z+, rather than y+)
	# ----------

	#if bone.parent is null:
	#	localMatrix = fixMatrixForRootBone(localMatrix)

	return localMatrix

def fixMatrixForRootBone(localMatrix):
	position, rotation, scale = localMatrix.decompose()

	'''rotation = Quaternion([.707107, .707107, 0, 0]).rotation_difference(rotation) # w, x, y, z
	yOld = rotation.y
	rotation.y = -rotation.z
	rotation.z = yOld'''
	# todo; make sure this doesn't mess up the positions/rotations of its descendants (I think it does)

	#rotation = Quaternion([.707107, 0, 0, .707107]).rotation_difference(rotation) # make it be rotated 90 degrees around the y-axis (using Unity's left-hand rule), when imported into Unity
	#rotation = Quaternion([.707107, 0, 0, -.707107]) * rotation
	
	return Matrix.Translation(position) * rotation.to_matrix().to_4x4() * Matrix.Scale(1, 4, scale)

# 3d object creation
# ==========

def CreateObject_Empty(name, position = (0, 0, 0), rotation = (0, 0, 0, 1), scale = (1, 1, 1), emptyDrawType = "PLAIN_AXES"):
	position = Vector(position)
	rotation = Vector(rotation)
	scale = Vector(scale)

	result = bpy.data.objects.new(name, None)

	scene = bpy.context.scene
	scene.objects.link(result)
	scene.update()

	result.location = position
	#result.rotation = rotation
	result.scale = scale #/ 2

	result.empty_draw_type = emptyDrawType
	
	return result

def CreateObject_Cube(name, position = (0, 0, 0), rotation = (0, 0, 0, 1), scale = (1, 1, 1)):
	position = Vector(position)
	rotation = Vector(rotation)
	scale = Vector(scale)

	#return bpy.ops.mesh.primitive_cube_add(location = location, rotation = rotation, scale = scale)
	bpy.ops.mesh.primitive_cube_add() #location = position)
	result = [a for a in bpy.data.objects if a.select][0]
	result.location = position + Vector((scale.x / 2, scale.y / 2, scale.z / 2))
	#result.rotation = rotation #result.localRotation = rotation
	result.scale = scale #result.localScale = scale
	return result

# object control
# ==========

savedSelections = {}
def SaveSelection(name = "main"):
	savedSelections[name] = GetSelection()
def GetSelection():
	result = {}
	for obj in bpy.data.objects:
		result[obj] = obj.select
	return result
def LoadSelection(name = "main"):
	selection = savedSelections[name]
	for obj in bpy.data.objects:
		obj.select = obj in selection and selection[obj]

def DeleteObject(obj):
	for child in obj.children:
		DeleteObject(child)

	for obj2 in bpy.context.scene.objects:
		obj2.select = false
	obj.select = true
	bpy.ops.object.delete()

'''def SetObjectOriginPoint(obj, originPoint):
	saved_location = bpy.context.scene.cursor_location.copy()
    bpy.ops.view3d.snap_cursor_to_selected()

    bpy.ops.object.mode_set(mode = 'OBJECT')
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')  
    bpy.context.scene.cursor_location = saved_location

    bpy.ops.object.mode_set(mode = 'EDIT')'''