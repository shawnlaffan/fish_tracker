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


if __name__ == "__main__":

    in_file    = arcpy.GetParameterAsText (0)
    pop_fld    = arcpy.GetParameterAsText (1)
    kde_radius = arcpy.GetParameterAsText (2)
    mask       = arcpy.GetParameterAsText (3)
    workspace  = arcpy.GetParameterAsText (4)

    arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()
        
    if len (mask) > 0:
        arcpy.env.mask = mask
    if arcpy.env.cellSize is None or arcpy.env.cellSize in ["MAXOF", "MINOF"]:
        arcpy.env.cellSize = mask
    if arcpy.env.extent is None or arcpy.env.extent in ["MAXOF", "MINOF"]:
        arcpy.env.extent = mask
    
    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)
    arcpy.AddMessage ('Cell size is: %s' % arcpy.env.cellSize)

    try:
        kde = KernelDensity(in_file, pop_fld, "#", kde_radius, "HECTARES")
    except Exception as e:
        #print e.message
        #arcpy.AddError(e.message)
        print arcpy.GetMessages()
        raise

    percentiles = [0.1, 0.5]
    for percentile in percentiles:
        print "Calculating percentile %s" % percentile
        pctl_val = get_percentile (kde, percentile = percentile, skip_value = 0)
        clipped = Con (kde, 1, None, "Value > %s" % pctl_val)
        scratch = arcpy.CreateScratchName('pctl', str(int(percentile * 10)))
        clipped.save (scratch)
        
        print "%s is %s" % (percentile, pctl_val)

    print "Completed"
