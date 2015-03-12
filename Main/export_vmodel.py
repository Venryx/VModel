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

import bpy
import mathutils

import shutil
import os
import os.path
import math
import operator
import random

from io_scene_vmodel import *
from io_scene_vmodel.v import nothing, false, true
from io_scene_vmodel.v import Log, s

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
	text = v.indent_lines(text, 1, false)

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

def generate_objects(data, options):
	chunks = []
	for obj in data["objects"]:
		if obj.parent == nothing and obj.VModel_export: # root objects
			chunks.append(obj.name + ":" + ConvertObjectToVDF(obj, data, options))
	return "{^}\n" + v.indent_lines("\n".join(chunks))

def ConvertObjectToVDF(obj, data, options):
	object_string = "{^}"

	if options.option_flip_yz:
		ROTATE_X_PI2 = mathutils.Quaternion((1.0, 0.0, 0.0), math.radians(-90.0)).to_matrix().to_4x4()
		matrix_world = ROTATE_X_PI2 * obj.matrix_world
	else:
		matrix_world = obj.matrix_world
	position, rotationQ, scale = matrix_world.decompose()
	rotationQ = v.Quaternion_toDegrees(rotationQ)
	rotation = v.Vector_toDegrees(rotationQ.to_euler("ZYX"))

	object_string += "\nposition:" + generate_vec3(position)
	object_string += "\nrotation:" + (generate_vec3(rotation) if options.rotationDataType == "Euler Angle" else generate_quat(rotationQ))
	object_string += "\nscale:" + generate_vec3(scale)

	if obj.type == "MESH":
		object_string += "\nmesh:" + generate_mesh_string(obj, data["scene"], options)
	elif obj.type == "ARMATURE":
		object_string += "\narmature:" + ConvertArmatureToVDF(obj, obj.data, options)

		actions = []
		for action in bpy.data.actions:
			if action.groups[0].name in obj.data.bones:
				actions.append(action)
		object_string += "\nanimations:" + ConvertActionsToVDF(obj, obj.data, actions, options)

	children_string = "{^}"
	for child in obj.children:
		if child.VModel_export:
			children_string += "\n" + child.name + ":" + ConvertObjectToVDF(child, data, options)
	if len(children_string) > len("{^}"):
		object_string += "\nchildren:" + v.indent_lines(children_string, 1, false)

	object_string = v.indent_lines(object_string, 1, false)

	return object_string

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

		if true: #false: #export_single_model:
			if options.option_flip_yz:
				# that's what Blender's native export_obj.py does to flip YZ
				X_ROT = mathutils.Matrix.Rotation(-math.pi / 2, 4, 'X')
				mesh.transform(X_ROT * obj.matrix_world)
			else:
				mesh.transform(obj.matrix_world)
					
		mesh.update(calc_tessface=True)

		mesh.calc_normals()
		mesh.calc_tessface()
		#mesh.transform(mathutils.Matrix.Scale(option_scale, 4))
		return mesh

	return nothing

def generate_mesh_string(obj, scene, options):
	mesh = extract_mesh(obj, scene, options)

	'''
	morphs = []
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
		scene.frame_set(original_frame, 0.0) # restore animation state
	'''

	vertices = []
	vertices.extend(mesh.vertices[:])

	vertexColors = len(mesh.vertex_colors) > 0
	mesh_extract_colors = options.option_colors and vertexColors
	if vertexColors:
		active_col_layer = mesh.vertex_colors.active
		if not active_col_layer:
			mesh_extract_colors = false
	
	ncolor = 0
	colors = {}
	if mesh_extract_colors:
		ncolor = extract_vertex_colors(mesh, colors, ncolor)

	morphTargets_string = ""
	nmorphTarget = 0
	if options.option_animation_morph:
		chunks = []
		for i, morphVertices in enumerate(morphs):
			morphTarget = '{name:"%s_%06d" vertices:[%s]}' % ("animation", i, morphVertices)
			chunks.append(morphTarget)

		morphTargets_string = "[^]\n" + v.indent_lines("\n".join(chunks))
		nmorphTarget = len(morphs)

	if options.align_model == 1:
		v.center(vertices)
	elif options.align_model == 2:
		bottom(vertices)
	elif options.align_model == 3:
		top(vertices)

	model_string = "{^}"
	model_string += "\nvertices:" + GetVertexesStr(obj, mesh, vertices, options)
	model_string += "\nfaces:" + GetFacesStr(obj, mesh)
	#model_string += "\nmorphTargets:" + morphTargets_string
	#model_string += "\ncolors:" + generate_vertex_colors(colors, options.option_colors)
	if obj.find_armature():
		model_string += "\narmature:\"" + obj.find_armature().name + "\""

	model_string = v.indent_lines(model_string, 1, false)

	bpy.data.meshes.remove(mesh) # remove temp mesh

	return model_string

def GetVertexesStr(obj, mesh, vertices, options):
	if not options.option_vertices:
		return ""

	result = "[^]"
	for i, vertex in enumerate(vertices):
		result += "\n{"
		result += "position:[" + generate_vertex(vertex) + "]"
		result += " normal:[" + s(vertex.normal[0]) + " " + s(vertex.normal[1]) + "]"

		uvsStr = ""
		nuvs = []
		uv_layers = []
		if options.option_uv_coords and len(mesh.uv_textures) > 0 and (not mesh.uv_textures.active == nothing):
			for index, layer in enumerate(mesh.tessface_uv_textures):
				if len(uv_layers) <= index:
					uvs = {}
					count = 0
					uv_layers.append(uvs)
					nuvs.append(count)
				else:
					uvs = uv_layers[index]
					count = nuvs[index]

				uv_layer = layer.data
				for face_index, face in enumerate(v.get_faces(mesh)):
					for uv_index, uv in enumerate(uv_layer[face_index].uv):
						key = v.veckey2d(uv)
						if key not in uvs:
							uvs[key] = count
							count += 1
				nuvs[index] = count
			for faceIndex, face in enumerate(v.get_faces(mesh)):
				for layer_index, uvs in enumerate(uv_layers): # for now, we assume there's only one
					vecs = []
					uv_layer = mesh.tessface_uv_textures[layer_index].data
					for vec in uv_layer[faceIndex].uv:
						vecs.append(vec)

					faceVertexIndex = 0
					for i2 in face.vertices:
						if i2 == i:
							vec = vecs[faceVertexIndex]
							result += " uv" + (s(layer_index) if layer_index > 0 else "") + "_face" + s(faceIndex) + ":[" + s(vec[0]) + " " + s(vec[1]) + "]" #s(posComp[0]) + " " + s(posComp[1]) + "]"
						faceVertexIndex += 1
		result += " boneWeights:" + GetBoneWeightsStr(obj, mesh, vertex) + "}"

	result = v.indent_lines(result, 1, false)
	return result

def GetBoneWeightsStr(obj, mesh, vertex):
	armature_object = obj.find_armature()
	bone_names = [bone.name for bone in armature_object.pose.bones]

	obj_orig = nothing
	for obj2 in bpy.data.objects: # find the original object
		if obj2.name == mesh.name or obj2 == obj:
			obj_orig = obj2
			break

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
		result += (" " if faceIndex != 0 else "") + "["
		for i in range(len(face.vertices)):
			result += (" " if i != 0 else "") + s(face.vertices[i])
		result += "]"
	result += "]"
	return result

# armature
# ==========

def ConvertArmatureToVDF(obj, armature, options):
	result = "{^}"

	bones_string, nbone = generate_bones(obj, armature, options)
	result += "\nbones:" + bones_string

	result = v.indent_lines(result, 1, false)
	return result

def generate_bones(armature_object, armature, options):
	if not options.option_bones:
		return "", 0
	if armature_object is nothing:
		return "", 0

	hierarchy = []
	armature_matrix = armature_object.matrix_world
	pose_bones = armature_object.pose.bones
	#pose_bones = armature.bones

	for pose_bone in pose_bones:
		armature_bone = pose_bone.bone
		#armature_bone = pose_bone
		bonePos = armature_matrix * armature_bone.head_local
		boneIndex = nothing

		if armature_bone.parent is nothing:
			bone_matrix = armature_matrix * armature_bone.matrix_local
			bone_index = -1
		else:
			parent_matrix = armature_matrix * armature_bone.parent.matrix_local
			bone_matrix = armature_matrix * armature_bone.matrix_local
			bone_matrix = parent_matrix.inverted() * bone_matrix

			bone_index = i = 0
			for pose_parent in pose_bones:
				armature_parent = pose_parent.bone
				#armature_parent = pose_parent
				if armature_parent.name == armature_bone.parent.name:
					bone_index = i
				i += 1

		pos, rotQ, scl = bone_matrix.decompose()
		rotQ = v.Quaternion_toDegrees(rotQ)
		rotationEuler = v.Vector_toDegrees(rotQ.to_euler("XYZ"))

		parentName = armature_bone.parent.name if armature_bone.parent != nothing else "null"
		positionStr = ""
		rotationStr = ""
		scaleStr = ""
		if options.option_flip_yz:
			positionStr = "[" + s(pos.x) + " " + s(pos.z) + " " + s(-pos.y) + "]"
			rotationStr = ("[" + s(rotationEuler.x) + " " + s(rotationEuler.z) + " " + s(-rotationEuler.y) + "]") if options.rotationDataType == "Euler Angle" else ("[" + s(rotQ.x) + " " + s(rotQ.z) + " " + s(-rotQ.y) + " " + s(rotQ.w) + "]")
			scaleStr = "[" + s(scl.x) + " " + s(scl.z) + " " + s(scl.y) + "]"
		else:
			positionStr = "[" + s(pos.x) + " " + s(pos.y) + " " + s(pos.z) + "]"
			rotationStr = ("[" + s(rotationEuler.x) + " " + s(rotationEuler.y) + " " + s(rotationEuler.z) + "]") if options.rotationDataType == "Euler Angle" else ("[" + s(rotQ.x) + " " + s(rotQ.y) + " " + s(rotQ.z) + " " + s(rotQ.w) + "]")
			scaleStr = "[" + s(scl.x) + " " + s(scl.y) + " " + s(scl.z) + "]"

		hierarchy.append(armature_bone.name + ":{parent:" + parentName + " position:" + positionStr + " rotation:" + rotationStr + " scale:" + scaleStr + "}")

	bones_string = "{^}\n" + v.indent_lines(" ".join(hierarchy), 1)
	
	return bones_string, len(pose_bones)

# skeletal animation
# ==========

def ConvertActionsToVDF(armature_object, armature, actions, options):
	result = "{^}"
	for action in actions:
		result += "\n" + action.name + ":" + ConvertActionToVDF(armature_object, armature, action, options)
	result = v.indent_lines(result, 1, false)
	return result

def ConvertActionToVDF(armature_object, armature, action, options):
	if not options.option_animation_skeletal or len(bpy.data.actions) == 0:
		return ""
	if armature_object is None or armature is None:
		return "", 0

	# todo: add scaling influences

	# get current context and then switch to dopesheet temporarily
	current_context = bpy.context.area.type
	bpy.context.area.type = "DOPESHEET_EDITOR"
	bpy.context.space_data.mode = "ACTION"	
	
	oldActiveObject = bpy.context.scene.objects.active
	bpy.context.scene.objects.active = armature_object # set active object (needed to set active action)
	#oldActiveAction = bpy.context.area.spaces.active.action #if "action" in bpy.context.area.spaces.active else nothing
	bpy.context.area.spaces.active.action = action # set active action
	
	armature_matrix = armature_object.matrix_world

	fps = bpy.data.scenes[0].render.fps

	end_frame = action.frame_range[1]
	start_frame = action.frame_range[0]

	frame_length = end_frame - start_frame

	used_frames = int(frame_length) + 1

	keys = []
	channels_location = []
	channels_rotation = []
	channels_scale = []
	
	# precompute per-bone data
	for pose_bone in armature_object.pose.bones:
		armature_bone = pose_bone.bone
		keys.append([])
		channels_location.append(find_channels(action, armature_bone, "location"))
		channels_rotation.append(find_channels(action, armature_bone, "rotation_quaternion"))
		channels_rotation.append(find_channels(action, armature_bone, "rotation_euler"))
		channels_scale.append(find_channels(action, armature_bone, "scale"))

	# process all frames
	for frame_i in range(0, used_frames):
		#print("Processing frame %d/%d" % (frame_i, used_frames))
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

		# process all bones for the current frame
		bone_index = 0
		for pose_bone in armature_object.pose.bones:
			# extract the bone transformations
			if pose_bone.parent is None:
				bone_matrix = armature_matrix * pose_bone.matrix
			else:
				parent_matrix = armature_matrix * pose_bone.parent.matrix
				bone_matrix = armature_matrix * pose_bone.matrix
				bone_matrix = parent_matrix.inverted() * bone_matrix
			pos, rotQ, scl = bone_matrix.decompose()
			rotQ = v.Quaternion_toDegrees(rotQ)
			rotEuler = v.Vector_toDegrees(rotQ.to_euler("XYZ"))

			isKeyframe = has_keyframe_at(channels_location[bone_index], frame) or has_keyframe_at(channels_rotation[bone_index], frame) or has_keyframe_at(channels_scale[bone_index], frame)
			if isKeyframe:
				pchange = True or has_keyframe_at(channels_location[bone_index], frame)
				rchange = True or has_keyframe_at(channels_rotation[bone_index], frame)
				schange = True or has_keyframe_at(channels_scale[bone_index], frame)

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

				# START-FRAME: needs position, rotation, and scale attributes (required frame)
				if frame == start_frame:
					keyframe = s(time) + ':{position:' + posStr + ' rotation:' + rotStr + ' scale:' + scaleStr + '}'
					keys[bone_index].append(keyframe)

				# END-FRAME: needs position, rotation, and scale attributes with animation length
				# (required frame)
				elif frame == end_frame:
					keyframe = s(time) + ':{position:' + posStr + ' rotation:' + rotStr + ' scale:' + scaleStr + '}'
					keys[bone_index].append(keyframe)

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

					keys[bone_index].append(keyframe)
			bone_index += 1

	# gather data
	parents = []
	bone_index = 0
	for pose_bone in armature_object.pose.bones:
		keys_string = "\n\t".join(keys[bone_index])
		parent = pose_bone.name + ':{^}\n\t%s' % (keys_string)
		bone_index += 1
		parents.append(parent)
	boneKeyframesStr = "{^}\n" + v.indent_lines("\n".join(parents))

	if options.option_frame_index_as_time:
		length = frame_length
	else:
		length = frame_length / fps

	animation_string = "{^}"
	#animation_string += "\nname:" + action.name
	animation_string += "\nfps:" + s(fps)
	animation_string += "\nlength:" + s(length)
	animation_string += "\nboneKeyframes:" + boneKeyframesStr
	animation_string = v.indent_lines(animation_string, 1, false)

	bpy.data.scenes[0].frame_set(start_frame)

	# reset context
	bpy.context.area.type = current_context
	# reset context, additional
	#bpy.context.area.spaces.active.action = oldActiveAction
	bpy.context.scene.objects.active = oldActiveObject
	
	return animation_string

def find_channels(action, bone, channel_type):
	bone_name = bone.name
	ngroups = len(action.groups)
	result = []
	if ngroups > 0: # Variant 1: channels grouped by bone names
		# Find the channel group for the given bone
		group_index = -1
		for i in range(ngroups):
			if action.groups[i].name == bone_name:
				group_index = i
		# Get all desired channels in that group
		if group_index > -1:
			for channel in action.groups[group_index].channels:
				if channel_type in channel.data_path:
					result.append(channel)
	else: # Variant 2: no channel groups, bone names included in channel names
		bone_label = '"%s"' % bone_name
		for channel in action.fcurves:
			data_path = channel.data_path
			if bone_label in data_path and channel_type in data_path:
				result.append(channel)
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