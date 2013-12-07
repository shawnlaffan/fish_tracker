import arcpy
from arcpy.sa import *
import os, math, tempfile
from get_path_residence_times import get_path_residence_times

class Toolbox(object):
    def __init__(self):
        """Toolbox to run the FishTracker analysis system."""
        self.label = "Fish Tracker"
        self.alias = "FishTracker"

        # List of tool classes associated with this toolbox
        self.tools = [GetPathResidenceTimes]


descr = """
Toolbox to run the FishTracker analysis system.
"""

class GetPathResidenceTimes (object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "GetPathResidenceTimes"
        self.description = descr
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input Features parameter
        in_file = arcpy.Parameter(
            displayName   = "Input Feature Class",
            name          = "in_file",
            datatype      = "DEFeatureClass",
            parameterType = "Required",
            direction     = "Input",
            #description   = 'XXXXX'
            )
        in_file.filter.list = ["Point"]

        cost_rast = arcpy.Parameter(
            displayName   = "Cost Raster",
            name          = "cost_raster",
            datatype      = "DERasterDataset",
            parameterType = "Required",
            direction     = "Input"
        )

        # Derived Output raster parameter
        out_raster = arcpy.Parameter(
            displayName   = "Output Raster",
            name          = "out_raster",
            datatype      = "DERasterDataset",
            parameterType = "Required",
            direction     = "Output"
        )
        out_raster.parameterDependencies = [in_file.name]

        t_diff_fld_name = arcpy.Parameter(
            displayName   = "Time Difference Field Name",
            name          = "t_diff_fld_name",
            datatype      = "Field",
            parameterType = "Required",
            direction     = "Input"
        )
        t_diff_fld_name.value = "T_DIFF_HRS"
        t_diff_fld_name.parameterDependencies = [in_file.name]

        workspace = arcpy.Parameter(
            displayName   = "Workspace",
            name          = "workspace",
            datatype      = "DEWorkspace",
            parameterType = "Optional",
            direction     = "Input"
        )
        workspace.value = arcpy.env.workspace

        parameters = [
            in_file,
            cost_rast,
            out_raster,
            t_diff_fld_name,
            workspace
        ]

        return parameters

    #def GetParameterCount(self):
    #    #params = self.getParameterInfo
    #    return 5  #  need to iterate over the params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        arcpy.CheckOutExtension("Spatial")

        get_path_residence_times (
            parameters[0].valueAsText,
            parameters[1].valueAsText,
            parameters[2].valueAsText,
            parameters[3].valueAsText,
            parameters[4].valueAsText,
        )


if __name__ == "__main__":
    #get_path_residence_times ()
    print "exiting"
