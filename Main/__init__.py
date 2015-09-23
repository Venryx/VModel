#__all__ = ["v", "vdebug", "vglobals", "export_vmodel"]
import vmodel.v
import vmodel.vdebug
import vmodel.vclassextensions
import vmodel.vglobals
import vmodel.vmodelexport

# init
# ==========

from vmodel import *
from vmodel.vglobals import *

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

# VModel object panel
# ==========

# general
bpy.types.Object.VModel_export = bpy.props.BoolProperty(default = true)

# vobject
bpy.types.Object.VModel_anchorToTerrain = bpy.props.BoolProperty(default = false)
bpy.types.Object.VModel_anchorVertexesToTerrain = bpy.props.BoolProperty(default = false)
bpy.types.Object.VModel_gateGrate = bpy.props.BoolProperty(default = false)
bpy.types.Object.VModel_gateGrate_openPosition_x = bpy.props.FloatProperty()
bpy.types.Object.VModel_gateGrate_openPosition_y = bpy.props.FloatProperty()
bpy.types.Object.VModel_gateGrate_openPosition_z = bpy.props.FloatProperty()

# material
bpy.types.Object.material_doubleSided = bpy.props.BoolProperty(default = false)
bpy.types.Object.material_alphaMin_enabled = bpy.props.BoolProperty(default = false)
bpy.types.Object.material_alphaMin = bpy.props.FloatProperty(min = 0, max = 1, default = .5)

class OBJECT_PT_hello(bpy.types.Panel):
	bl_label = "VModel - Object"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	#bl_context = "object"
	bl_context = "constraint" # this panel is rarely used, so we'll use it for our own stuff

	'''@classmethod
	def poll(clr, context):
		return Active() is not null'''
	def draw(self, context):
		layout = self.layout
		#obj = context.object
		obj = Active()
		if obj is null:
			return
		
		row = layout.row()
		row.label(text="General")

		row = layout.row()
		row.prop(obj, "VModel_export", text="Export object")

		layout.separator()
		row = layout.row()
		row.label(text="VObject")

		row = layout.row()
		row.prop(obj, "VModel_anchorToTerrain", text="Anchor to terrain")

		row = layout.row()
		row.prop(obj, "VModel_anchorVertexesToTerrain", text="Anchor vertexes to terrain")

		row = layout.row()
		row.prop(obj, "VModel_gateGrate", text="Gate grate")
		if obj.VModel_gateGrate:
			row = layout.row()
			row.label(text="Open position")
			row.prop(obj, "VModel_gateGrate_openPosition_x", text="X")
			row.prop(obj, "VModel_gateGrate_openPosition_y", text="Y")
			row.prop(obj, "VModel_gateGrate_openPosition_z", text="Z")

		layout.separator()
		row = layout.row()
		row.label(text="Material")

		row = layout.row()
		row.prop(obj, "material_doubleSided", text="Double-sided")

		row = layout.row()
		row.prop(obj, "material_alphaMin_enabled", text="Alpha min")
		if obj.material_alphaMin_enabled:
			row.prop(obj, "material_alphaMin", text="Minimum alpha required for a pixel/fragment to be rendered.")

# VModel material panel
# ==========

VModel_material_types = [("Basic", "Basic", "Basic"), ("Phong", "Phong", "Phong"), ("Lambert", "Lambert", "Lambert")]
bpy.types.Material.VModel_materialType = EnumProperty(name = "Material type", description = "Material type", items = VModel_material_types, default = "Lambert")

bpy.types.Material.VModel_unlitShader = bpy.props.BoolProperty(default = false)
bpy.types.Material.VModel_leafShader = bpy.props.BoolProperty(default = false)

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

		row = layout.row()
		row.prop(mat, "VModel_unlitShader", text="Unlit shader")

		row = layout.row()
		row.prop(mat, "VModel_leafShader", text="Leaf shader")

		#row = layout.row()
		#row.prop(mat, "VModel_blendingType", text="Blending type")

		#row = layout.row()
		#row.prop(mat, "VModel_useVertexColors", text="Use vertex colors")

# exporter - settings
# ==========

import json
def save_settings_export(context, properties):
	settings = {}
	for name in dir(properties): #properties.__dict__.keys():
		if name in properties:
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
	useFrameIndexAsKey = BoolProperty(name = "Use frame index as key", description = "Use (original) frame index as keyframe's key", default = true)
	skipLastKeyframe = BoolProperty(name = "Skip last keyframe", description = "(e.g. for some looping animations, where it's just a duplicate of the first)", default = true)

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

		import vmodel.vmodelexport
		#global s_defaultNumberTruncate
		vglobals.s_defaultNumberTruncate = self.maxDecimalPlaces
		return vmodel.vmodelexport.save(self, context, self.properties)
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
		row.prop(self.properties, "useFrameIndexAsKey")
		row = layout.row()
		row.prop(self.properties, "skipLastKeyframe")
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
	if "vmodelexport" in locals():
		imp.reload(vmodelexport)

def menu_func_export(self, context):
	default_path = bpy.data.filepath.replace(".blend", ".vmodel")
	self.layout.operator(ExportVModel.bl_idname, text="VModel (.vmodel)").filepath = default_path

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)

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

	import vmodel.v
	import vmodel.vdebug
	import vmodel.vclassextensions
	import vmodel.vglobals
	import vmodel.vmodelexport

	# make modules available to console panels
	# ==========

	import bpy
	bpy.VModel_VModel_Main = sys.modules[__name__] #["vmodel"]
	bpy.VModel_V = v
	bpy.VModel_VDebug = vdebug
	bpy.VModel_VClassExtensions = vclassextensions
	bpy.VModel_VGlobals = vglobals
	bpy.VModel_VModelExport = vmodelexport

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)
	ReloadModules()
def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)
if __name__ == "__main__":
	register()