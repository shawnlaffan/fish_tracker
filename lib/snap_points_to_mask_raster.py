#!/usr/bin/env python

"""
Snaps the point features to the cost raster to ensure all are inside.
FIXME:  Moves points in the original file!
"""

import os, re

# Import arcpy module and other required modules
import arcpy
import arcpy.management as arcmgt

def snap_points_to_mask_raster (in_file, mask, out_file, distance, workspace):
    
    if distance is None or len (distance) == 0:
        distance = "100 METERS"
    
    if arcpy.env.outputCoordinateSystem is None:
        arcpy.env.outputCoordinateSystem = mask
    print arcpy.env.outputCoordinateSystem.name

    if len(workspace):
        arcpy.env.workspace = workspace
    if arcpy.env.workspace is None or len(arcpy.env.workspace) == 0:
        arcpy.env.workspace = os.getcwd()

    arcpy.AddMessage ("workspace is %s" % arcpy.env.workspace)

    try:
        suffix = None
        wk = arcpy.env.workspace
        if not '.gdb' in wk:
            suffix = '.shp'
        poly_file = arcpy.CreateScratchName(None, suffix, 'POLYGON')
        arcpy.RasterToPolygon_conversion (mask, poly_file, 'NO_SIMPLIFY')
    except:
        raise

    arcpy.AddMessage ("poly_file is %s" % poly_file)

    #  handle layers and datasets
    desc = arcpy.Describe(in_file)
    in_file = desc.catalogPath

    #  add .shp extension if needed - clunky, but otherwise system fails below
    re_gdb = re.compile ('\.gdb$')
    path = os.path.dirname(out_file)
    if len (path) == 0:
        path = arcpy.env.workspace
    if not re_gdb.search (path):
        out_file += '.shp'

    arcpy.AddMessage ("Input point file is %s" % in_file)
    arcpy.AddMessage ("Output point file is %s" % out_file)

    arcmgt.CopyFeatures (in_file, out_file)

    try:
        snap_layer_name = 'get_layer_for_snapping'
        arcmgt.MakeFeatureLayer (out_file, snap_layer_name)
        arcmgt.SelectLayerByLocation (snap_layer_name, 'intersect', poly_file, '#', 'NEW_SELECTION')
        arcmgt.SelectLayerByAttribute(snap_layer_name, 'SWITCH_SELECTION')
        if arcmgt.GetCount(snap_layer_name) > 0:
            arcpy.Snap_edit (snap_layer_name, [[poly_file, "EDGE", distance]])
        else:
            arcpy.AddMessage ('No features selected, no snapping applied')
    except Exception as e:
        print arcpy.GetMessages()
        raise e

    arcmgt.Delete (snap_layer_name)
    arcmgt.Delete (poly_file)

    print arcpy.GetMessages()
    print "Completed"

    return

if __name__ == "__main__":
    in_file   = arcpy.GetParameterAsText (0)
    mask      = arcpy.GetParameterAsText (1)
    out_file  = arcpy.GetParameterAsText (2)
    distance  = arcpy.GetParameterAsText (3)
    workspace = arcpy.GetParameterAsText (4)

    snap_points_to_mask_raster (in_file, mask, out_file, distance, workspace)
