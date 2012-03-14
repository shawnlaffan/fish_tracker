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
    in_table  = in_table + r"\Sheet1$"
    out_file  = arcpy.GetParameterAsText (1)
    polygon_file = arcpy.GetParameterAsText (2)
    workspace = arcpy.GetParameterAsText (3)

    arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if (arcpy.env.workspace is None):
        arcpy.env.workspace = os.getcwd()
    print "Workspace is", arcpy.env.workspace
    
    add_msg_and_print ('Currently in directory: %s\n' % os.getcwd())
    add_msg_and_print ('Workspace is: %s' % arcpy.env.workspace)
    
    #  get the path to the output table
    path = os.path.dirname(out_file)
    if len (path) == 0:
        path = "."
    basename = os.path.basename(out_file)
    
    
    #  Having identified the files we now iterate over the rows in the tables
    #  and add a number of fields
    table_view = "table_view"
    arcmgt.MakeTableView(in_table, table_view)
    
    fields = arcpy.ListFields(in_table)
    
    rows = arcpy.SearchCursor(table_view)
    last_row = None
    
    arcpy.env.outputCoordinateSystem = default_coord_sys
    arcpy.env.geographicTransformations = "GDA_1994_To_WGS_1984"
    arcpy.env.XYResolution = "0.0000000001 Meters"
    arcpy.env.XYTolerance  = "0.0000000001 Meters"
    
    featureList = []

    for row in rows:
        new_row = []
        for fld in fields:
            new_row.append (row.getValue(fld.name))
        
        if last_row is None:
            last_row = new_row
            continue
        
        for item in new_row:
            last_row.append (item)
        #pprint.pprint (last_row)
        time_diff = last_row[-1] - last_row[4]
        last_row.append (time_diff)
        last_row.append (time_diff_in_hours(time_diff))

        pnt1 = arcpy.CreateObject("Point")
        pnt1.X = last_row[3]
        pnt1.Y = last_row[2]
        pnt2 = arcpy.CreateObject("Point")
        pnt2.X = last_row[8]
        pnt2.Y = last_row[7]
        line_array = arcpy.CreateObject("Array")
        line_array.add(pnt1)
        line_array.add(pnt2)
        polyline = arcpy.Polyline(line_array)
        featureList.append(polyline)
        line_array.removeAll
        
        diff = ((last_row[8] - last_row[3]) ** 2 + (last_row[7] - last_row[2]) ** 2) ** 0.5
        print "%.10f %s" % (diff, polyline.length)

        last_row = new_row

    try:
        arcmgt.CopyFeatures(featureList, out_file)
        arcmgt.DefineProjection(out_file, default_coord_sys)
        add_msg_and_print("Completed")
    except:
        add_msg_and_print("Unable to save to %s" % out_file)