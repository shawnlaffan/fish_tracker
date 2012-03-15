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
        
    if not mask is None:
        arcpy.env.mask = mask
    if arcpy.env.cellSize is None or arcpy.env.cellSize in ["MAXOF", "MINOF"]:
        arcpy.env.cellSize = mask
    if arcpy.env.extent is None or arcpy.env.extent in ["MAXOF", "MINOF"]:
        arcpy.env.extent = mask
    
    add_msg_and_print ('Currently in directory: %s\n' % os.getcwd())
    add_msg_and_print ('Workspace is: %s' % arcpy.env.workspace)
    add_msg_and_print ('Cell size is: %s' % arcpy.env.cellSize)

    try:
        kde = KernelDensity(in_file, pop_fld, "#", kde_radius, "HECTARES")
    except Exception as e:
        print e.message
        arcpy.AddError(e.message)
        raise
    
    percentiles = [0.1, 0.5]
    for percentile in percentiles:
        print "Calculating percentile %s" % percentile
        pctl_val = get_percentile (kde, percentile = percentile, skip_value = 0)
        clipped = Con (kde, 1, None, "Value > %s" % pctl_val)
        clipped.save ("xx" + str (int (percentile * 10)))
        print "%s is %s" % (percentile, pctl_val)

    print "Completed"
