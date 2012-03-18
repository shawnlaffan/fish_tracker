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

def add_msg_and_print(msg, severity=0):
    # Adds a Message to the geoprocessor (in case this is run as a tool)
    # and also prints the message to the screen (standard output)
    # 
    print msg

    # Split the message on \n first, so that if it's multiple lines, 
    #  a GPMessage will be added for each line
    try:
        for string in msg.split('\n'):
            # Add appropriate geoprocessing message 
            #
            if severity == 0:
                arcpy.AddMessage(string)
            elif severity == 1:
                arcpy.AddWarning(string)
            elif severity == 2:
                arcpy.AddError(string)
    except:
        pass


if __name__ == "__main__":

    in_file    = arcpy.GetParameterAsText (0)
    cost_rast  = arcpy.GetParameterAsText (1)
    target_fld = arcpy.GetParameterAsText (2)
    workspace  = arcpy.GetParameterAsText (3)

    if len (target_fld) == 0 or target_fld == "#":
        target_fld = "New_WP"

    arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()
    
    #arcpy.env.extent = "MINOF"
    arcpy.env.snapRaster = cost_rast
    scratch = arcpy.CreateScratchName('xx', '.shp')
    arcpy.Buffer_analysis(in_file, scratch, "2000 meters")
    desc = arcpy.Describe(scratch)
    arcpy.env.extent = desc.extent
    arcmgt.Delete(scratch)
    print "Extent is %s" % arcpy.env.extent

    add_msg_and_print ('Currently in directory: %s\n' % os.getcwd())
    add_msg_and_print ('Workspace is: %s' % arcpy.env.workspace)
    #add_msg_and_print ('Scratch table is: %s' % out_table)
    
    table_view = "table_view"
    arcmgt.MakeTableView(in_file, table_view)
    
    fields = arcpy.ListFields(in_file)
    
    
    layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, layer)
    desc = arcpy.Describe(layer)
    fld_names = []
    for fld in desc.fields:
        fld_names.append(fld.name)
    
    try:
        fields = ["PATH_FROM", "PATH_TO", "PATH_DIST"]
        #arcmgt.DeleteField(layer, fields)
        #arcmgt.DeleteField(layer, "FROM_")
        for fld in fields:
            if not fld in fld_names:
                arcmgt.AddField(table_view, fld, "DOUBLE")  #  SHOULD GET TYPE FROM target_fld
        
    except Exception as e:
        print e.message
        arcpy.AddError(e.message)
        raise
    
    dest_layer = "dest_layer"
    arcmgt.MakeFeatureLayer(in_file, dest_layer)

    rows = arcpy.UpdateCursor(table_view)
    last_target = None

    for row in rows:

        if last_target is None:
            last_target = row.getValue(target_fld)
            continue

        arcmgt.SelectLayerByAttribute(
            layer,
            "NEW_SELECTION",
            '%s = %s' % (target_fld, last_target)
        )
        backlink_rast  = arcpy.CreateScratchName("backlink")
        path_dist_rast = PathDistance(layer, cost_rast, out_backlink_raster = backlink_rast)

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
        
        condition = "%s in (%s, %s)" % (target_fld, last_target, row.getValue(target_fld))
        condition = "%s = %s or %s = %s" % (target_fld, last_target, target_fld, row.getValue(target_fld))
        print "Condition is: %s" % condition
        result = int(arcmgt.GetCount(dest_layer).getOutput(0))
        print result
        arcmgt.SelectLayerByAttribute(dest_layer, where_clause = condition)
        result = int(arcmgt.GetCount(dest_layer).getOutput(0))
        print result
        try:
            path_rast = CostPath(dest_layer, path_dist_rast, backlink_rast)
            rate = time / path_distance
            zero = Time (path_rast, 0)
            rate_rast = Plus (zero, rate)
            rate_rast.save(arcpy.CreateScratchName("cp"))
        except Exception as e:
            add_msg_and_print(e.message)
        
        #  now we convert to point
        

        try:
            arcmgt.Delete(backlink_rast)
        except Exception as e:
            add_msg_and_print(e.message)

        last_target = row.getValue(target_fld)


    print "Completed"
