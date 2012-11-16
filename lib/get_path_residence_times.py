"""
Process data tables collected for Matt Taylor's Mulloway research.
Determine if they are best with or without tartare sauce.
"""

class NoFeatures(Exception):
    pass

class PointNotOnRaster(Exception):
    pass

# Import arcpy module and other required modules
import arcpy
import arcpy.management as arcmgt
from arcpy.sa import *
arcpy.CheckOutExtension("Spatial")

import os
import numpy
from pprint import pprint


if __name__ == "__main__":
    t_diff_fld_name = "T_DIFF_HRS"

    in_file    = arcpy.GetParameterAsText (0)
    cost_rast  = arcpy.GetParameterAsText (1)
    out_raster = arcpy.GetParameterAsText (2)
    target_fld = arcpy.GetParameterAsText (3)
    workspace  = arcpy.GetParameterAsText (4)
    
    if len (out_raster) == 0:
        arcpy.AddError ("Missing argument: out_rast")
        raise Exception

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
    transit_array_accum = arcpy.RasterToNumPyArray (CreateConstantRaster (0))

    feat_layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, feat_layer)
    desc = arcpy.Describe (feat_layer)
    oid_fd_name = desc.OIDFieldName

    proc_layer = "process_layer"
    arcmgt.MakeFeatureLayer(in_file, proc_layer)
    rows = arcpy.SearchCursor(proc_layer)
    last_target = None

    for row_cur in rows:
        transit_time = row_cur.getValue (t_diff_fld_name)

        if last_target is None or transit_time == 0:
            arcpy.AddMessage('Skipping record %s' % row_cur.getValue(oid_fd_name))
            last_target = row_cur.getValue(target_fld)
            last_oid    = row_cur.ID
            continue

        arcpy.AddMessage ("Processing OID %i" % cur_row.getValue(oid_fd_name))

        arcmgt.SelectLayerByAttribute(
            feat_layer,
            "NEW_SELECTION",
            '%s = %s' % (target_fld, last_target)
        )
        backlink_rast  = arcpy.CreateScratchName("backlink")
        path_dist_rast = PathDistance(feat_layer, cost_rast, out_backlink_raster = backlink_rast)

        #  extract the distance from the last point
        shp = row_cur.shape
        centroid = shp.centroid
        (x, y) = (centroid.X, centroid.Y)
        result = arcmgt.GetCellValue(path_dist_rast, "%s %s" % (x, y), "1")
        path_distance = result.getOutput(0)

        #  get a raster of the path from origin to destination
        condition = '%s in (%i, %i)' % (oid_fd_name, last_oid, row_cur.ID)
        dest_layer = "dest_layer" + str (last_oid)
        arcmgt.MakeFeatureLayer(in_file, dest_layer, where_clause = condition)

        count = arcmgt.GetCount(dest_layer)
        count = int (count.getOutput(0))
        if count == 0:
            raise NoFeatures("No features selected.  Possible coordinate system issues.\n" + condition)

        try:
            path_cost_rast = CostPath(dest_layer, path_dist_rast, backlink_rast)
            path_cost_rast.save (arcpy.CreateScratchName("cp%d_" % last_target))
            path_dist_rast.save (arcpy.CreateScratchName("pd%d_" % last_target))
        except Exception as e:
            raise

        nodata = path_dist_rast.noDataValue

        try:
            dist_masked    = path_dist_rast * (path_cost_rast * 0 + 1)
            path_array     = arcpy.RasterToNumPyArray(dist_masked)
            path_array_idx = numpy.where(path_array != nodata)
            transit_array  = numpy.zeros_like(path_array)
        except:
            raise

        if len(path_array_idx[0]) == 1:
            arcpy.AddError ("point does not intersect the raster, OID is %s" % row.getValue (oid_fd_name))
            raise PointNotOnRaster

        path_sum  = 0
        row_count = len (path_array) 
        col_count = len (path_array[0])
        print "processing %i cells of path raster" % (len(path_array_idx[0]))
        for idx in range (len(path_array_idx[0])):
            i = path_array_idx[0][idx]
            j = path_array_idx[1][idx]
            val = path_array[i][j]
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
        #  and increment the cumulative transit array
        transit_array_accum = transit_array_accum + transit_array / speed

        try:
            arcmgt.Delete(backlink_rast)
            arcmgt.Delete(dest_layer)
        except Exception as e:
            arcpy.AddMessage (e)

        last_target = row_cur.getValue(target_fld)
        last_oid    = row_cur.ID

    #  need to use env settings to get it to be the correct size
    try:
        xx = arcpy.NumPyArrayToRaster (transit_array_accum, lower_left_coord, cellsize_used, cellsize_used, 0)
        print "Saving to %s" % out_raster
        xx.save (out_raster)
    except:
        raise


    print "Completed"
