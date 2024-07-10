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
import random

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


def get_percentile (in_file, percentile = 0.5, multiplier = 0, skip_value = None):
    # mult_rast = Times (in_file, multiplier)
    multiplier = float(multiplier)
    if multiplier == 0:
        max = float (arcpy.GetRasterProperties_management (in_file, "MAXIMUM").getOutput (0))
        multiplier = 2048 / max
        add_msg_and_print("Percentile multiplier : " + str(multiplier))
        # add_msg_and_print("Max IS: " + str(max))
        # add_msg_and_print("F IS: " + str(in_file))
    
    int_rast  = Int (Times (in_file, multiplier))
    
    #  no idea why this is needed, but something needs to tickle int_rast
    print (int_rast)

    #  the print statement is not always enough 
    temp_int_name = arcpy.CreateScratchName("pctl_int")
    try:
        int_rast.save(temp_int_name)
    except Exception as e:
        arcpy.AddMessage (e)
                
    # add_msg_and_print("Int IS: " + str(int_rast))
    
    arcmgt.BuildRasterAttributeTable(int_rast)

    table_view = "table_view%d" % int (random.random() * 1000)
    arcmgt.MakeTableView(int_rast, table_view)

    fields = arcpy.ListFields(in_file)
    
    rows = arcpy.SearchCursor(table_view)
    cum_sum = 0

    for row in rows:
    
        val   = row.getValue("Value")
        count = row.getValue("Count")
        
        if val == skip_value:
            continue
        
        cum_sum = cum_sum + count

    row = None

    target = cum_sum * percentile

    rows2 = arcpy.SearchCursor(table_view)
    cum_sum = 0
    val = 0

    for row2 in rows2:
    
        val   = row2.getValue("Value")
        count = row2.getValue("Count")
        
        if val == skip_value:
            continue
        
        cum_sum = cum_sum + count

        if cum_sum >= target:
            break

    val = float (val) / multiplier

    arcmgt.Delete (table_view)
    arcmgt.Delete (temp_int_name)
    
    add_msg_and_print("Percentile threshold is: " + str(val))
    
    return val


if __name__ == "__main__":

    in_file     = arcpy.GetParameterAsText (0)
    percentile  = arcpy.GetParameterAsText (1)
    skip_value  = arcpy.GetParameterAsText (2)
    multiplier  = arcpy.GetParameterAsText (3)
    workspace   = arcpy.GetParameterAsText (4)

    if len (multiplier) == 0 or multiplier == "#":
        multiplier = 0
    if len (skip_value) == 0 or skip_value == "#":
        skip_value = None
    if not skip_value is None:
        skip_value = int (skip_value)
    percentile = float (percentile)

    arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()
    
    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)

    val = get_percentile(in_file, percentile, multiplier, skip_value)

    print "Value is %s" % (val)

    print "Completed"
