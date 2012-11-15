"""
Process data tables collected for Matt Taylor's Mulloway research.
Determine if they are best BBQ'd or crumbed and oven roasted.
"""

class NoFeatures(Exception):
    pass

# Import arcpy module and other required modules
import arcpy
import arcpy.management as arcmgt
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")

import os
import numpy
#import pprint


if __name__ == "__main__":
    t_diff_fld_name = "T_DIFF_HRS"

    in_file    = arcpy.GetParameterAsText (0)
    cost_rast  = arcpy.GetParameterAsText (1)
    target_fld = arcpy.GetParameterAsText (2)
    workspace  = arcpy.GetParameterAsText (3)

    if len (target_fld) == 0 or target_fld == "#":
        target_fld = "New_WP"

    arcpy.env.overwriteOutput = True

    if arcpy.env.outputCoordinateSystem is None:
        arcpy.env.outputCoordinateSystem = cost_rast
    print arcpy.env.outputCoordinateSystem.name

    if len(workspace):
        arcpy.env.workspace = workspace
    if arcpy.env.workspace is None or len(arcpy.env.workspace) == 0:
        arcpy.env.workspace = os.getcwd()

    arcpy.env.snapRaster = cost_rast
    scratch = arcpy.CreateScratchName('xx', '.shp')
    try:
        arcpy.Buffer_analysis(in_file, scratch, "2000 meters")
    except Exception as e:
        arcpy.AddMessage (str(e))
        raise
    desc = arcpy.Describe(scratch)
    arcpy.env.extent = desc.extent
    arcmgt.Delete(scratch)
    print "Extent is %s" % arcpy.env.extent

    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)


    feat_layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, feat_layer)
    desc = arcpy.Describe (feat_layer)
    oid_fd_name = desc.OIDFieldName

    proc_layer = "process_layer"
    arcmgt.MakeFeatureLayer(in_file, proc_layer)
    rows = arcpy.SearchCursor(proc_layer)
    last_target = None

    for row in rows:

        if last_target is None:
            last_target = row.getValue(target_fld)
            last_oid    = row.ID
            continue

        arcmgt.SelectLayerByAttribute(
            feat_layer,
            "NEW_SELECTION",
            '%s = %s' % (target_fld, last_target)
        )
        backlink_rast  = arcpy.CreateScratchName("backlink")
        path_dist_rast = PathDistance(feat_layer, cost_rast, out_backlink_raster = backlink_rast)

        #  extract the distance from the last point
        shp = row.shape
        centroid = shp.centroid
        (x, y) = (centroid.X, centroid.Y)
        result = arcmgt.GetCellValue(path_dist_rast, "%s %s" % (x, y), "1")
        path_distance = result.getOutput(0)

        traverse_time = row.getValue (t_diff_fld_name)

        #  get a raster of the path from origin to destination
        #condition = '"%s" = %s or "%s" = %s' % (target_fld, last_target, target_fld, row.getValue(target_fld))
        condition = '%s in (%i, %i)' % (oid_fd_name, last_oid, row.ID)
        dest_layer = "dest_layer" + str (last_oid)
        arcmgt.MakeFeatureLayer(in_file, dest_layer, where_clause = condition)

        count = arcmgt.GetCount(dest_layer)
        count = int (count.getOutput(0))
        if count == 0:
            raise NoFeatures("No features selected.  Possible coordinate system issues.\n" + condition)

        path_rast = None
        try:
            path_rast = CostPath(dest_layer, path_dist_rast, backlink_rast)
            path_dist_rast.save(arcpy.CreateScratchName("pd%d_" % last_target))
            path_rast.save (arcpy.CreateScratchName("cp%d_" % last_target))
        except Exception as e:
            raise
            #arcpy.AddMessage (str (e))
        
        try:
            path_array    = arcpy.RasterToNumPyArray(path_dist_rast)
            transit_array = numpy.copy(path_array)
        except:
            raise
        nodata = path_dist_rast.noDataValue

        #  loop over the array and check the neighbours
        row_count = len (path_array) 
        col_count = len (path_array[0]) 
        i = -1
        for row in path_array:
            i = i + 1
            j = -1
            for val in row:
                j = j + 1
                if val == nodata:
                    continue
                nbrs = []
                for k in (i-1, i, i+1):
                    if k < 0 or k >= row_count:
                        continue    
                    checkrow = path_array[k]
                    for l in (j-1, j, j+1):
                        if l < 0 or l >= col_count:
                            continue
                        checkval = checkrow[l]
                        if checkval != nodata:
                            nbrs.append(checkval)
                minval = min (nbrs)
                print val, minval


        try:
            arcmgt.Delete(backlink_rast)
            arcmgt.Delete(dest_layer)
        except Exception as e:
            arcpy.AddMessage (e)

        last_target = row.getValue(target_fld)


    print "Completed"
