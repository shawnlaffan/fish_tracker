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

    in_file   = arcpy.GetParameterAsText (0)
    out_file  = arcpy.GetParameterAsText (1)
    cost_rast = arcpy.GetParameterAsText (2)
    workspace = arcpy.GetParameterAsText (3)

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
    
    #  get the path to the output table
    path = os.path.dirname(out_file)
    if len (path) == 0:
        path = "."
    basename = os.path.basename(out_file)
    
    table_view = "table_view"
    arcmgt.MakeTableView(in_file, table_view)
    
    fields = arcpy.ListFields(in_file)
    
    rows = arcpy.SearchCursor(table_view)
    last_target = None
    
    layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, layer)
    target_fld = "New_WP"

    for row in rows:
        
        if last_target is None:
            last_target = row.getValue(target_fld)
            continue
        
        arcmgt.SelectLayerByAttribute(
            layer,
            "NEW_SELECTION",
            '%s = %s' % (target_fld, last_target)
        )
        raster = PathDistance(layer, cost_rast)
        #scratch = arcpy.CreateScratchName('xx')
        #raster.save(scratch)
        
        shp = row.shape
        centroid = shp.centroid
        (x, y) = (centroid.X, centroid.Y)
        result = arcmgt.GetCellValue(raster, "%s %s" % (x, y), "1")
        print "%s,%s,%s" % (row.getValue(target_fld), last_target, result.getOutput(0))
        
        last_target = row.getValue(target_fld)


    print "Completed"
