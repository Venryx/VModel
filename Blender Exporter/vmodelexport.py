from vmodel import *
from vmodel.vglobals import *

import bpy
import mathutils

import shutil
import os
import os.path
import math
from math import fabs
import operator
import random
import re

import bmesh

# main
# ==========

def save(operator, context, options):
	#options.filepath = ensure_extension(options.filepath, '.json') # maybe todo: add this back
	source_file = os.path.basename(bpy.data.filepath)

	text = "{^}"
	text += "\nobjects:" + GetObjectsStr({"scene": context.scene, "objects": context.scene.objects}, options)
	text = v.indentLines(text, 1, false)

	vdebug.MarkSections()

	v.write_file(options.filepath, text)
	return {'FINISHED'}

# objects
# ==========

meshFirstObjectNames = {}
meshStrings = {}
def GetObjectsStr(data, options):
	global meshFirstObjectNames, meshStrings
	meshFirstObjectNames = {}
	meshStrings = {}

	chunks = []
	for obj in data["objects"]:
		if obj.parent == null and obj.VModel_export: # root objects
			chunks.append(obj.name + ":" + GetObjectStr(obj, data, options))
	return "{^}\n" + v.indentLines("\n".join(chunks))
def GetObjectStr(obj, data, options):
	object_string = "{^}"

	matrix_local = obj.matrix_local #obj.matrix_world
	position, rotationQ, scale = matrix_local.decompose()
	'''position = obj.localPosition
	rotationQ = obj.localRotation
	scale = obj.localScale'''

	rotationQ_degrees = v.Quaternion_toDegrees(rotationQ)
	rotation = v.Vector_toDegrees(rotationQ_degrees.to_euler("XYZ")); #ZYX"))

	object_string += "\nposition:" + S(position)
	object_string += "\nrotation:" + (S(rotation) if options.rotationDataType == "Euler Angle" else S(rotationQ))
	#object_string += "\nscale:" + S(scale)
	object_string += "\nscale:" + S(scale) if options.writeDefaultValues or fabs(scale.x - 1) > .001 or fabs(scale.y - 1) > .001 or fabs(scale.z - 1) > .001 else ""

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
	if obj.VModel_anchorVertexesToTerrain:
		object_string += "\nanchorVertexesToTerrain:true"
	if obj.VModel_gateGrate:
		#object_string += "\ngateGrate:true"
		# todo: break point
		object_string += "\ngateGrate_openPosition:" + S(Vector((obj.VModel_gateGrate_openPosition_x, obj.VModel_gateGrate_openPosition_y, obj.VModel_gateGrate_openPosition_z)))

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
		#mesh = obj.to_mesh(scene, True, "RENDER")
		#mesh = obj.to_mesh(scene, false, "RENDER")

		# only apply modifiers for mesh-retrieval if there are no Armature modifiers in the list
		mesh = obj.to_mesh(scene, len([a for a in obj.modifiers if type(a) == bpy.types.ArmatureModifier]) == 0, "RENDER")

		if not mesh:
			raise Exception("Error, could not get mesh data from object [%s]" % obj.name)

		# preserve original name
		mesh.name = obj.name
	
		mesh.update(calc_tessface=True)

		mesh.calc_normals()
		mesh.calc_tessface()
		#mesh.transform(mathutils.Matrix.Scale(option_scale, 4))
		return mesh

	return null

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
	for faceIndex, face in enumerate(mesh.GetFaces()):
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
		result += "position:" + S(vertex.co)
		result += " normal:[" + S(vertex.normal[0]) + " " + S(vertex.normal[1]) + " " + S(vertex.normal[2]) + "]"

		uvsStr = ""
		if options.option_uv_coords and len(mesh.uv_textures) > 0 and (not mesh.uv_textures.active == null):
			''' # this approach took 12.79 seconds
			for faceIndex, face in enumerate(v.get_faces(mesh)):
				for layerIndex, layer in enumerate(mesh.tessface_uv_textures): # for now, we assume there's only one
					for faceVertexIndex, vertexIndex2 in enumerate(face.vertices):
						if vertexIndex == vertexIndex2:
							vec = layer.data[faceIndex].uv[faceVertexIndex]
							result += " uv" + (S(layerIndex) if layerIndex > 0 else "") + "_face" + S(faceIndex) + ":[" + S(vec[0]) + " " + S(vec[1]) + "]" #S(posComp[0]) + " " + S(posComp[1]) + "]"
			'''

			# this approach took .69 seconds
			if vertexIndex in vertexInfoByVertexThenLayerThenFace: # (a vertex might not be a part of any face)
				vertexInfo = vertexInfoByVertexThenLayerThenFace[vertexIndex]
				for layerIndex, layerInfo in sorted(vertexInfo.items()):
					layerFaceUVValues = []
					for faceIndex, faceInfo in sorted(layerInfo.items()):
						if not Any(layerFaceUVValues, lambda a:a["uvPoint"][0] == faceInfo["uvPoint"][0] and a["uvPoint"][1] == faceInfo["uvPoint"][1]):
							layerFaceUVValues.append(faceInfo)
					if len(layerFaceUVValues) == 1:
						uvsStr += " uv" + (S(layerIndex + 1) if layerIndex > 0 else "") + ":[" + S(faceInfo["uvPoint"][0]) + " " + S(faceInfo["uvPoint"][1]) + "]"
					else:
						for faceIndex, faceInfo in sorted(layerInfo.items()):
							uvsStr += " uv" + (S(layerIndex + 1) if layerIndex > 0 else "") + "_face" + S(faceIndex) + ":[" + S(faceInfo["uvPoint"][0]) + " " + S(faceInfo["uvPoint"][1]) + "]"
		result += uvsStr

		if obj.find_armature() != null:
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
			result += (" " if len(result) > 1 else "") + obj.vertex_groups[index].name + ":" + S(group.weight)
	result += "}"

	return result

# vertex colors (to become part of "mesh" section)
# ==========

'''def hexcolor(c):
	return (int(c[0] * 255) << 16) + (int(c[1] * 255) << 8) + int(c[2] * 255)

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

	return "[" + " ".join(S(c) for c in chunks) + "]"'''

# faces
# ==========

def GetFacesStr(obj, mesh):
	result = "["
	for faceIndex, face in enumerate(mesh.GetFaces()):
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
				result += (" " if vertexIndex != 0 else "") + S(vertex)
			result += "]"'''

		result += (" " if faceIndex != 0 else "") + "["
		for vertexIndex, vertex in enumerate(face.vertices):
			result += (" " if vertexIndex != 0 else "") + S(vertex)
		if face.material_index > 0:
			result += " {material:" + S(face.material_index) + "}"
		result += "]"
	result += "]"
	return result

# materials
# ==========

def GetMaterialsStr(obj, mesh):
	result = "[^]"
	for materialIndex, material in enumerate(obj.data.materials):
		if not material.use_nodes:
			raise Exception("Materials must have the \"Use Nodes\" setting enabled.")

		matStr = "\n{" #diffuseColor:\"" + ColorToHexStr(material.diffuse_color) + "\""
		if material.node_tree != null:
			nodes = material.node_tree.nodes

			for node in nodes: # note: the below makes a lot of assumptions about the nodes' configurations and applications
			
				# for diffuseColor
				if node.name == "Mix" and not node.inputs[1].is_linked:
					matStr += ("" if matStr.count(":") == 0 else " ") + "diffuseColor:\"" + ColorToHexStr(node.inputs[1].default_value) + "\""
				elif node.name == "RGB":
					matStr += ("" if matStr.count(":") == 0 else " ") + "diffuseColor:\"" + ColorToHexStr(node.color) + "\""
				elif node.name == "Diffuse BSDF": #type == "BSDF_DIFFUSE":
					#if not node.inputs[0].is_linked and not diffuseColorHasOwnNode: # if just raw diffuse (no from-other-node/link input), and if a separate RGB node was not found, then use the raw diffuse
					if not node.inputs[0].is_linked: # if just raw diffuse (no from-other-node/link input), then use the raw diffuse
						#matStr += ("" if matStr.count(":") == 0 else " ") + "diffuseColor:\"" + ColorToHexStr(node.color) + "\""
						matStr += ("" if matStr.count(":") == 0 else " ") + "diffuseColor:\"" + ColorToHexStr(node.inputs[0].default_value) + "\"" # maybe todo: get this to show the gamma corrected value (as in UI) rather than the base
				
				# for others
				elif node.name == "Transparent BSDF": #type == "BSDF_TRANSPARENT":
					matStr += ("" if matStr.count(":") == 0 else " ") + "transparency:true"
				elif node.name == "Mix Shader" and not node.inputs[0].is_linked:
					matStr += ("" if matStr.count(":") == 0 else " ") + "alpha:" + S(node.inputs[0].default_value)
				elif node.name == "Image Texture": #type == "TEX_IMAGE":
					textureBaseName = re.sub("[.0-9]+$", "", node.image.name)
					matStr += ("" if matStr.count(":") == 0 else " ") + "texture:\"" + textureBaseName + "\""
			result += matStr
		if "VModel_unlitShader" in material and material.VModel_unlitShader:
			result += " unlitShader:true"
		#if "material_leafShader" in obj and obj.material_leafShader:
		#	result += " leafShader:true"
		if "VModel_leafShader" in material and material.VModel_leafShader:
			result += " leafShader:true"
		if "material_doubleSided" in obj and obj.material_doubleSided:
			result += " doubleSided:true"
		result += "}"

	result = v.indentLines(result, 1, false)

	return result

def ColorToHexStr(color):
	result = ""
	if len(color) == 4: # for now, trim off the alpha component (if there is one)
		color = color[:3]
	for colorComp in color:
		# compensate for gamma-correction thing (full white was showing up as "cccccc" (204, 204, 204) before)
		# see: http://blenderartists.org/forum/showthread.php?320221-Converting-HEX-colors-to-blender-RGB
		colorComp *= 255 / 204
		compStr = S(hex(int(colorComp * 255)))[2:]
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
		if obj.data.edit_bones[bone.name].parent == null:
			bones_string += "\n" + v.indentLines(GetBoneStr(obj, armature, bone, options))
			#bones_string += "\n" + v.indentLines(GetBoneStr(obj, armature, poseBone, options))
	result += "\n" + v.indentLines("bones:" + bones_string)

	# revert
	bpy.ops.object.mode_set(mode = oldMode)
	bpy.context.scene.objects.active = oldActiveObject

	return result

#def GetBoneStr(obj, armature, poseBone, options):
#	bone = poseBone.bone
def GetBoneStr(obj, armature, bone, options):
	hierarchy = []
	armature_matrix = obj.matrix_world
	#poseBones = obj.pose.bones #armature.bones

	'''if bone.parent is null:
		bone_matrix = armature_matrix * bone.matrix_local
	else:
		parent_matrix = armature_matrix * bone.parent.matrix_local
		bone_matrix = armature_matrix * bone.matrix_local
		bone_matrix = parent_matrix.inverted() * bone_matrix'''
	'''if bone.parent is null:
		bone_matrix = v.GetBoneLocalMatrix(bone) #bone.matrix_local
	else:
		parent_matrix = v.GetBoneLocalMatrix(bone.parent) #bone.parent.matrix_local
		bone_matrix = v.GetBoneLocalMatrix(bone) #bone.matrix_local
		bone_matrix = parent_matrix.inverted() * bone_matrix'''
	#bone_matrix = v.GetBoneLocalMatrix(bone, true, false) #poseBone)
	bone_matrix = bone.GetMatrix()
	if bone.parent == null:
		bone_matrix = v.fixMatrixForRootBone(bone_matrix)
	pos, rotQ, scl = bone_matrix.decompose()

	'''pos = obj.location
	rotQ = obj.rotation_quaternion
	scl = obj.scale'''

	#pos = bone.head_local
	#pos, rotQ, scl = bone.matrix.to_4x4().decompose()
	#rotQ, scl = bone.matrix.to_4x4().decompose()[1:]

	# at-rest bones, even if they have 'rotation', don't actually apply their rotation to their descendent bones (i.e. the descendents local-position is actually just the position relative to the armature)
	# so undo applying of parent-bone matrix to the current bone's location
	# pos = bone.matrix_local.decompose()[0] if bone.parent is null else bone.matrix_local.decompose()[0] - bone.parent.matrix_local.decompose()[0]

	# for some reason, the "rest" or "base" rotation of a bone is [-.5 0 0 0] (relative to the world) (i.e. rotated forward 90 degrees--with the tail/tip/non-core-end having a higher y value)
	# we're going to correct that, so that the stored rotation is the rotation to get from the world-rotation (identity/none/[0 0 0 1]) to the bone rotation
	#rotQ = mathutils.Quaternion([.707107, .707107, 0, 0]).inverted() * rotQ # w, x, y, z
	'''rotQ = mathutils.Quaternion([.707107, .707107, 0, 0]).rotation_difference(rotQ)
	yOld = rotQ.y
	rotQ.y = -rotQ.z
	rotQ.z = yOld'''

	rotQ_degrees = v.Quaternion_toDegrees(rotQ)
	rotationEuler = v.Vector_toDegrees(rotQ_degrees.to_euler("XYZ"))

	#parentNameStr = ("\"" + obj.data.edit_bones[bone.name].parent.name + "\"") if obj.data.edit_bones[bone.name].parent != null else "null"
	
	positionStr = S(pos)
	rotationStr = S(rotationEuler) if options.rotationDataType == "Euler Angle" else S(rotQ)

	childrenStr = ""
	if len(obj.data.edit_bones[bone.name].children) > 0:
		for childEditBone in obj.data.edit_bones[bone.name].children:
			childrenStr += "\n" + v.indentLines(GetBoneStr(obj, armature, next(a for a in armature.bones if a.name == childEditBone.name), options))

	result = bone.name + ":{position:" + positionStr + " rotation:" + rotationStr + (" scale:" + S(scl) if options.writeDefaultValues or fabs(scl.x - 1) > .001 or fabs(scl.y - 1) > .001 or fabs(scl.z - 1) > .001 else "") + (" children:{^}" if len(childrenStr) > 0 else "") + "}" + childrenStr
	#result = bone.name + ":{position:" + positionStr + " scale:" + scaleStr + (" children:{^}" if len(childrenStr) > 0 else "") + "}" + childrenStr

	return result

# skeletal animation
# ==========

def GetBoneChannels(action, bone, channelType):
	result = []

	vdebug.StartSection()

	'''if len(action.groups) > 0 and Any(action.groups, lambda a:a.name == bone.name): # variant 1: groups:[{name:"Bone1", channels:[{data_path:"location"}]}]
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
	else: # variant 3: fcurves:[{data_path:"pose.bones[\"Bone1\"].location"}]'''
	bone_label = "\"" + bone.name + "\""
	for channel in action.fcurves:
		data_path = channel.data_path
		if bone_label in data_path and channelType in data_path:
			result.append(channel)

	vdebug.EndSection("a")

	return result
def GetKeyframeAt(channel, frame):
	for keyframe in channel.keyframe_points:
		#if keyframe.co[0] == frame:
		if round(keyframe.co[0]) == frame: # maybe temp; assume the user wants keyframes to always be seen as having integer x-axis points
			return keyframe
	return null
def IsKeyframeAt(channels, frame):
	for channel in channels:
		if GetKeyframeAt(channel, frame) is not null:
			return true
	return false

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
	oldActiveAction = bpy.context.area.spaces.active.action #if "action" in bpy.context.area.spaces.active else null
	bpy.context.area.spaces.active.action = action
	oldFrame = bpy.data.scenes[0].frame_current

	armature_matrix = obj.matrix_world #obj.matrix_local
	fps = bpy.data.scenes[0].render.fps
	#firstFrame = action.frame_range[0]
	#enderFrame = int(action.frame_range[1]) + 1
	enderFrame = round(action.frame_range[1]) + 1
	if options.skipLastKeyframe:
		enderFrame -= 1 # skip the last frame (e.g. for some looping animations, where it's just a duplicate of the first)

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
	#for frame in range(firstFrame, enderFrame): # process all frames
	for frame in range(0, enderFrame): # process all frames # maybe temp; assume the user wants keyframes to always be seen as having integer x-axis points
		vdebug.StartSection()
		
		# compute the time of the frame
		'''if options.useFrameIndexAsKey:
			time = frame - firstFrame
		else:
			time = (frame - firstFrame) / fps'''
		if options.useFrameIndexAsKey:
			time = frame
		else:
			time = frame / fps

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
			#bone_matrix = v.GetBoneLocalMatrix(poseBone, false)
			#bone_matrix = v.GetBoneLocalMatrix(poseBone) # maybe temp; bake orientation as relative to armature, as Unity API wants it in the end
			bone_matrix = poseBone.GetMatrix()
			pos, rotQ, scl = bone_matrix.decompose()

			'''pos = poseBone.location
			rotQ = poseBone.rotation_quaternion
			scl = poseBone.scale'''

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
			isKeyframe = IsKeyframeAt(bonePropertyChannels["location"], frame) or IsKeyframeAt(bonePropertyChannels["rotation"], frame) or IsKeyframeAt(bonePropertyChannels["scale"], frame) or frame == enderFrame - 1

			vdebug.EndSection("3")

			if isKeyframe:
				vdebug.StartSection()

				'''pchange = IsKeyframeAt(bonePropertyChannels["location"], frame)
				rchange = IsKeyframeAt(bonePropertyChannels["rotation"], frame)
				schange = IsKeyframeAt(bonePropertyChannels["scale"], frame)'''
				pchange = true
				rchange = true
				schange = true

				rotStr = S(rotEuler) if options.rotationDataType == "Euler Angle" else S(rotQ)
				scaleStr = S(scl) if options.writeDefaultValues or fabs(scl.x - 1) > .001 or fabs(scl.y - 1) > .001 or fabs(scl.z - 1) > .001 else null

				vdebug.EndSection("4")
				vdebug.StartSection()

				# start-frame and end-frame: need position, rotation, and scale attributes (required frames)
				#if frame == firstFrame or frame == enderFrame - 1:
				if frame == 0 or frame == enderFrame - 1:
					keyframe = S(time) + ":{position:" + S(pos) + " rotation:" + rotStr + (" scale:" + scaleStr if scaleStr != null else "") + "}"
					keys[boneIndex].append(keyframe)
				# middle-frame: needs only one of the attributes; can be an empty frame (optional frame)
				elif pchange == true or rchange == true:
					keyframe = S(time) + ':{'
					if pchange == true:
						keyframe += "position:" + S(pos)
					if rchange == true:
						keyframe += " rotation:" + rotStr
					if schange == true and scaleStr != null:
						keyframe += " scale:" + scaleStr
					keyframe += '}'

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

	'''if options.useFrameIndexAsKey:
		length = frame_length
	else:
		length = frame_length / fps'''
	length = enderFrame

	vdebug.EndSection("6")
	vdebug.StartSection()

	animation_string = "{^}"
	#animation_string += "\nname:" + action.name
	animation_string += "\nfps:" + S(fps)
	animation_string += "\nlength:" + S(length)
	animation_string += "\nboneKeyframes:" + boneKeyframesStr
	animation_string = v.indentLines(animation_string, 1, false)

	#bpy.data.scenes[0].frame_set(start_frame)
	bpy.data.scenes[0].frame_set(0)

	# revert
	bpy.data.scenes[0].frame_set(oldFrame)
	bpy.context.area.spaces.active.action = oldActiveAction
	bpy.context.space_data.mode = oldSpaceDataMode
	bpy.context.area.type = oldContext
	bpy.ops.object.mode_set(mode = oldMode)
	bpy.context.scene.objects.active = oldActiveObject
	
	vdebug.EndSection("7")

	return animation_string
def GetAnimationsStr(obj, armature, actions, options):
	result = "{^}"

	# todo: change to pose mode (or something like that)
	for action in actions:
		result += "\n" + action.name + ":" + GetActionStr(obj, armature, action, options)
	result = v.indentLines(result, 1, false)
	# todo: revert mode

	return result