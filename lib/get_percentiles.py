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

    in_file     = arcpy.GetParameterAsText (0)
    percentiles = arcpy.GetParameterAsText (1)
    skip_val    = arcpy.GetParameterAsText (2)
    multiplier  = arcpy.GetParameterAsText (3)
    workspace   = arcpy.GetParameterAsText (4)

    if len (multiplier) == 0 or multiplier == "#":
        multiplier = 100
    if len (skip_val) == 0 or skip_val == "#":
        skip_val = None
    if not skip_val is None:
        skip_val = int (skip_val)

    arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()
    
    add_msg_and_print ('Currently in directory: %s\n' % os.getcwd())
    add_msg_and_print ('Workspace is: %s' % arcpy.env.workspace)
    
    mult_rast = Times (in_file, multiplier)
    int_rast  = Int (mult_rast)
    arcmgt.BuildRasterAttributeTable(int_rast)
    
    table_view = "table_view"
    arcmgt.MakeTableView(int_rast, table_view)
    
    fields = arcpy.ListFields(in_file)
    
    rows = arcpy.SearchCursor(table_view)
    cum_sum = 0

    for row in rows:
    
        val   = row.getValue("Value")
        count = row.getValue("Count")
        
        if val == skip_val:
            continue
        
        cum_sum = cum_sum + count

    row = None

    target = cum_sum * 0.1

    rows2 = arcpy.SearchCursor(table_view)
    cum_sum = 0
    val = 0

    for row2 in rows2:
    
        val   = row2.getValue("Value")
        count = row2.getValue("Count")
        
        if val == skip_val:
            continue
        
        cum_sum = cum_sum + count

        if cum_sum >= target:
            break

    print "Value is %s, cum_sum is %s, target was %s" % (val, cum_sum, target)



    print "Completed"
