"""
Get home ranges for a set of data points.
Does median and upper 90th percentile.
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

from get_raster_percentile import *

def threshold_raster_by_percentile (in_file, out_file, percentile, multiplier, skip_value, workspace):
    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()

    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)
    arcpy.AddMessage ('Cell size is: %s' % arcpy.env.cellSize)
    
    if len (skip_value) == 0 or skip_value == "#":
        skip_value = None
    arcpy.AddMessage ("skip_value is " + skip_value)

    #  should use pass-through
    threshold = get_percentile (in_file, percentile, multiplier, skip_value)
    
    clipped = Con (in_file, 1, None, "Value > %s" % threshold)
    #scratch = arcpy.CreateScratchName('pctl', str(int(percentile * 10)))
    clipped.save (out_file)

    print "Completed"

    return

if __name__ == "__main__":
    #import sys
    #arcpy.AddMessage (sys.argv[1:])
    #params = arcpy.GetParameterInfo()
    #arcpy.AddMessage(params)
    in_raster  = arcpy.GetParameterAsText (0)
    out_raster = arcpy.GetParameterAsText (1)
    pctl       = arcpy.GetParameterAsText (2)
    skip_val   = arcpy.GetParameterAsText (3)
    multiplier = arcpy.GetParameterAsText (4)
    workspace  = arcpy.GetParameterAsText (5)
    
    arcpy.AddMessage (in_raster)

    threshold_raster_by_percentile (in_raster, out_raster, pctl, skip_val, multiplier, workspace)

    arcpy.AddMessage ("Percentile threshold process completed")
