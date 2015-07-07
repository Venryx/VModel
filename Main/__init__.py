#__all__ = ["v", "vdebug", "vglobals", "export_vmodel"]
import io_scene_vmodel.v
import io_scene_vmodel.vdebug
import io_scene_vmodel.vglobals
import io_scene_vmodel.export_vmodel

# init
# ==========

from io_scene_vmodel import *
from io_scene_vmodel.vglobals import *

from math import *
#import math

bl_info = {
	"name": "VModel format",
	"author": "Venryx; source (ThreeJS) exporter authors: mrdoob, kikko, alteredq, remoe, pxf, n3tfr34k, crobi",
	"version": (0, 0, 1),
	"blender": (2, 7, 0),
	"location": "File > Export",
	"description": "Export VModel models",
	"warning": "",
	"wiki_url": "n/a",
	"tracker_url": "n/a",
	"category": "Import-Export"
}

import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper

# ShowSpaceTaken operator
# ==========

BLOCK_SIZE = 4

class ShowSpaceTakenOperator(bpy.types.Operator):
	"""Visualizes the dimensions of the space taken by the selected object, in Biome Defense terrain blocks."""
	bl_idname = "view3d.show_space_taken"
	bl_label = "Show Space Taken"
	@classmethod
	def poll(cls, context): # is called to determine whether the operator can be invoked
		return context.active_object is not None
	def execute(self, context): # invokes the operator and returns a state
		if "SpaceTaken" in bpy.data.objects:
			#v.SaveSelection()
			bpy.ops.view3d.hide_space_taken() #HideSpaceTakenOperator(null).execute()
			#v.LoadSelection()

		blocks = v.CreateObject_Empty("SpaceTaken")
		#spaceTaken = bpy.context.scene.objects.active.GetBounds()
		spaceTaken = Box.Null
		#for obj in [a for a in bpy.data.objects if a.select][0].GetDescendents(): #bpy.data.objects
		for obj in bpy.context.scene.objects.active.GetDescendents():
			if obj.VModel_export:
				spaceTaken = spaceTaken.Encapsulate(obj.GetBounds())

		for obj in bpy.context.scene.objects:
			obj.select = false

		#Log("A:" + s(floor(spaceTaken.position.x) - (floor(spaceTaken.position.x) % BLOCK_SIZE)) + ";" + s(floor(spaceTaken.GetMax().x) - (floor(spaceTaken.GetMax().x) % BLOCK_SIZE)))
		for x in range(floor(spaceTaken.position.x) - (floor(spaceTaken.position.x) % BLOCK_SIZE), (floor(spaceTaken.GetMax().x) - (floor(spaceTaken.GetMax().x) % BLOCK_SIZE)) + BLOCK_SIZE, BLOCK_SIZE):
			for y in range(floor(spaceTaken.position.y) - (floor(spaceTaken.position.y) % BLOCK_SIZE), (floor(spaceTaken.GetMax().y) - (floor(spaceTaken.GetMax().y) % BLOCK_SIZE)) + BLOCK_SIZE, BLOCK_SIZE):
				for z in range(floor(spaceTaken.position.z) - (floor(spaceTaken.position.z) % BLOCK_SIZE), (floor(spaceTaken.GetMax().z) - (floor(spaceTaken.GetMax().z) % BLOCK_SIZE)) + BLOCK_SIZE, BLOCK_SIZE):
					#block = v.CreateObject_Cube("SpaceTaken", (x, y, z), (0, 0, 0, 1), (BLOCK_SIZE, BLOCK_SIZE, .1))
					#block = v.CreateObject_Empty("Block", (x, y, z), (0, 0, 0, 1), (BLOCK_SIZE, BLOCK_SIZE, .1), "CUBE")
					block = v.CreateObject_Empty("Block", Vector((x, y, z)) + (Vector((BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)) / 2), Vector((0, 0, 0, 1)), Vector((BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)) / 2, "CUBE")
					block.select = true
					block.parent = blocks
		return {'FINISHED'}

# HideSpaceTaken operator
# ==========

class HideSpaceTakenOperator(bpy.types.Operator):
	bl_idname = "view3d.hide_space_taken"
	bl_label = "Hide Space Taken"
	@classmethod
	def poll(cls, context):
		return context.active_object is not None
	def execute(self, context):
		if "SpaceTaken" not in bpy.data.objects:
			return {'FINISHED'}
		blocks = bpy.data.objects["SpaceTaken"]
		'''for ob in bpy.context.scene.objects:
			ob.select = false
		blocks.select = true
		bpy.ops.object.delete()'''
		v.DeleteObject(blocks)

		return {'FINISHED'}

# VModel object panel
# ==========

bpy.types.Object.VModel_export = bpy.props.BoolProperty(default = true)
bpy.types.Object.VModel_anchorToTerrain = bpy.props.BoolProperty(default = false)
bpy.types.Object.VModel_anchorVertexesToTerrain = bpy.props.BoolProperty(default = false)
bpy.types.Object.material_doubleSided = bpy.props.BoolProperty(default = false)
bpy.types.Object.material_alphaMin_enabled = bpy.props.BoolProperty(default = false)
bpy.types.Object.material_alphaMin = bpy.props.FloatProperty(description = "Minimum alpha required for a pixel/fragment to be rendered.", min = 0, max = 1, default = .5)

class OBJECT_PT_hello(bpy.types.Panel):
	bl_label = "VModel"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		
		row = layout.row()
		row.label(text="Selected object: " + obj.name)

		row = layout.row()
		row.prop(obj, "VModel_export", text="Export object")

		row = layout.row()
		row.prop(obj, "VModel_anchorToTerrain", text="Anchor to terrain")

		row = layout.row()
		row.prop(obj, "VModel_anchorVertexesToTerrain", text="Anchor vertexes to terrain")

		row = layout.row()
		row.operator("view3d.show_space_taken", text="Show space taken")
		row.operator("view3d.hide_space_taken", text="Hide space taken")

		row = layout.row()
		row.label(text="Material:")

		row = layout.row()
		row.prop(obj, "material_doubleSided", text="Double-sided")

		row = layout.row()
		row.prop(obj, "material_alphaMin_enabled", text="Alpha min")
		if obj.material_alphaMin_enabled:
			row.prop(obj, "material_alphaMin", text="")

# VModel material panel
# ==========

VModel_material_types = [("Basic", "Basic", "Basic"), ("Phong", "Phong", "Phong"), ("Lambert", "Lambert", "Lambert")]
bpy.types.Material.VModel_materialType = EnumProperty(name = "Material type", description = "Material type", items = VModel_material_types, default = "Lambert")

'''VModel_blending_types = [("NoBlending", "NoBlending", "NoBlending"), ("NormalBlending", "NormalBlending", "NormalBlending"),
						("AdditiveBlending", "AdditiveBlending", "AdditiveBlending"), ("SubtractiveBlending", "SubtractiveBlending", "SubtractiveBlending"),
						("MultiplyBlending", "MultiplyBlending", "MultiplyBlending"), ("AdditiveAlphaBlending", "AdditiveAlphaBlending", "AdditiveAlphaBlending")]
bpy.types.Material.VModel_blendingType = EnumProperty(name = "Blending type", description = "Blending type", items = VModel_blending_types, default = "NormalBlending")'''

#bpy.types.Material.VModel_useVertexColors = bpy.props.BoolProperty()

class MATERIAL_PT_hello(bpy.types.Panel):
	bl_label = "VModel"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "material"

	def draw(self, context):
		layout = self.layout
		mat = context.material

		row = layout.row()
		row.label(text="Selected material: " + mat.name)

		row = layout.row()
		row.prop(mat, "VModel_materialType", text="Material type")

		#row = layout.row()
		#row.prop(mat, "VModel_blendingType", text="Blending type")

		#row = layout.row()
		#row.prop(mat, "VModel_useVertexColors", text="Use vertex colors")

# Exporter - settings
# ==========

SETTINGS_FILE_EXPORT = "vmodel_settings_export.js"

import os
import json

def file_exists(filename):
	"""Return true if file exists and accessible for reading.

	Should be safer than just testing for existence due to links and
	permissions magic on Unix filesystems.

	@rtype: boolean
	"""

	try:
		f = open(filename, 'r')
		f.close()
		return True
	except IOError:
		return False

def get_settings_fullpath():
	return os.path.join(bpy.app.tempdir, SETTINGS_FILE_EXPORT)

def save_settings_export(context, properties):
	settings = {}
	for name in dir(properties): #properties.__dict__.keys():
		if name in properties:
			#Log("propName:" + name)
			settings[name] = properties[name]

	context.scene["vModelExportSettings"] = json.dumps(settings)

def restore_settings_export(context, properties, self):
	settings = json.loads(context.scene["vModelExportSettings"]) if "vModelExportSettings" in context.scene else {}
	for name in settings.keys():
		self.properties[name] = settings[name]

# exporter
# ==========

class ExportVModel(bpy.types.Operator, ExportHelper):
	'''Export scene as a .vmodel (vdf) file.'''

	bl_idname = "export.vmodel"
	bl_label = "Export VModel"

	filename_ext = ".vmodel"

	option_vertices = BoolProperty(name = "Vertices", description = "Export vertices", default = true)
	#option_vertices_deltas = BoolProperty(name = "Deltas", description = "Delta vertices", default = false)
	option_faces = BoolProperty(name = "Faces", description = "Export faces", default = true)
	#option_faces_deltas = BoolProperty(name = "Deltas", description = "Delta faces", default = false)
	option_normals = BoolProperty(name = "Normals", description = "Export normals", default = true)

	option_colors = BoolProperty(name = "Colors", description = "Export vertex colors", default = false)
	option_uv_coords = BoolProperty(name = "UVs", description = "Export texture coordinates", default = true)

	option_skinning = BoolProperty(name = "Skinning", description = "Export skin data", default = true)
	option_bones = BoolProperty(name = "Bones", description = "Export bones", default = true)

	align_types = [("None","None","None"), ("Center","Center","Center"), ("Bottom","Bottom","Bottom"), ("Top","Top","Top")]
	align_model = EnumProperty(name = "Align model", description = "Align model", items = align_types, default = "None")

	rotationDataTypes = [("Euler Angle","Euler Angle","Euler Angle"), ("Quaternion","Quaternion","Quaternion")]
	rotationDataType = EnumProperty(name = "Rotation data-type/structure", description = "How to store object rotations (euler angle is simpler, quaternion avoids gimbal lock)", items = rotationDataTypes, default = "Quaternion")
	maxDecimalPlaces = IntProperty(name = "Max decimal places", description = "Round serialized numbers to have at most x decimal-places (-1 for no rounding)", min = -1, max = 30, soft_min = -1, soft_max = 30, default = 5)
	writeDefaultValues = BoolProperty(name = "Write default values", description = "Write values even if they're the defaults. (e.g. \"scale:[1 1 1]\")", default = false)

	option_animation_morph = BoolProperty(name = "Morph animation", description = "Export animation (morphs)", default = false)
	option_animation_skeletal = BoolProperty(name = "Skeletal animation", description = "Export animation (skeletal)", default = true)
	option_frame_index_as_time = BoolProperty(name = "Frame index as time", description = "Use (original) frame index as frame time", default = true)

	def invoke(self, context, event):
		restore_settings_export(context, self.properties, self)
		return ExportHelper.invoke(self, context, event)

	'''@classmethod
	def poll(cls, context):
		return true #context.active_object != None'''

	def execute(self, context):
		#print("Selected: " + context.active_object.name)

		if not self.properties.filepath:
			raise Exception("filename not set")

		save_settings_export(context, self.properties)

		filepath = self.filepath

		import io_scene_vmodel.export_vmodel
		#global s_defaultNumberTruncate
		vglobals.s_defaultNumberTruncate = self.maxDecimalPlaces
		return io_scene_vmodel.export_vmodel.save(self, context, self.properties)
		vglobals.s_defaultNumberTruncate = -1

	def draw(self, context):
		layout = self.layout

		row = layout.row()
		row.label(text="Geometry:")

		row = layout.row()
		row.prop(self.properties, "option_vertices")
		# row = layout.row()
		# row.enabled = self.properties.option_vertices
		# row.prop(self.properties, "option_vertices_deltas")
		layout.separator()

		row = layout.row()
		row.prop(self.properties, "option_faces")
		row = layout.row()
		row.enabled = self.properties.option_faces
		# row.prop(self.properties, "option_faces_deltas")
		layout.separator()

		row = layout.row()
		row.prop(self.properties, "option_normals")
		layout.separator()

		row = layout.row()
		row.prop(self.properties, "option_bones")
		row.prop(self.properties, "option_skinning")
		layout.separator()

		row = layout.row()
		row.label(text="Materials:")

		row = layout.row()
		row.prop(self.properties, "option_uv_coords")
		#row.prop(self.properties, "option_colors")
		layout.separator()

		row = layout.row()
		row.label(text="Settings:")

		row = layout.row()
		row.prop(self.properties, "align_model")
		row = layout.row()
		row.prop(self.properties, "rotationDataType")
		row = layout.row()
		row.prop(self.properties, "maxDecimalPlaces")
		layout.separator()
		row = layout.row()
		row.prop(self.properties, "writeDefaultValues")
		layout.separator()

		row = layout.row()
		row.label(text="--------- Experimental ---------")
		layout.separator()

		row = layout.row()
		row.label(text="Animation:")

		row = layout.row()
		row.prop(self.properties, "option_animation_morph")
		row = layout.row()
		row.prop(self.properties, "option_animation_skeletal")
		row = layout.row()
		row.prop(self.properties, "option_frame_index_as_time")
		layout.separator()

		layout.separator()

# registration stuff (old)
# ==========

# [was at top section] to support reload properly, try to access a package var; if it's there, reload everything
'''import bpy
if "bpy" in locals():
	#unregister()
	#register()

	import imp
	if "v" in locals():
		imp.reload(v)
	if "vdebug" in locals():
		imp.reload(vdebug)
	if "vglobals" in locals():
		imp.reload(vglobals)
	if "export_vmodel" in locals():
		imp.reload(export_vmodel)

def menu_func_export(self, context):
	default_path = bpy.data.filepath.replace(".blend", ".vmodel")
	self.layout.operator(ExportVModel.bl_idname, text="VModel (.vmodel)").filepath = default_path

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)

	# operators
	#bpy.utils.register_class(ShowSpaceTakenOperator)
	#bpy.utils.register_class(HideSpaceTakenOperator)
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)

	# operators
	#bpy.utils.unregister_class(ShowSpaceTakenOperator)
	#bpy.utils.unregister_class(HideSpaceTakenOperator)

if __name__ == "__main__":
	register()'''

# registration stuff
# ==========

def menu_func_export(self, context):
	default_path = bpy.data.filepath.replace(".blend", ".vmodel")
	self.layout.operator(ExportVModel.bl_idname, text="VModel (.vmodel)").filepath = default_path

def ReloadModules(): # doesn't reload itself (this root/init module), because that already happens when the F8 button is pressed (also, I don't know how to have it do so)
	# clear submodules
	import sys
	module_name = "io_scene_vmodel"
	Log("Reloading submodules for " + module_name)
	for m in dict(sys.modules):
		if m[0:len(module_name) + 1] == module_name + ".":
			Log("    Reloading submodule: " + m[len(module_name) +1:])
			del sys.modules[m]

	import io_scene_vmodel.v
	import io_scene_vmodel.vdebug
	import io_scene_vmodel.vglobals
	import io_scene_vmodel.export_vmodel

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)
	ReloadModules()
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)
if __name__ == "__main__":
	register()