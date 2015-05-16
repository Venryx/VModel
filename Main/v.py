import re
import math
from mathutils import *

# snippets
# ==========

#__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

# constants
# ==========

nothing = None
false = False
true = True

# linq
# ==========

def any(collection, matchFunc):
	return len(list(filter(matchFunc, collection))) > 0

# custom - console helpers
# ==========

def GetObjByName(name):
	for obj in data["objects"]:
		if obj.name == name:
			return obj
	return nothing

# custom
# ==========

def Log(message):
	print(message)

s_defaultNumberTruncate = -1

def s(obj, numberTruncate = nothing):
	numberTruncate = numberTruncate if numberTruncate != nothing else s_defaultNumberTruncate
	#if numberTruncate != -1:
	#	numberTruncate += 1 # todo: make sure this is correct

	result = ""

	#if obj is int or obj is float: #or obj is long: #or obj is complex:
	if type(obj) == int or type(obj) == float:
		if numberTruncate != -1:
			result = ("{:." + str(numberTruncate) + "f}").format(float("%g" % obj)) #obj)
		else:
			result = "%g" % obj #str(obj)

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
		result = "[" + s(obj.x) + " " + s(obj.y) + " " + s(obj.z) + "]"
	elif type(obj) == Quaternion:
		result = "[" + s(obj.x) + " " + s(obj.y) + " " + s(obj.z) + " " + s(obj.w) + "]"
	else:
		result = str(obj)
	
	return result

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

# Utils - files
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

# Utils - alignment
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