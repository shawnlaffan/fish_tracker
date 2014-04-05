"""
Process data tables collected for Matt Taylor's Mulloway research.
Determine if they are best with or without tartare sauce.
"""

class NoFeatures(Exception):
    pass

class PointNotOnRaster(Exception):
    pass

class WorkspaceIsGeodatabase (Exception):
    pass

class CostRasterIsZero(Exception):
    pass

class NumPyArrayExceedsSizeLimits (Exception):
    pass


# Import arcpy module and other required modules
import arcpy
import arcpy.management as arcmgt
#from arcpy.sa import *
from arcpy.sa import Raster, CostPath, PathDistance, IsNull

arcpy.CheckOutExtension("Spatial")

import os
import numpy
from pprint import pprint


def check_points_are_in_in_cost_raster(in_file, raster):
    proc_layer = "checker"
    arcmgt.MakeFeatureLayer(in_file, proc_layer)
    rows = arcpy.SearchCursor(proc_layer)

    for row_cur in rows:
        shp = row_cur.shape
        centroid = shp.centroid
        (x, y) = (centroid.X, centroid.Y)
        result = arcmgt.GetCellValue(raster, "%s %s" % (x, y), "1")
        value = result.getOutput(0)
        if value == 'NoData':
            return 0
        #print value

    return 1


def get_path_residence_times (in_file, cost_rast, out_raster, t_diff_fld_name, workspace):
    
    if len (out_raster) == 0:
        arcpy.AddError ("Missing argument: out_rast")
        raise Exception
    if len (t_diff_fld_name) == 0:
        t_diff_fld_name = "T_DIFF_HRS"

    arcpy.env.overwriteOutput = True  #  This is underhanded.  It should be an argument.

    if arcpy.env.outputCoordinateSystem is None:
        arcpy.env.outputCoordinateSystem = cost_rast
    arcpy.AddMessage ("coordinate system is %s" % arcpy.env.outputCoordinateSystem.name)

    if len(workspace):
        arcpy.env.workspace = workspace
    if arcpy.env.workspace is None or len(arcpy.env.workspace) == 0:
        arcpy.env.workspace = os.getcwd()

    if '.gdb' in arcpy.env.workspace:
        arcpy.AddError (
            "Worskpace is a geodatabase.  " +
            "This brings too much pain for this script to work.\n" +
            "%s" % arcpy.env.workspace
        )
        raise WorkspaceIsGeodatabase


    r = Raster(cost_rast)
    
    if r.maximum == 0 and r.minimum == 0:
        arcpy.AddMessage ('Cost raster has only zero value.  Cannot calculate cost distances.')
        raise CostRasterIsZero

    size = r.height * r.width * 4
    if size > 2 * 1028 ** 3:
        import struct
        struct_size = struct.calcsize("P") * 8
        if struct_size == 32:
            size_in_gb = float (size) / (1028 ** 3)
            arcpy.AddMessage (
                'Cost raster exceeds 2 GiB in size (%s GiB).  This is too large for a 32 bit NumPy.' % size_in_gb
            )
            raise NumPyArrayExceedsSizeLimits

    if not check_points_are_in_in_cost_raster(in_file, cost_rast):
        arcpy.AddError ('One or more input points do not intersect the cost raster')
        raise PointNotOnRaster

    arcpy.env.snapRaster = cost_rast
    suffix = None
    wk = arcpy.env.workspace
    if not '.gdb' in wk:
        suffix = '.shp'


    ext = arcpy.env.extent
    if ext is None:
        arcpy.env.extent = r.extent

    arcpy.AddMessage ("Extent is %s" % arcpy.env.extent)

    arcpy.env.cellSize = r.meanCellWidth
    arcpy.AddMessage ("Cell size is %s" % arcpy.env.cellSize)
    cellsize_used = float (arcpy.env.cellSize)
    extent = arcpy.env.extent
    lower_left_coord = extent.lowerLeft
    
    arcpy.AddMessage ('Currently in directory: %s\n' % os.getcwd())
    arcpy.AddMessage ('Workspace is: %s' % arcpy.env.workspace)
    arcpy.AddMessage ("lower left is %s" % lower_left_coord)

    if arcpy.env.mask is None:
        arcpy.AddMessage ("Setting mask to %s" % cost_rast)
        arcpy.env.mask = cost_rast

    #  accumulated transits
    transit_array_accum = arcpy.RasterToNumPyArray (Raster(cost_rast) * 0)

    feat_layer = "feat_layer"
    arcmgt.MakeFeatureLayer(in_file, feat_layer)
    desc = arcpy.Describe (feat_layer)
    oid_fd_name = desc.OIDFieldName
    arcpy.AddMessage("oid_fd_name = %s" % oid_fd_name)

    #  variable name is redundant now??? - should all calls be to oid_fd_name?
    target_fld = oid_fd_name

    proc_layer = "process_layer"
    arcmgt.MakeFeatureLayer(in_file, proc_layer)
    rows = arcpy.SearchCursor(proc_layer)
    last_target = None

    for row_cur in rows:
        transit_time = row_cur.getValue (t_diff_fld_name)

        if last_target is None or transit_time == 0:
            message = 'Skipping %s = %s' % (oid_fd_name, row_cur.getValue(oid_fd_name))
            if transit_time == 0:
                message = message + "  Transit time is zero"
            arcpy.AddMessage(message)
            last_target = row_cur.getValue(target_fld)
            last_oid    = row_cur.getValue(oid_fd_name)
            continue

        arcpy.AddMessage ("Processing %s %i" % (oid_fd_name, row_cur.getValue(oid_fd_name)))

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
        path_distance = float (result.getOutput(0))
        arcpy.AddMessage("Path distance is %s\nTransit time is %s" % (path_distance, transit_time))

        #  get a raster of the path from origin to destination
        condition = '%s in (%i, %i)' % (oid_fd_name, last_oid, row_cur.getValue(oid_fd_name))
        dest_layer = "dest_layer" + str (last_oid)
        arcmgt.MakeFeatureLayer(in_file, dest_layer, where_clause = condition)

        count = arcmgt.GetCount(dest_layer)
        count = int (count.getOutput(0))
        if count == 0:
            raise NoFeatures("No features selected.  Possible coordinate system issues.\n" + condition)

        try:
            path_cost_rast = CostPath(dest_layer, path_dist_rast, backlink_rast)
            #path_dist_rast.save("xx_pr" + str (last_oid))
        except Exception as e:
            raise

        try:
            pcr_mask       = 1 - IsNull (path_cost_rast)
            #pcr_mask.save ("xx_pcr_mask" + str (last_oid))
            dist_masked    = path_dist_rast * pcr_mask
            path_array     = arcpy.RasterToNumPyArray(dist_masked, nodata_to_value = -9999)
            path_array_idx = numpy.where(path_array > 0)
            transit_array  = numpy.zeros_like(path_array)  #  past experience suggests we might need to use a different approach to guarantee we get zeroes
        except:
            raise

        path_sum = None

        if path_distance == 0:
            path_sum = 1 #  stayed in the same cell
            mask_array = arcpy.RasterToNumPyArray(pcr_mask, nodata_to_value = -9999)
            mask_array_idx = numpy.where(mask_array == 1)
            i = mask_array_idx[0][0]
            j = mask_array_idx[1][0]
            transit_array[i][j] = path_sum
        else:
            row_count = len (path_array) 
            col_count = len (path_array[0])
            arcpy.AddMessage ("processing %i cells of path raster" % (len(path_array_idx[0])))

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
                        if k == i and j == l:
                            continue  #  don't check self
                        checkval = checkrow[l]
                        #  negs are nodata, and this way we
                        #  don't need to care what that value is
                        if checkval >= 0:
                            diff = val - checkval
                            if diff > 0:
                                nbrs.append(diff)
                                #arcpy.AddMessage ("Check and diff vals are %s %s" % (checkval, diff))
                diff = min (nbrs)
                #arcpy.AddMessage ("Diff  val is %s" % diff)
                transit_array[i][j] = diff

            path_sum = path_array.max()  #  could use path_distance?
            #arcpy.AddMessage ("path_array.max is %s" % path_sum)

        #  Increment the cumulative transit array by the fraction of the
        #  transit time spent in each cell.
        #  Use path_sum because it corrects for cases where we stayed in the same cell.
        transit_array_accum = transit_array_accum + ((transit_array / path_sum) * transit_time)

        #xx = arcpy.NumPyArrayToRaster (transit_array, lower_left_coord, cellsize_used, cellsize_used, 0)
        #tmpname = "xx_t_arr_" + str (last_oid)
        #print "Saving to %s" % tmpname
        #xx.save (tmpname)


        try:
            arcmgt.Delete(backlink_rast)
            arcmgt.Delete(dest_layer)
        except Exception as e:
            arcpy.AddMessage (e)

        #  getting off-by-one errors when using the environment, so use this directly
        ext = path_cost_rast.extent
        lower_left_coord = ext.lowerLeft

        last_target = row_cur.getValue(target_fld)
        last_oid    = row_cur.getValue(oid_fd_name)

    #  need to use env settings to get it to be the correct size
    try:
        arcpy.AddMessage ("lower left is %s" % lower_left_coord)
        xx = arcpy.NumPyArrayToRaster (transit_array_accum, lower_left_coord, cellsize_used, cellsize_used, 0)
        print "Saving to %s" % out_raster
        xx.save (out_raster)
    except:
        raise


    print "Completed"

    return ()

if __name__ == "__main__":
    in_file    = arcpy.GetParameterAsText (0)
    cost_rast  = arcpy.GetParameterAsText (1)
    out_raster = arcpy.GetParameterAsText (2)
    t_diff_fld_name = arcpy.GetParameterAsText (3)
    workspace  = arcpy.GetParameterAsText (4)

    get_path_residence_times (
        in_file,
        cost_rast,
        out_raster,
        t_diff_fld_name,
        workspace
    )
    
    