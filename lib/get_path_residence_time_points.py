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

    arcpy.env.cellSize = cost_rast
    print "Cell size is %s" % arcpy.env.cellSize
    cellsize_used = float (arcpy.env.cellSize)
    extent = arcpy.env.extent
    lower_left_coord = extent.lowerLeft

    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)

    #  cumulative transits
    transit_array_cum = arcpy.RasterToNumPyArray (CreateConstantRaster (0))

    feat_layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, feat_layer)
    desc = arcpy.Describe (feat_layer)
    oid_fd_name = desc.OIDFieldName

    proc_layer = "process_layer"
    arcmgt.MakeFeatureLayer(in_file, proc_layer)
    rows = arcpy.SearchCursor(proc_layer)
    last_target = None

    for row_cur in rows:

        if last_target is None:
            last_target = row_cur.getValue(target_fld)
            last_oid    = row_cur.ID
            continue

        arcmgt.SelectLayerByAttribute(
            feat_layer,
            "NEW_SELECTION",
            '%s = %s' % (target_fld, last_target)
        )
        backlink_rast  = arcpy.CreateScratchName("backlink")
        backlink_rast  = None
        path_dist_rast = PathDistance(feat_layer, cost_rast, out_backlink_raster = backlink_rast)

        #  extract the distance from the last point
        shp = row_cur.shape
        centroid = shp.centroid
        (x, y) = (centroid.X, centroid.Y)
        result = arcmgt.GetCellValue(path_dist_rast, "%s %s" % (x, y), "1")
        path_distance = result.getOutput(0)

        #  get a raster of the path from origin to destination
        #condition = '"%s" = %s or "%s" = %s' % (target_fld, last_target, target_fld, row.getValue(target_fld))
        condition = '%s in (%i, %i)' % (oid_fd_name, last_oid, row_cur.ID)
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
            transit_array = path_array * 0
        except:
            raise
        nodata = path_dist_rast.noDataValue

        transit_time = row_cur.getValue (t_diff_fld_name)
        path_sum = 0
        #  loop over the array and check the neighbours
        #  brute force search - need to follow the path
        row_count = len (path_array) 
        col_count = len (path_array[0])
        print "processing path raster, %i rows, %i cols" % (row_count, col_count)
        i = -1
        for row in path_array:
            i = i + 1
            if row.max() == 0:  #  skip empty rows, should be faster than checking in the loop
                continue
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
                diff = val - minval
                transit_array[i][j] = diff

        path_sum = path_array.max()
        #  now calculate speed
        speed = path_sum / transit_time
        transit_array_cum = transit_array_cum + transit_array / speed
        print "%s, %s, %s, %s" % (path_sum, transit_array.max(), transit_array_cum.max(), speed)

        #  need to use env settings to get it to be the correct size
        xx = arcpy.NumPyArrayToRaster (transit_array_cum, lower_left_coord, cellsize_used, cellsize_used, nodata)
        scratch = arcpy.CreateScratchName ('trans_cum', '.img', 'raster')
        print "Saving to %s" % scratch
        xx.save (scratch)

        try:
            arcmgt.Delete(backlink_rast)
            arcmgt.Delete(dest_layer)
        except Exception as e:
            arcpy.AddMessage (e)

        last_target = row_cur.getValue(target_fld)


    print "Completed"
