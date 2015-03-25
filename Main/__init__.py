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

# ################################################################
# Init
# ################################################################

# todo: make this not needed, then remove it
import io_scene_vmodel.v
import io_scene_vmodel.vdebug
import io_scene_vmodel.export_vmodel

from io_scene_vmodel import *
from io_scene_vmodel.v import nothing, false, true
from io_scene_vmodel.v import Log, s

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

# To support reload properly, try to access a package var,
# if it's there, reload everything
import bpy

if "bpy" in locals():
	import imp
	if "v" in locals():
		imp.reload(v)
	if "vdebug" in locals():
		imp.reload(vdebug)
	if "export_vmodel" in locals():
		imp.reload(export_vmodel)

from bpy.props import *
from bpy_extras.io_utils import ExportHelper, ImportHelper

# VModel object panel
# ==========

bpy.types.Object.VModel_export = bpy.props.BoolProperty(default = True)

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

# ################################################################
# Exporter - settings
# ################################################################
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
	#__import__('code').interact(local={k: v for ns in (globals(), locals()) for k, v in ns.items()})

	settings = {}
	for name in dir(properties): #properties.__dict__.keys():
		if name in properties:
			#Log("propName:" + name)
			settings[name] = properties[name]

	'''
	fname = get_settings_fullpath()
	f = open(fname, "w")
	json.dump(settings, f)
	'''

	context.scene["vModelExportSettings"] = json.dumps(settings)

def restore_settings_export(context, properties, self):
	'''
	settings = {}
	fname = get_settings_fullpath()
	if file_exists(fname):
		f = open(fname, "r")
		''#'
		try: # maybe temp
			settings = json.load(f)
		except:
			pass
		''#'
		settings = json.load(f)
	'''

	settings = {}
	settings = json.loads(context.scene["vModelExportSettings"]) if "vModelExportSettings" in context.scene else {}
	'''
	try:
		settings = json.loads(context.scene["vModelExportSettings"]) if "vModelExportSettings" in context.scene else {}
	except:
		pass
	'''
	
	defaults = {
		"option_vertices": true,
		"option_faces": true,
		"option_normals": true,

		"option_colors": true,
		"option_uv_coords": true,

		"option_skinning": true,
		"option_bones": true,

		"align_model": "None",

		"option_flip_yz": false,
		"rotationDataType": "Euler Angle",
		"maxDecimalPlaces": 7,

		"option_animation_morph": false,
		"option_animation_skeletal": true,
		"option_frame_index_as_time": true,
	}

	for name in defaults.keys():
		self.properties[name] = defaults[name]
	for name in settings.keys():
		self.properties[name] = settings[name]

	'''for name in settings.keys(): #dir(settings): #properties.__dict__.keys():
		Log(name + ";" + s(name in settings) + ";" + s(name in defaults))
		if name in settings or name in defaults: #not name.startswith("_"):
			self.properties[name] = settings[name] if name in settings else defaults[name]'''

# exporter
# ==========

class ExportVModel(bpy.types.Operator, ExportHelper):
	'''Export scene as a .vmodel (vdf) file.'''

	bl_idname = "export.vmodel"
	bl_label = "Export VModel"

	filename_ext = ".vmodel"

	option_vertices = BoolProperty(name = "Vertices", description = "Export vertices", default = true)
	option_vertices_deltas = BoolProperty(name = "Deltas", description = "Delta vertices", default = false)

	option_faces = BoolProperty(name = "Faces", description = "Export faces", default = true)
	option_faces_deltas = BoolProperty(name = "Deltas", description = "Delta faces", default = false)

	option_normals = BoolProperty(name = "Normals", description = "Export normals", default = true)

	option_colors = BoolProperty(name = "Colors", description = "Export vertex colors", default = true)
	option_uv_coords = BoolProperty(name = "UVs", description = "Export texture coordinates", default = true)

	option_skinning = BoolProperty(name = "Skinning", description = "Export skin data", default = true)
	option_bones = BoolProperty(name = "Bones", description = "Export bones", default = true)

	align_types = [("None","None","None"), ("Center","Center","Center"), ("Bottom","Bottom","Bottom"), ("Top","Top","Top")]
	align_model = EnumProperty(name = "Align model", description = "Align model", items = align_types, default = "None")

	option_flip_yz = BoolProperty(name = "Flip YZ", description = "Flip YZ", default = true)
	rotationDataTypes = [("Euler Angle","Euler Angle","Euler Angle"), ("Quaternion","Quaternion","Quaternion")]
	rotationDataType = EnumProperty(name = "Rotation data-type/structure", description = "How to store object rotations (euler angle is simpler, quaternion avoids gimbal lock)", items = rotationDataTypes, default = "Euler Angle")
	maxDecimalPlaces = IntProperty(name = "Max decimal places", description = "Round serialized numbers to have at most x decimal-places (-1 for no rounding)", min = -1, max = 30, soft_min = -1, soft_max = 30, default = 7)

	option_animation_morph = BoolProperty(name = "Morph animation", description = "Export animation (morphs)", default = false)
	option_animation_skeletal = BoolProperty(name = "Skeletal animation", description = "Export animation (skeletal)", default = false)
	option_frame_index_as_time = BoolProperty(name = "Frame index as time", description = "Use (original) frame index as frame time", default = false)

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
		v.s_defaultNumberTruncate = self.maxDecimalPlaces
		return io_scene_vmodel.export_vmodel.save(self, context, self.properties)
		v.s_defaultNumberTruncate = self.maxDecimalPlaces = -1

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
		row.prop(self.properties, "option_colors")
		layout.separator()

		row = layout.row()
		row.label(text="Settings:")

		row = layout.row()
		row.prop(self.properties, "align_model")
		row = layout.row()
		row.prop(self.properties, "option_flip_yz")
		row = layout.row()
		row.prop(self.properties, "rotationDataType")
		row = layout.row()
		row.prop(self.properties, "maxDecimalPlaces")
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


# ################################################################
# Common
# ################################################################
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
	register()