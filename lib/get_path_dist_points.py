"""
Process data tables collected for Matt Taylor's Mulloway research.
Determine if they are best BBQ'd or crumbed and oven roasted.
"""


# Import arcpy module and other required modules
import arcpy
import arcpy.management as arcmgt
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")

import os
import string
import math
import pprint

def add_fields_to_layer (layer):
    desc = arcpy.Describe(layer)
    fld_names = []
    for fld in desc.fields:
        fld_names.append(fld.name)
    
    try:
        fields = ["PATH_FROM", "PATH_TO", "PATH_DIST"]
        for fld in fields:
            if not fld in fld_names:
                arcmgt.AddField(table_view, fld, "DOUBLE")  #  SHOULD GET TYPE FROM target_fld
        
    except Exception as e:
        print e
        arcpy.AddError(str (e))
        raise
    return


if __name__ == "__main__":

    in_file    = arcpy.GetParameterAsText (0)
    cost_rast  = arcpy.GetParameterAsText (1)
    target_fld = arcpy.GetParameterAsText (2)
    workspace  = arcpy.GetParameterAsText (3)

    if len (target_fld) == 0 or target_fld == "#":
        target_fld = "New_WP"

    arcpy.env.overwriteOutput = True

    if arcpy.env.outputCoordinateSystem is None:
        arcpy.env.outputCoordinateSystem = cost_rast
    print arcpy.env.outputCoordinateSystem.name

    if len(workspace):
        arcpy.env.workspace = workspace
    if arcpy.env.workspace is None or len(arcpy.env.workspace) == 0:
        arcpy.env.workspace = os.getcwd()

    arcpy.env.snapRaster = cost_rast
    scratch = arcpy.CreateScratchName('xx', '.shp')
    try:
        arcpy.Buffer_analysis(in_file, scratch, "2000 meters")
    except Exception as e:
        arcpy.AddMessage (str(e))
        raise
    desc = arcpy.Describe(scratch)
    arcpy.env.extent = desc.extent
    arcmgt.Delete(scratch)
    print "Extent is %s" % arcpy.env.extent

    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)
    
    table_view = "table_view"
    arcmgt.MakeTableView(in_file, table_view)
    
    fields = arcpy.ListFields(in_file)
    
    feat_layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, feat_layer)
    
    add_fields_to_layer (feat_layer)

    dest_layer = "dest_layer"
    arcmgt.MakeFeatureLayer(in_file, dest_layer)

    rows = arcpy.UpdateCursor(table_view)
    last_target = None

    for row in rows:

        if last_target is None:
            last_target = row.getValue(target_fld)
            continue

        arcmgt.SelectLayerByAttribute(
            feat_layer,
            "NEW_SELECTION",
            '%s = %s' % (target_fld, last_target)
        )
        backlink_rast  = arcpy.CreateScratchName("backlink")
        path_dist_rast = PathDistance(feat_layer, cost_rast, out_backlink_raster = backlink_rast)

        shp = row.shape
        centroid = shp.centroid
        (x, y) = (centroid.X, centroid.Y)
        result = arcmgt.GetCellValue(path_dist_rast, "%s %s" % (x, y), "1")
        path_distance = result.getOutput(0)
        row.setValue("PATH_TO",   float (row.getValue(target_fld)))
        row.setValue("PATH_FROM", float (last_target))
        row.setValue("PATH_DIST", float (path_distance))
        print "%s,%s,%s" % (row.getValue(target_fld), last_target, path_distance)
        rows.updateRow(row)

        #  get a raster of the path from origin to destination

        condition = "%s = %s or %s = %s" % (target_fld, last_target, target_fld, row.getValue(target_fld))
        #print "Condition is: %s" % condition
        #result = int(arcmgt.GetCount(dest_layer).getOutput(0))
        #print result
        arcmgt.SelectLayerByAttribute(dest_layer, where_clause = condition)
        #result = int(arcmgt.GetCount(dest_layer).getOutput(0))
        #print result
        try:
            path_rast = CostPath(dest_layer, path_dist_rast, backlink_rast)
            #rate = time / path_distance
            #zero = Time (path_rast, 0)
            #rate_rast = Plus (zero, rate)
            path_dist_rast.save(arcpy.CreateScratchName("pd%d_" % last_target))
            path_rast.save (arcpy.CreateScratchName("cp%d_" % last_target))
        except Exception as e:
            arcpy.AddMessage (str (e))
        
        #  now we convert to point
        #print path_rast

        try:
            arcmgt.Delete(backlink_rast)
        except Exception as e:
            arcpy.AddMessage (str (e))

        last_target = row.getValue(target_fld)


    print "Completed"