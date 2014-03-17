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

#  All Rights Reserved. VUE(R) is a registered trademark of e-on software, inc.
#  http://www.e-onsoftware.com/

# <pep8 compliant>

bl_info = {
    "name": "Export Vue Synchro Data",
    "author": "Maxim Seliverstov",
    "version": (0, 1),
    "blender": (2, 57, 0),
    "location": "File > Export > Export Vue Synchro Data (.dat)", 
    "description": "Export Vue Synchro Data (.dat)",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"}


import bpy
import os, sys
import struct
from math import radians
import math
from mathutils import Matrix


def create_header(fw, frame_start, frame_end, scene_frame_range, scale, type_obj):
    scene = bpy.context.scene
    
    obj_name = create_obj_name(type_obj)

    selected = bpy.context.selected_objects
    num_name = 36 + (12 * len(selected))

    end_name = (num_name+len(obj_name))

    frames_len = frame_end - frame_start

    header = struct.pack('iiiifiiff', 
                36,                                                              # un name
                len(selected),                                                   # num_obj
                frames_len,                                                      # num_frames
                frame_start,                                                     # start_frame
                scene.render.fps,                                                # fps
                scene.render.resolution_x,                                       # feame_width
                scene.render.resolution_y,                                       # frame_height
                scene.render.pixel_aspect_x / scene.render.pixel_aspect_y,       # pixel_aspect
                scale)

    fw.write(header)

    for ob in selected:

        if ob.type == 'CAMERA':
            type_obj = 1
            len_data = 116
        else:
            type_obj = 2
            len_data = 48

        table = struct.pack('iii',
                type_obj,
                num_name,
                end_name)
        fw.write(table)

        num_name += len(ob.name)+1
        end_name += (frames_len+1) * len_data



    fw.write(obj_name)


def create_obj_name(type_obj):
    selected = bpy.context.selected_objects

    obj_name = b''

    for obj in selected:
        name = obj.name.encode('utf-8')
        obj_name += name + b'\x00'

    return obj_name

def create_frame(obj, frame):
    cam_obj = bpy.data.objects[obj]
    matrix = cam_obj.matrix_world
    scene = bpy.context.scene

    if  cam_obj.type == 'CAMERA':

        neg_rot_x = Matrix.Rotation(radians(180), 4, 'X')
        neg_rot_z = Matrix.Rotation(radians(180), 4, 'Z')

        matrix = matrix * neg_rot_x * neg_rot_z
    
    row0 = struct.pack('fff', 
                        matrix[0][3],
                        matrix[1][3],
                        matrix[2][3])

    row1 = struct.pack('fff', 
                        matrix[0][0],
                        matrix[0][1],
                        matrix[0][2])


    row2 = struct.pack('fff',
                        matrix[1][0],
                        matrix[1][1],
                        matrix[1][2])

    row3 = struct.pack('fff',
                        matrix[2][0],
                        matrix[2][1],
                        matrix[2][2])

    
    if cam_obj.type == 'CAMERA':
        fov = cam_obj.data.lens/2
        
        vuesensor=35.975130221963276
        angl=cam_obj.data.angle
        fov=(vuesensor/2)/math.tan(angl/2)
        fov=fov/2

        motion_blur = scene.render.motion_blur_shutter
        focus = cam_obj.data.dof_distance

        row4 = struct.pack('fff', fov, focus, motion_blur)
        
        row5 = struct.pack('fff', 1.0, 1.1, 1.2)
        row6 = struct.pack('fff', 2.0, 2.1, 2.2)
        row7 = struct.pack('fff', 3.0, 3.1, 3.2)
        row8 = struct.pack('fff', 4.0, 4.1, 4.2)

        row_Z = struct.pack('ff', fov, focus)

    
        frame = row0 + row1 + row2 + row3 + row4 + row5 + row6 + row7 + row8 + row_Z
    else:
        frame = row0 + row1 + row2 + row3

    return frame

def create_dat_file(filepath, frame_start, frame_end, type_obj, scene_frame_range, scale):
        
    selected = bpy.context.selected_objects
    scene = bpy.context.scene

    fw = open(filepath, 'wb+')
    create_header(fw, frame_start, frame_end, scene_frame_range, scale, type_obj)

    for obj in selected:
        for f in range(frame_start, frame_end+1):
            scene.frame_set(f)
            frame = create_frame(obj.name, f)
            fw.write(frame)
    
    fw.close

from bpy.props import StringProperty, IntProperty, BoolProperty, FloatProperty
from bpy_extras.io_utils import ExportHelper

class VueSynchDataExporter(bpy.types.Operator, ExportHelper):
    """Save a python script which re-creates cameras and markers elsewhere"""
    bl_idname = "export_vue_synchdata.cameras"
    bl_label = "Export Vue Synchro Data"

    filename_ext = ".dat"
    filter_glob = StringProperty(default="*.dat", options={'HIDDEN'})

    world_scale = FloatProperty(name="Scale",
            description="World Scale",
            default=1.0, min=0, max=1000)
    scene_frame_range = BoolProperty(name="Use scene frame range",
            default=False)
    frame_start = IntProperty(name="Start Frame",
            description="Start frame for export",
            default=1, min=1, max=300000)
    frame_end = IntProperty(name="End Frame",
            description="End frame for export",
            default=250, min=1, max=300000)
    only_selected = BoolProperty(name="Only Selected",
            default=True)

    def execute(self, context):
        create_dat_file(self.filepath, self.frame_start, self.frame_end, self.only_selected, self.scene_frame_range, self.world_scale)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.frame_start = context.scene.frame_start
        self.frame_end = context.scene.frame_end

        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_export(self, context):
    import os
    default_path = os.path.splitext(bpy.data.filepath)[0] + ".dat"
    self.layout.operator(VueSynchDataExporter.bl_idname, text="Export Vue Synchro Data  (.dat)").filepath = default_path


def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_export.append(menu_export)


def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_export.remove(menu_export)


if __name__ == "__main__":
    register()
