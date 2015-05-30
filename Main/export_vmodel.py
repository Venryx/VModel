# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""
Blender exporter for VModel format (.vmodel vdf files).
"""

from io_scene_vmodel import *
from io_scene_vmodel.v import nothing, false, true
from io_scene_vmodel.v import Log, s

import bpy
import mathutils

import shutil
import os
import os.path
import math
import operator
import random
import re

import bmesh

# main
# ==========

def save(operator, context, options):
	#options.filepath = ensure_extension(options.filepath, '.json') # maybe todo: add this back
	source_file = os.path.basename(bpy.data.filepath)

	# todo: make sure this isn't needed
	#if scene.objects.active:
	#	bpy.ops.object.mode_set(mode='OBJECT')

	text = "{^}"
	text += "\nobjects:" + generate_objects({"scene": context.scene, "objects": context.scene.objects}, options)
	text = v.indentLines(text, 1, false)

	'''vdebug.MarkSection("Mesh")
	vdebug.MarkSection("1")
	vdebug.MarkSection("2")
	vdebug.MarkSection("3")
	vdebug.MarkSection("4")
	vdebug.MarkSection("a")
	vdebug.MarkSection("b")
	vdebug.MarkSection("c")
	vdebug.MarkSection("d")
	vdebug.MarkSection("Armature")
	vdebug.MarkSection("Animations")'''

	vdebug.MarkSections()

	v.write_file(options.filepath, text)
	return {'FINISHED'}

# basic object serializers
# ==========

def generate_vec2(vec):
	return "[" + s(vec[0]) + " " + s(vec[1]) + "]"
def generate_vec3(vec, option_flip_yz = false):
	if option_flip_yz:
		return "[" + s(vec[0]) + " " + s(vec[2]) + " " + s(vec[1]) + "]"
	return "[" + s(vec[0]) + " " + s(vec[1]) + " " + s(vec[2]) + "]"
def generate_vec4(vec):
	return "[" + s(vec[0]) + " " + s(vec[1]) + " " + s(vec[2]) + " " + s(vec[3]) + "]"
def generate_quat(quat):
	return "[" + s(quat.x) + " " + s(quat.y) + " " + s(quat.z) + " " + s(quat.w) + "]"

def generate_bool_property(property):
	if property:
		return "true"
	return "false"
def generate_string(s):
	return '"%s"' % s
def generate_string_list(src_list):
	return "[" + " ".join(generate_string(item) for item in src_list) + "]"
def get_mesh_filename(mesh):
	object_id = mesh["data"]["name"]
	#filename = "%s.json" % sanitize(object_id)
	return filename

def generate_vertex(vertex):
	return s(vertex.co.x) + " " + s(vertex.co.y) + " " + s(vertex.co.z)
def generate_normal(n):
	return s(n[0]) + " " + s(n[1]) + " " + s(n[2])
def generate_vertex_color(c):
	return s(c) #"%d" % c

def generate_hex(number):
	return "0x%06x" % number
def hexcolor(c):
	return (int(c[0] * 255) << 16) + (int(c[1] * 255) << 8) + int(c[2] * 255)

# objects
# ==========

meshFirstObjectNames = {}
meshStrings = {}
def generate_objects(data, options):
	meshFirstObjectNames = {}
	meshStrings = {}

	chunks = []
	for obj in data["objects"]:
		if obj.parent == nothing and obj.VModel_export: # root objects
			chunks.append(obj.name + ":" + GetObjectStr(obj, data, options))
	return "{^}\n" + v.indentLines("\n".join(chunks))

#def ConvertObjectToVDF(obj, data, options):
def GetObjectStr(obj, data, options):
	object_string = "{^}"

	'''if options.option_flip_yz:
		ROTATE_X_PI2 = mathutils.Quaternion((1.0, 0.0, 0.0), math.radians(-90.0)).to_matrix().to_4x4()
		matrix_world = ROTATE_X_PI2 * obj.matrix_world
	else:
		matrix_world = obj.matrix_world
	position, rotationQ, scale = matrix_world.decompose()'''
	if options.option_flip_yz:
		ROTATE_X_PI2 = mathutils.Quaternion((1.0, 0.0, 0.0), math.radians(-90.0)).to_matrix().to_4x4()
		matrix_local = ROTATE_X_PI2 * obj.matrix_local
	else:
		matrix_local = obj.matrix_local
	position, rotationQ, scale = matrix_local.decompose()
	'''position = obj.localPosition
	rotationQ = obj.localRotation
	scale = obj.localScale'''

	rotationQ_degrees = v.Quaternion_toDegrees(rotationQ)
	rotation = v.Vector_toDegrees(rotationQ_degrees.to_euler("XYZ")); #ZYX"))

	object_string += "\nposition:" + generate_vec3(position)
	object_string += "\nrotation:" + (generate_vec3(rotation) if options.rotationDataType == "Euler Angle" else generate_quat(rotationQ))
	object_string += "\nscale:" + generate_vec3(scale)

	if obj.type == "MESH":
		vdebug.StartSection("Mesh")
		if obj.data not in meshFirstObjectNames:
			meshFirstObjectNames[obj.data] = obj.name
			meshStrings[obj.data] = GetMeshStr(obj, data["scene"], options)
			object_string += "\nmesh:" + meshStrings[obj.data]
		else:
			object_string += "\nmesh:\"" + meshFirstObjectNames[obj.data] + "\""
		vdebug.EndSection("Mesh")
	elif obj.type == "ARMATURE":
		vdebug.StartSection("Armature")
		object_string += "\narmature:" + GetArmatureStr(obj, obj.data, options)
		vdebug.EndSection("Armature")

		vdebug.StartSection("Animations")
		actions = []
		for action in bpy.data.actions:
			if ActionContainsChannelsForArmature(action, obj.data): # action.groups[0].name == obj.data.name or action.groups[0].name in obj.data.bones: # action == obj.animation_data.action # todo: make sure this is correct
				actions.append(action)
		object_string += "\nanimations:" + GetAnimationsStr(obj, obj.data, actions, options)
		vdebug.EndSection("Animations")

	if obj.VModel_anchorToTerrain:
		object_string += "\nanchorToTerrain:true"

	children_string = "{^}"
	for child in obj.children:
		if child.VModel_export:
			children_string += "\n" + child.name + ":" + GetObjectStr(child, data, options)
	if len(children_string) > len("{^}"):
		object_string += "\nchildren:" + v.indentLines(children_string, 1, false)

	object_string = v.indentLines(object_string, 1, false)

	return object_string

def ActionContainsChannelsForArmature(action, armature):
	armatureBoneNames = [x.name for x in armature.bones]
	for fcurve in action.fcurves:
		boneName = fcurve.data_path[fcurve.data_path.find('"') + 1:fcurve.data_path.find('"', fcurve.data_path.find('"') + 1)]
		if boneName in armatureBoneNames:
			return true
	return false

# mesh
# ==========

def extract_mesh(obj, scene, options):
	if obj.type == "MESH":
		# collapse modifiers into mesh
		mesh = obj.to_mesh(scene, True, "RENDER")
		if not mesh:
			raise Exception("Error, could not get mesh data from object [%s]" % obj.name)

		# preserve original name
		mesh.name = obj.name

		'''if true: #false: #export_single_model:
			if options.option_flip_yz:
				# that's what Blender's native export_obj.py does to flip YZ
				X_ROT = mathutils.Matrix.Rotation(-math.pi / 2, 4, 'X')
				mesh.transform(X_ROT * obj.matrix_world)
			else:
				mesh.transform(obj.matrix_world)'''
					
		mesh.update(calc_tessface=True)

		mesh.calc_normals()
		mesh.calc_tessface()
		#mesh.transform(mathutils.Matrix.Scale(option_scale, 4))
		return mesh

	return nothing

def GetMeshStr(obj, scene, options):
	mesh = extract_mesh(obj, scene, options)

	'''morphs = []
	if options.option_animation_morph:
		original_frame = scene.frame_current # save animation state
		scene_frames = range(scene.frame_start, scene.frame_end + 1, 1)
		for index, frame in enumerate(scene_frames):
			scene.frame_set(frame, 0.0)

			anim_mesh = extract_mesh(obj, scene, options)

			frame_vertices = []
			frame_vertices.extend(anim_mesh.vertices[:])

			if index == 0:
				if options.align_model == 1:
					offset = v.center(frame_vertices)
				elif options.align_model == 2:
					offset = v.bottom(frame_vertices)
				elif options.align_model == 3:
					offset = v.top(frame_vertices)
				else:
					offset = False
			else:
				if offset:
					v.translate(frame_vertices, offset)

			morphVertices = GetVertexesStr(obj, mesh, frame_vertices, options)
			morphs.append(morphVertices)

			# remove temp mesh
			bpy.data.meshes.remove(anim_mesh)
		scene.frame_set(original_frame, 0.0) # restore animation state'''

	vertices = []
	vertices.extend(mesh.vertices[:])
	
	if options.align_model == 1:
		v.center(vertices)
	elif options.align_model == 2:
		bottom(vertices)
	elif options.align_model == 3:
		top(vertices)

	model_string = "{^}"
	model_string += "\nvertices:" + GetVertexesStr(obj, mesh, vertices, options)
	model_string += "\nfaces:" + GetFacesStr(obj, mesh)
	model_string += "\nmaterials:" + GetMaterialsStr(obj, mesh)

	'''morphTargets_string = ""
	nmorphTarget = 0
	if options.option_animation_morph:
		chunks = []
		for i, morphVertices in enumerate(morphs):
			morphTarget = '{name:"%s_%06d" vertices:[%s]}' % ("animation", i, morphVertices)
			chunks.append(morphTarget)

		morphTargets_string = "[^]\n" + v.indentLines("\n".join(chunks))
		nmorphTarget = len(morphs)
	model_string += "\nmorphTargets:" + morphTargets_string'''

	'''vertexColors = len(mesh.vertex_colors) > 0
	mesh_extract_colors = options.option_colors and vertexColors
	if vertexColors:
		active_col_layer = mesh.vertex_colors.active
		if not active_col_layer:
			mesh_extract_colors = false

	ncolor = 0
	colors = {}
	if mesh_extract_colors:
		ncolor = extract_vertex_colors(mesh, colors, ncolor)
	model_string += "\ncolors:" + generate_vertex_colors(colors, options.option_colors)'''

	if obj.find_armature():
		model_string += "\narmature:\"" + obj.find_armature().name + "\""

	model_string = v.indentLines(model_string, 1, false)

	bpy.data.meshes.remove(mesh) # remove temp mesh

	return model_string

def GetVertexesStr(obj, mesh, vertices, options):
	if not options.option_vertices:
		return ""

	vertexInfoByVertexThenLayerThenFace = {}
	for faceIndex, face in enumerate(v.get_faces(mesh)):
		for layerIndex, layer in enumerate(mesh.tessface_uv_textures): # for now, we assume there's only one
			for faceVertexIndex, vertexIndex in enumerate(face.vertices):
				if vertexIndex not in vertexInfoByVertexThenLayerThenFace:
					vertexInfoByVertexThenLayerThenFace[vertexIndex] = {}
				vertexInfo = vertexInfoByVertexThenLayerThenFace[vertexIndex]

				if layerIndex not in vertexInfo:
					vertexInfo[layerIndex] = {}
				layerInfo = vertexInfo[layerIndex]

				if faceIndex not in layerInfo:
					layerInfo[faceIndex] = {}
				faceInfo = layerInfo[faceIndex]

				faceInfo["uvPoint"] = layer.data[faceIndex].uv[faceVertexIndex]

	result = "[^]"
	for vertexIndex, vertex in enumerate(vertices):
		result += "\n{"
		result += "position:[" + generate_vertex(vertex) + "]"
		result += " normal:[" + s(vertex.normal[0]) + " " + s(vertex.normal[1]) + " " + s(vertex.normal[2]) + "]"

		uvsStr = ""
		if options.option_uv_coords and len(mesh.uv_textures) > 0 and (not mesh.uv_textures.active == nothing):
			''' # this approach took 12.79 seconds
			for faceIndex, face in enumerate(v.get_faces(mesh)):
				for layerIndex, layer in enumerate(mesh.tessface_uv_textures): # for now, we assume there's only one
					for faceVertexIndex, vertexIndex2 in enumerate(face.vertices):
						if vertexIndex == vertexIndex2:
							vec = layer.data[faceIndex].uv[faceVertexIndex]
							result += " uv" + (s(layerIndex) if layerIndex > 0 else "") + "_face" + s(faceIndex) + ":[" + s(vec[0]) + " " + s(vec[1]) + "]" #s(posComp[0]) + " " + s(posComp[1]) + "]"
			'''

			# this approach took .69 seconds
			vertexInfo = vertexInfoByVertexThenLayerThenFace[vertexIndex]
			for layerIndex, layerInfo in sorted(vertexInfo.items()):
				layerFaceUVValues = []
				for faceIndex, faceInfo in sorted(layerInfo.items()):
					if not v.any(layerFaceUVValues, lambda a:a["uvPoint"][0] == faceInfo["uvPoint"][0] and a["uvPoint"][1] == faceInfo["uvPoint"][1]):
						layerFaceUVValues.append(faceInfo)
				if len(layerFaceUVValues) == 1:
					uvsStr += " uv" + (s(layerIndex + 1) if layerIndex > 0 else "") + ":[" + s(faceInfo["uvPoint"][0]) + " " + s(faceInfo["uvPoint"][1]) + "]"
				else:
					for faceIndex, faceInfo in sorted(layerInfo.items()):
						uvsStr += " uv" + (s(layerIndex + 1) if layerIndex > 0 else "") + "_face" + s(faceIndex) + ":[" + s(faceInfo["uvPoint"][0]) + " " + s(faceInfo["uvPoint"][1]) + "]"
		result += uvsStr

		if obj.find_armature() != nothing:
			result += " boneWeights:" + GetBoneWeightsStr(obj, mesh, vertex)
			
		result += "}"

	result = v.indentLines(result, 1, false)
	return result

def GetBoneWeightsStr(obj, mesh, vertex):
	armatureObj = obj.find_armature()
	bone_names = [bone.name for bone in armatureObj.pose.bones]

	result = "{"
	for group in vertex.groups: # a 'group' is basically a bone-weight assignment
		index = group.group
		if obj.vertex_groups[index].name in bone_names:
			result += (" " if len(result) > 1 else "") + obj.vertex_groups[index].name + ":" + s(group.weight)
	result += "}"

	return result

# vertex colors (to become part of "mesh" section)
# ==========

'''
def extract_vertex_colors(mesh, colors, count):
	color_layer = mesh.tessface_vertex_colors.active.data

	for face_index, face in enumerate(v.get_faces(mesh)):
		face_colors = color_layer[face_index]
		face_colors = face_colors.color1, face_colors.color2, face_colors.color3, face_colors.color4

		for c in face_colors:
			key = hexcolor(c)
			if key not in colors:
				colors[key] = count
				count += 1

	return count

def generate_vertex_colors(colors, options):
	if not options.option_colors:
		return ""

	chunks = []
	for key, index in sorted(colors.items(), key=operator.itemgetter(1)):
		chunks.append(key)

	return "[" + " ".join(generate_vertex_color(c) for c in chunks) + "]"
'''

# faces
# ==========

def GetFacesStr(obj, mesh):
	result = "["
	for faceIndex, face in enumerate(v.get_faces(mesh)):
		'''bpy.ops.object.mode_set(mode = "EDIT") # go to edit mode to create bmesh
		bm = bmesh.from_edit_mesh(obj.data) # create bmesh object from object mesh
		#bmFace = bm.faces[faceIndex]
		for faceIndex2, face2 in enumerate(bm.faces):
			__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})
		# if bmFace.material_index == materialIndex or materialIndex == -1:
		bpy.ops.object.mode_set(mode = oldMode)'''

		'''if face.material_index == materialIndex or materialIndex == -1:
			result += (" " if len(result) > 1 else "") + "[" #result += (" " if faceIndex != 0 else "") + "["
			for vertexIndex, vertex in enumerate(face.vertices):
				result += (" " if vertexIndex != 0 else "") + s(vertex)
			result += "]"'''

		result += (" " if faceIndex != 0 else "") + "["
		for vertexIndex, vertex in enumerate(face.vertices):
			result += (" " if vertexIndex != 0 else "") + s(vertex)
		if face.material_index > 0:
			result += " {material:" + s(face.material_index) + "}"
		result += "]"
	result += "]"
	return result

# materials
# ==========

def GetMaterialsStr(obj, mesh):
	result = "[^]"
	for materialIndex, material in enumerate(obj.data.materials):
		result += "\n{diffuseColor:\"" + ColorToHexStr(material.diffuse_color) + "\""
		if material.node_tree != nothing: # todo: make sure this is correct
			for node in material.node_tree.nodes:
				if node.type == "TEX_IMAGE": # for now, we just assume that the first image-texture node holds the texture actually used
					textureBaseName = re.sub("[.0-9]+$", "", node.image.name)
					result += " texture:\"" + textureBaseName + "\""
		result += "}"

	result = v.indentLines(result, 1, false)

	return result

def ColorToHexStr(color):
	result = ""
	for colorComp in color:
		# compensate for gamma-correction thing (full white was showing up as "cccccc" (204, 204, 204) before)
		# see: http://blenderartists.org/forum/showthread.php?320221-Converting-HEX-colors-to-blender-RGB
		colorComp *= 255 / 204
		compStr = s(hex(int(colorComp * 255)))[2:]
		while len(compStr) < 2:
			compStr = "0" + compStr
		result += compStr
	return result

# armature
# ==========

def GetArmatureStr(obj, armature, options):
	result = "{^}"

	# force bone positions/parenting/etc. to update (if user just moved some in edit mode, and hasn't left to object mode yet)
	oldMode = bpy.context.object.mode
	bpy.ops.object.mode_set(mode = "OBJECT")
	bpy.ops.object.mode_set(mode = oldMode)

	# select armature, and change to edit mode
	oldActiveObject = bpy.context.scene.objects.active
	bpy.context.scene.objects.active = obj
	oldMode = bpy.context.object.mode
	bpy.ops.object.mode_set(mode = "EDIT")

	bones_string = "{^}"
	for poseBone in obj.pose.bones: #armature.bones
		bone = poseBone.bone
		if obj.data.edit_bones[bone.name].parent == nothing:
			bones_string += "\n" + v.indentLines(GetBoneStr(obj, armature, bone, options))
			#bones_string += "\n" + v.indentLines(GetBoneStr(obj, armature, poseBone, options))
	result += "\n" + v.indentLines("bones:" + bones_string)

	# revert
	bpy.ops.object.mode_set(mode = oldMode)
	bpy.context.scene.objects.active = oldActiveObject

	return result

def GetBoneStr(obj, armature, bone, options):
#def GetBoneStr(obj, armature, poseBone, options):
#	bone = poseBone.bone

	hierarchy = []
	armature_matrix = obj.matrix_world
	#poseBones = obj.pose.bones #armature.bones

	'''if bone.parent is nothing:
		bone_matrix = armature_matrix * bone.matrix_local
	else:
		parent_matrix = armature_matrix * bone.parent.matrix_local
		bone_matrix = armature_matrix * bone.matrix_local
		bone_matrix = parent_matrix.inverted() * bone_matrix'''
	'''if bone.parent is nothing:
		bone_matrix = v.getBoneLocalMatrix(bone) #bone.matrix_local
	else:
		parent_matrix = v.getBoneLocalMatrix(bone.parent) #bone.parent.matrix_local
		bone_matrix = v.getBoneLocalMatrix(bone) #bone.matrix_local
		bone_matrix = parent_matrix.inverted() * bone_matrix'''
	bone_matrix = v.getBoneLocalMatrix(bone, true, false) #poseBone)
	if bone.parent == nothing:
		bone_matrix = v.fixMatrixForRootBone(bone_matrix)
	pos, rotQ, scl = bone_matrix.decompose()

	#__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

	'''pos = obj.location
	rotQ = obj.rotation_quaternion
	scl = obj.scale'''

	#pos = bone.head_local
	#pos, rotQ, scl = bone.matrix.to_4x4().decompose()
	#rotQ, scl = bone.matrix.to_4x4().decompose()[1:]

	# at-rest bones, even if they have 'rotation', don't actually apply their rotation to their descendent bones (i.e. the descendents local-position is actually just the position relative to the armature)
	# so undo applying of parent-bone matrix to the current bone's location
	# pos = bone.matrix_local.decompose()[0] if bone.parent is nothing else bone.matrix_local.decompose()[0] - bone.parent.matrix_local.decompose()[0]

	# for some reason, the "rest" or "base" rotation of a bone is [-.5 0 0 0] (relative to the world) (i.e. rotated forward 90 degrees--with the tail/tip/non-core-end having a higher y value)
	# we're going to correct that, so that the stored rotation is the rotation to get from the world-rotation (identity/none/[0 0 0 1]) to the bone rotation
	#rotQ = mathutils.Quaternion([.707107, .707107, 0, 0]).inverted() * rotQ # w, x, y, z
	'''rotQ = mathutils.Quaternion([.707107, .707107, 0, 0]).rotation_difference(rotQ)
	yOld = rotQ.y
	rotQ.y = -rotQ.z
	rotQ.z = yOld'''

	rotQ_degrees = v.Quaternion_toDegrees(rotQ)
	rotationEuler = v.Vector_toDegrees(rotQ_degrees.to_euler("XYZ"))

	#parentNameStr = ("\"" + obj.data.edit_bones[bone.name].parent.name + "\"") if obj.data.edit_bones[bone.name].parent != nothing else "null"
	positionStr = ""
	rotationStr = ""
	scaleStr = ""
	if options.option_flip_yz:
		positionStr = "[" + s(pos.x) + " " + s(pos.z) + " " + s(-pos.y) + "]"
		rotationStr = ("[" + s(rotationEuler.x) + " " + s(rotationEuler.z) + " " + s(-rotationEuler.y) + "]") if options.rotationDataType == "Euler Angle" else ("[" + s(rotQ.x) + " " + s(rotQ.z) + " " + s(-rotQ.y) + " " + s(rotQ.w) + "]")
		scaleStr = "[" + s(scl.x) + " " + s(scl.z) + " " + s(scl.y) + "]"
	else:
		positionStr = s(pos)
		rotationStr = s(rotationEuler) if options.rotationDataType == "Euler Angle" else s(rotQ)
		scaleStr = s(scl)

	childrenStr = ""
	if len(obj.data.edit_bones[bone.name].children) > 0:
		for childEditBone in obj.data.edit_bones[bone.name].children:
			childrenStr += "\n" + v.indentLines(GetBoneStr(obj, armature, next(a for a in armature.bones if a.name == childEditBone.name), options))

	result = bone.name + ":{position:" + positionStr + " rotation:" + rotationStr + " scale:" + scaleStr + (" children:{^}" if len(childrenStr) > 0 else "") + "}" + childrenStr
	#result = bone.name + ":{position:" + positionStr + " scale:" + scaleStr + (" children:{^}" if len(childrenStr) > 0 else "") + "}" + childrenStr

	return result

# skeletal animation
# ==========

def GetAnimationsStr(obj, armature, actions, options):
	result = "{^}"

	# todo: change to pose mode (or something like that)
	for action in actions:
		result += "\n" + action.name + ":" + GetActionStr(obj, armature, action, options)
	result = v.indentLines(result, 1, false)
	# todo: revert mode

	return result

def GetActionStr(obj, armature, action, options):
	if not options.option_animation_skeletal or len(bpy.data.actions) == 0:
		return ""
	if obj is None or armature is None:
		return "", 0

	# todo: add scaling influences

	vdebug.StartSection()

	# select object, change to pose mode, select action, change to dopesheet editor area type, and change to action mode
	oldActiveObject = bpy.context.scene.objects.active
	bpy.context.scene.objects.active = obj
	oldMode = bpy.context.object.mode
	bpy.ops.object.mode_set(mode = "POSE")
	oldContext = bpy.context.area.type
	bpy.context.area.type = "DOPESHEET_EDITOR"
	oldSpaceDataMode = bpy.context.space_data.mode
	bpy.context.space_data.mode = "ACTION"
	oldActiveAction = bpy.context.area.spaces.active.action #if "action" in bpy.context.area.spaces.active else nothing
	bpy.context.area.spaces.active.action = action
	oldFrame = bpy.data.scenes[0].frame_current

	armature_matrix = obj.matrix_world #obj.matrix_local
	fps = bpy.data.scenes[0].render.fps
	start_frame = action.frame_range[0]
	end_frame = action.frame_range[1]
	frame_length = end_frame - start_frame
	used_frames = int(frame_length) + 1

	bonePropertyChannelsSet = {}
	for boneIndex, poseBone in enumerate(obj.pose.bones):
		bonePropertyChannels = {}
		bonePropertyChannels["location"] = GetBoneChannels(action, poseBone, "location")
		bonePropertyChannels["rotation"] = GetBoneChannels(action, poseBone, "rotation_quaternion")
		if len(bonePropertyChannels["rotation"]) == 0:
			bonePropertyChannels["rotationChannels"] = GetBoneChannels(action, poseBone, "rotation_euler")
		bonePropertyChannels["scale"] = GetBoneChannels(action, poseBone, "scale")
		bonePropertyChannelsSet[poseBone.name] = bonePropertyChannels

	vdebug.EndSection("1")

	keys = {}
	for frame_i in range(0, used_frames): # process all frames

		vdebug.StartSection()

		# compute the index of the current frame (snap the last index to the end)
		frame = start_frame + frame_i
		if frame_i == used_frames - 1:
			frame = end_frame

		# compute the time of the frame
		if options.option_frame_index_as_time:
			time = frame - start_frame
		else:
			time = (frame - start_frame) / fps

		# let blender compute the pose bone transformations
		bpy.data.scenes[0].frame_set(frame)

		vdebug.EndSection("2")

		# process all bones for the current frame
		for boneIndex, poseBone in enumerate(obj.pose.bones):
			vdebug.StartSection()

			if boneIndex not in keys:
				keys[boneIndex] = []

			# extract the bone transformations
			'''if poseBone.parent is None:
				bone_matrix = armature_matrix * poseBone.matrix
			else:
				parent_matrix = armature_matrix * poseBone.parent.matrix
				bone_matrix = armature_matrix * poseBone.matrix
				bone_matrix = parent_matrix.inverted() * bone_matrix'''
			'''if poseBone.parent is None:
				bone_matrix = poseBone.matrix
			else:
				parent_matrix = poseBone.parent.matrix
				bone_matrix = poseBone.matrix
				bone_matrix = parent_matrix.inverted() * bone_matrix'''
			#bone_matrix = poseBone.matrix
			#bone_matrix = armature_matrix * poseBone.matrix
			#bone_matrix = v.getBoneLocalMatrix(poseBone, false)
			bone_matrix = v.getBoneLocalMatrix(poseBone) # maybe temp; bake orientation as relative to armature, as Unity API wants it in the end
			pos, rotQ, scl = bone_matrix.decompose()

			'''pos = poseBone.location
			rotQ = poseBone.rotation_quaternion
			scl = poseBone.scale'''

			#pos, rotQ, scl = poseBone.matrix.decompose()
			#__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

			# for some reason, the "rest" or "base" rotation of a bone is [-.5 0 0 0] (relative to the world) (i.e. rotated forward 90 degrees--with the tail/tip/non-core-end having a higher y value)
			# we're going to correct that, so that the stored rotation is the rotation to get from the world-rotation (identity/none/[0 0 0 1]) to the bone rotation
			#rotQ = mathutils.Quaternion([.707107, .707107, 0, 0]).inverted() * rotQ # w, x, y, z
			'''rotQ = mathutils.Quaternion([.707107, .707107, 0, 0]).rotation_difference(rotQ)
			yOld = rotQ.y
			rotQ.y = -rotQ.z
			rotQ.z = yOld'''

			rotQ_degrees = v.Quaternion_toDegrees(rotQ)
			rotEuler = v.Vector_toDegrees(rotQ_degrees.to_euler("XYZ"))

			bonePropertyChannels = bonePropertyChannelsSet[poseBone.name]

			#isKeyframe = has_keyframe_at(channels_location[boneIndex], frame) or has_keyframe_at(channels_rotation[boneIndex], frame) or has_keyframe_at(channels_scale[boneIndex], frame)
			isKeyframe = has_keyframe_at(bonePropertyChannels["location"], frame) or has_keyframe_at(bonePropertyChannels["rotation"], frame) or has_keyframe_at(bonePropertyChannels["scale"], frame)

			vdebug.EndSection("3")

			#__import__('code').interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})
			#isKeyframe = true

			if isKeyframe:
				vdebug.StartSection()

				'''pchange = has_keyframe_at(bonePropertyChannels["location"], frame)
				rchange = has_keyframe_at(bonePropertyChannels["rotation"], frame)
				schange = has_keyframe_at(bonePropertyChannels["scale"], frame)'''
				pchange = true
				rchange = true
				schange = true

				if options.option_flip_yz:
					px, py, pz = pos.x, pos.z, -pos.y
					rotEuler = [rotEuler[0], rotEuler[2], -rotEuler[1]]
					rx, ry, rz, rw = rotQ.x, rotQ.z, -rotQ.y, rotQ.w
					sx, sy, sz = scl.x, scl.z, scl.y
				else:
					px, py, pz = pos.x, pos.y, pos.z
					rx, ry, rz, rw = rotQ.x, rotQ.y, rotQ.z, rotQ.w
					sx, sy, sz = scl.x, scl.y, scl.z

				posStr = "[" + s(px) + " " + s(py) + " " + s(pz) + "]"
				rotStr = generate_vec3(rotEuler) if options.rotationDataType == "Euler Angle" else ("[" + s(rx) + " " + s(ry) + " " + s(rz) + " " + s(rw) + "]")
				scaleStr = "[" + s(sx) + " " + s(sy) + " " + s(sz) + "]"

				vdebug.EndSection("4")
				vdebug.StartSection()

				# START-FRAME: needs position, rotation, and scale attributes (required frame)
				if frame == start_frame:
					keyframe = s(time) + ':{position:' + posStr + ' rotation:' + rotStr + ' scale:' + scaleStr + '}'
					keys[boneIndex].append(keyframe)

				# END-FRAME: needs position, rotation, and scale attributes with animation length
				# (required frame)
				elif frame == end_frame:
					keyframe = s(time) + ':{position:' + posStr + ' rotation:' + rotStr + ' scale:' + scaleStr + '}'
					keys[boneIndex].append(keyframe)

				# MIDDLE-FRAME: needs only one of the attributes, can be an empty frame
				# (optional frame)
				elif pchange == True or rchange == true:
					keyframe = s(time) + ':{'
					if pchange == true:
						keyframe = keyframe + 'position:' + posStr
					if rchange == true:
						keyframe = keyframe + ' rotation:' + rotStr
					if schange == true:
						keyframe = keyframe + ' scale:' + scaleStr
					keyframe = keyframe + '}'

					keys[boneIndex].append(keyframe)

				vdebug.EndSection("5")

	vdebug.StartSection()

	# gather data
	parents = []
	bone_index = 0
	for boneIndex, poseBone in enumerate(obj.pose.bones):
		if len(keys[boneIndex]) == 0:
			continue
		keys_string = "\n\t".join(keys[boneIndex])
		parent = poseBone.name + ':{^}\n\t%s' % (keys_string)
		parents.append(parent)
	boneKeyframesStr = "{^}\n" + v.indentLines("\n".join(parents))

	if options.option_frame_index_as_time:
		length = frame_length
	else:
		length = frame_length / fps

	vdebug.EndSection("6")
	vdebug.StartSection()

	animation_string = "{^}"
	#animation_string += "\nname:" + action.name
	animation_string += "\nfps:" + s(fps)
	animation_string += "\nlength:" + s(length)
	animation_string += "\nboneKeyframes:" + boneKeyframesStr
	animation_string = v.indentLines(animation_string, 1, false)

	bpy.data.scenes[0].frame_set(start_frame)

	# revert
	bpy.data.scenes[0].frame_set(oldFrame)
	bpy.context.area.spaces.active.action = oldActiveAction
	bpy.context.space_data.mode = oldSpaceDataMode
	bpy.context.area.type = oldContext
	bpy.ops.object.mode_set(mode = oldMode)
	bpy.context.scene.objects.active = oldActiveObject
	
	vdebug.EndSection("7")

	return animation_string

'''
def find_channels(action, bone, channel_type):
	bone_name = bone.name
	ngroups = len(action.groups)
	result = []
	if ngroups > 0: # variant 1: channels grouped by bone names

		# variant a: groups are per-bone
		for group_index in range(ngroups):# find the channel group for the given bone
			if action.groups[i].name == bone_name:
				for channel in action.groups[group_index].channels: # get all desired channels in that group
					if channel_type in channel.data_path:
						result.append(channel)
		
		''#'
		# variant b: groups are per-armature
		for groupIndex, group in action.groups.items():
			for channel in action.groups[groupIndex].channels:
				# example: data_path == "pose.bones["ELEPHANt_ear_L_2"].location" (important note: there can be three location channels: one for x, one for y, and one for z)
				if ("['" + bone_name + "']") in action.groups[i].name and channel_type in channel.data_path:
					result.append(channel)
		''#'

	else: # variant 2: no channel groups, bone names included in channel names
		bone_label = '"%s"' % bone_name
		for channel in action.fcurves:
			data_path = channel.data_path
			if bone_label in data_path and channel_type in data_path:
				result.append(channel)

	__import__("code").interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

	return result
'''

def GetBoneChannels(action, bone, channelType):
	result = []

	vdebug.StartSection()

	#next((a for a in action.groups if a.name == bone.name), nothing) != nothing:
	if len(action.groups) > 0 and v.any(action.groups, lambda a:a.name == bone.name): # variant 1: groups:[{name:"Bone1", channels:[{data_path:"location"}]}]
		for groupIndex, group in action.groups.items(): # find the channel group for the given bone
			if group.name == bone.name:
				for channel in group.channels: # get all desired channels in that group
					if channelType in channel.data_path:
						result.append(channel)
	elif len(action.groups) > 0: # variant 2: groups:[{name:"Armature", channels:[{data_path:"pose.bones[\"Bone1\"].location"}]}]
		for groupIndex, group in action.groups.items():
			for channel in group.channels:
				# example: data_path == "pose.bones["ELEPHANt_ear_L_2"].location" (important note: there can be three location channels: one for x, one for y, and one for z)
				if ("[\"" + bone.name + "\"]") in channel.data_path and channelType in channel.data_path:
					result.append(channel)
	else: # variant 3: fcurves:[{data_path:"pose.bones[\"Bone1\"].location"}]
		bone_label = '"%s"' % bone.name
		for channel in action.fcurves:
			data_path = channel.data_path
			if bone_label in data_path and channelType in data_path:
				result.append(channel)

	vdebug.EndSection("a")

	return result

def find_keyframe_at(channel, frame):
	for keyframe in channel.keyframe_points:
		if keyframe.co[0] == frame:
			return keyframe
	return nothing

def has_keyframe_at(channels, frame):
	for channel in channels:
		if not find_keyframe_at(channel, frame) is nothing:
			return true
	return false

def handle_position_channel(channel, frame, position):
	change = false
	if channel.array_index in [0, 1, 2]:
		for keyframe in channel.keyframe_points:
			if keyframe.co[0] == frame:
				change = true
		value = channel.evaluate(frame)
		if channel.array_index == 0:
			position.x = value
		if channel.array_index == 1:
			position.y = value
		if channel.array_index == 2:
			position.z = value
	return change

def position(bone, frame, action, armatureMatrix):
	position = mathutils.Vector((0,0,0))
	change = False
	ngroups = len(action.groups)
	if ngroups > 0:
		index = 0
		for i in range(ngroups):
			if action.groups[i].name == bone.name:
				index = i
		for channel in action.groups[index].channels:
			if "location" in channel.data_path:
				hasChanged = handle_position_channel(channel, frame, position)
				change = change or hasChanged
	else:
		bone_label = '"%s"' % bone.name
		for channel in action.fcurves:
			data_path = channel.data_path
			if bone_label in data_path and "location" in data_path:
				hasChanged = handle_position_channel(channel, frame, position)
				change = change or hasChanged

	position = position * bone.matrix_local.inverted()
	if bone.parent == None:
		position.x += bone.head.x
		position.y += bone.head.y
		position.z += bone.head.z
	else:
		parent = bone.parent
		parentInvertedLocalMatrix = parent.matrix_local.inverted()
		parentHeadTailDiff = parent.tail_local - parent.head_local
		position.x += (bone.head * parentInvertedLocalMatrix).x + parentHeadTailDiff.x
		position.y += (bone.head * parentInvertedLocalMatrix).y + parentHeadTailDiff.y
		position.z += (bone.head * parentInvertedLocalMatrix).z + parentHeadTailDiff.z

	return armatureMatrix * position, change

def handle_rotation_channel(channel, frame, rotation):
	change = false
	if channel.array_index in [0, 1, 2, 3]:
		for keyframe in channel.keyframe_points:
			if keyframe.co[0] == frame:
				change = true

		value = channel.evaluate(frame)
		if channel.array_index == 1:
			rotation.x = value
		elif channel.array_index == 2:
			rotation.y = value
		elif channel.array_index == 3:
			rotation.z = value
		elif channel.array_index == 0:
			rotation.w = value

	return change

def rotation(bone, frame, action, armatureMatrix):
	# TODO: calculate rotation also from rotation_euler channels
	rotation = mathutils.Vector((0,0,0,1))
	change = false
	ngroups = len(action.groups)
	if ngroups > 0: # animation grouped by bones
		index = -1
		for i in range(ngroups):
			if action.groups[i].name == bone.name:
				index = i
		if index > -1:
			for channel in action.groups[index].channels:
				if "quaternion" in channel.data_path:
					hasChanged = handle_rotation_channel(channel, frame, rotation)
					change = change or hasChanged
	else: # animation in raw fcurves
		bone_label = '"%s"' % bone.name
		for channel in action.fcurves:
			data_path = channel.data_path
			if bone_label in data_path and "quaternion" in data_path:
				hasChanged = handle_rotation_channel(channel, frame, rotation)
				change = change or hasChanged

	rot3 = rotation.to_3d()
	rotation.xyz = rot3 * bone.matrix_local.inverted()
	rotation.xyz = armatureMatrix * rotation.xyz

	return rotation, change