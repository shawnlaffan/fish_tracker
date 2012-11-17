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

#install_info = arcpy.GetInstallInfo()
#install_dir  = install_info["InstallDir"]
#default_coord_sys = os.path.join (
#    install_dir,
#    r"Coordinate Systems\Geographic Coordinate Systems\World\WGS 1984.prj"
#    #r"Coordinate Systems\Projected Coordinate Systems\World\WGS 1984.prj"
#    )
default_coord_sys = arcpy.SpatialReference ("WGS 1984")

def add_msg_and_print(msg, severity=0):
    # Adds a Message to the geoprocessor (in case this is run as a tool)
    # and also prints the message to the screen (standard output)
    # 
    #print msg

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
    time_fld_name = "DST"           #  FIXME:  make these arguments
    lat_fld_name  = "Lattitude_dd"
    lon_fld_name  = "Longitude_dd"
    t_diff_fld_name = "T_DIFF_HRS"

    in_table  = arcpy.GetParameterAsText (0)
    out_file  = arcpy.GetParameterAsText (1)
    coord_sys = arcpy.GetParameterAsText (2)
    workspace = arcpy.GetParameterAsText (3)

    if string.count(in_table, 'xls') and not string.count(in_table, 'Sheet1$'):
        in_table  = in_table + r"\Sheet1$"

    #arcpy.env.overwriteOutput = True

    arcpy.env.workspace = workspace
    if arcpy.env.workspace is None:
        arcpy.env.workspace = os.getcwd()

    arcpy.AddMessage ("Coordinate sys is %s" % arcpy.env.outputCoordinateSystem)
    arcpy.AddMessage ("coord_sys arg is %s" % coord_sys)
    if len(coord_sys) == 0 and arcpy.env.outputCoordinateSystem is None:
        coord_sys = default_coord_sys
    else:
        try:  #  is it a spatial ref string?
            sr = arcpy.SpatialReference()
            sr.loadFromString (coord_sys)
            #coord_sys = sr.name
            coord_sys = sr
        except Exception as e:
            arcpy.AddMessage (e)
            coord_sys = arcpy.SpatialReference (coord_sys)

    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)
    arcpy.AddMessage ('Output file is: %s' % out_file)
    arcpy.AddMessage ('Coord sys for result is %s' % coord_sys.name)

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

    #  output stuff
    arcpy.CreateFeatureclass_management (path, basename, "POINT")
    out_fc_name = os.path.join (path, basename)
    arcpy.AddMessage ('out_fc_name = %s' % out_fc_name)
    
    name_dict = {}
    for fld in fields:
        name = (fld.name)[0:9]
        name = name.replace (" ", "_")
        name_dict[fld.name] = name
        arcpy.AddField_management(out_fc_name, name, fld.type)
    arcpy.AddField_management(out_fc_name, t_diff_fld_name, "DOUBLE")

    cur      = arcpy.InsertCursor(out_fc_name)
    poly_pnt = arcpy.CreateObject("Point")


    rows = arcpy.SearchCursor(table_view)
    last_row = None
    prev_time = None
    row_count = -1
    t_diff_in_hours = 0

    for row in rows:
        row_count = row_count + 1
        this_time = row.getValue(time_fld_name)

        if prev_time is not None:
            time_diff = this_time - prev_time
            t_diff_in_hours = time_diff_in_hours(time_diff)

        poly_pnt.ID = row_count
        poly_pnt.X  = row.getValue(lon_fld_name)
        poly_pnt.Y  = row.getValue(lat_fld_name)

        feat = cur.newRow()
        feat.shape = poly_pnt

        #arcpy.AddMessage ("t_diff_fld_name = %s, t_diff_in_hours = %s" % (t_diff_fld_name, t_diff_in_hours))

        for fld in fields:
            name = name_dict[fld.name]
            val = row.getValue(fld.name)
            #arcpy.AddMessage ("name = %s, val = %s" % (name, val))
            feat.setValue(name, val)
        feat.ID = row_count

        feat.setValue(t_diff_fld_name, t_diff_in_hours)

        cur.insertRow(feat)

        prev_time = this_time

    count = arcmgt.GetCount (out_fc_name)
    count = int (count.getOutput(0))
    if count == 0:
        arcpy.AddError ("No features created - is there a file lock issue?")

    arcpy.DefineProjection_management(out_fc_name, coord_sys)    

    print arcpy.GetMessages()
    
    print "Completed"
    