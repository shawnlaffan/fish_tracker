"""
Process data tables collected for Matt Taylor's Mulloway research.
Determine if they are best BBQ'd or crumbed and oven roasted.
"""


# Import arcpy module and other required modules
import arcpy
import arcpy.management as arcmgt

import os
import string
import math
import pprint

install_info = arcpy.GetInstallInfo()
install_dir  = install_info["InstallDir"]
default_coord_sys = os.path.join (
    install_dir,
    r"Coordinate Systems\Geographic Coordinate Systems\World\WGS 1984.prj"
    #r"Coordinate Systems\Projected Coordinate Systems\World\WGS 1984.prj"
    )

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

def time_diff_in_hours (td):
    return td.days * 24 + td.seconds / 3600.0




if __name__ == "__main__":

    in_table  = arcpy.GetParameterAsText (0)
    out_file  = arcpy.GetParameterAsText (1)
    polygon_file = arcpy.GetParameterAsText (2)
    workspace = arcpy.GetParameterAsText (3)

    arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()

    add_msg_and_print ('Currently in directory: %s\n' % os.getcwd())
    add_msg_and_print ('Workspace is: %s' % arcpy.env.workspace)
    #add_msg_and_print ('Scratch table is: %s' % out_table)
    
    #  get the path to the output table
    path = os.path.dirname(out_file)
    if len (path) == 0:
        path = "."
    basename = os.path.basename(out_file)
    
    #desc = arcpy.Describe(polygon_file)
    #sr = desc.spatialReference
    arcpy.env.outputCoordinateSystem = default_coord_sys
    arcpy.env.geographicTransformations = "GDA_1994_To_WGS_1984"
    arcpy.env.XYResolution = "0.0000000001 Meters"
    arcpy.env.XYTolerance  = "0.0000000001 Meters"
    
    temp_xy = arcpy.CreateScratchName("xx", ".shp")
    add_msg_and_print("temp_xy is %s" % temp_xy)
    try:
        arcmgt.XYToLine(in_table, temp_xy, "Longitude_dd", "Lattitude_dd", "Longitude_dd_2", "Lattitude_dd_2", "GEODESIC", "New_WP")
        
    except:
        add_msg_and_print ("Unable to create XY to line feature class")
        raise
    layer = "feat_layer"
    arcmgt.MakeFeatureLayer(temp_xy, layer)
    
    arcmgt.SelectLayerByLocation(layer, "COMPLETELY_WITHIN", polygon_file)
    arcmgt.SelectLayerByAttribute(layer, "SWITCH_SELECTION")
    
    temp_overlap = arcpy.CreateScratchName("xx_overlap_", ".shp")
    arcpy.CopyFeatures_management(layer, temp_overlap)

    #  now we need to iterate over those overlapping vertices and integrate them with the boundary polygon

    print "Completed"
    
