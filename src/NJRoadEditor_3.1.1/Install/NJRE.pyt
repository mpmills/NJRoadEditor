#-------------------------------------------------------------------------------
# Name:         NJRE.pyt
# Purpose:      Python toolbox file.
#
# Author:       NJ Office of GIS
# Contact:      njgin@oit.nj.gov
#
# Created:      9/22/2014
# Copyright:    (c) NJ Office of GIS 2015
# Licence:      GPLv3

#-------------------------------------------------------------------------------

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  It can be found in the ~Install\GPLv3_License.txt
# If not, see <http://www.gnu.org/licenses/>.

#-------------------------------------------------------------------------------
import arcpy, pythonaddins
import pickle
import os
import sys
#import socket
os.sys.path.append(os.path.dirname(__file__))
import erebus
from fgdc_parser import fgdc_parser

# import the ParseNames toolbox
pn = arcpy.ImportToolbox(os.path.join(os.path.dirname(__file__), "ParseNames.pyt"))

merge_left_interp = False
merge_right_interp = False
merge_elevation = 99

split_left_interp = False
split_right_interp = False
split_elevation = 99
currentG = 99
bis_start_end = 'na'
addintmess = {}
lr_current = []
sld_current = []
segmentfc = ""; segmentchangetab = ""; transtab = ""; segnametab = ""; segshieldtab = ""; segcommtab = ""; linreftab = ""; sldtab = "";

USER = ''
njre_config_path = os.path.join(os.path.dirname(__file__), 'njre_config.p')  #['NJ OIT', 'NJ DOT', 'County', 'Other']
if os.path.exists(njre_config_path):
    with open(njre_config_path,'rb') as njreconfig:
        USER = pickle.load(njreconfig)

esriversion = arcpy.GetInstallInfo()['Version']
if esriversion.split('.')[1] == '2':
    pyexe = 'C:\Python27\ArcGIS10.2\python.exe'
if esriversion.split('.')[1] == '3':
    pyexe = 'C:\Python27\ArcGIS10.3\python.exe'


def set_tool_indicator(workspace, value):
    tool_indicator_path = os.path.join(workspace, 'tool_indicator.p')
    tool_indicator = value
    with open(tool_indicator_path, 'wb') as output:
        pickle.dump(tool_indicator, output, -1)

def getlongnames(workspace, names):
    #workspace_type = 'sde'
    workspace_type = arcpy.env.workspace.split(".")[-1]
    if workspace_type == 'sde':
        try:
            import re
            desc = arcpy.Describe(workspace)
            conn = desc.connectionProperties

            inst = conn.instance
            ss = re.search('sql',inst, re.I)
            ora = re.search('oracle',inst, re.I)
            longnames = {}
            if ss:
                gdb = conn.database
                fcs = arcpy.ListFeatureClasses('*')
                for fc in fcs:
                    if fc.split('.')[2] == 'SEGMENT_CHANGE':
                        owner = fc.split('.')[1]
                        break
                for name in names:
                    longnames[name] = gdb + "." + owner + "." + name
            elif ora:
                fcs = arcpy.ListFeatureClasses('*')
                for fc in fcs:
                    if fc.split('.')[1] == 'SEGMENT_CHANGE':
                        owner = fc.split('.')[0]
                        break
                for name in names:
                    longnames[name] = owner + "." + name

            return longnames
        except:
            return None
    if workspace_type == 'gdb':
        try:
            longnames = {}
            for name in names:
                longnames[name] = name
            return longnames
        except:
            return None


longnames = getlongnames(arcpy.env.workspace, ["SEGMENT", "SEGMENT_CHANGE", "SEGMENT_TRANS", "SEG_NAME", "SEG_SHIELD", "SEGMENT_COMMENTS", "LINEAR_REF", "SLD_ROUTE"])
try:
    segmentfc = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT"], "Layer")
    segmentchangetab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_CHANGE"], "Layer")
    transtab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_TRANS"], "Table")
    segnametab = erebus.getlongname(arcpy.env.workspace, longnames["SEG_NAME"], "Table")
    segshieldtab = erebus.getlongname(arcpy.env.workspace, longnames["SEG_SHIELD"], "Table")
    segcommtab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_COMMENTS"], "Table")
    linreftab = erebus.getlongname(arcpy.env.workspace, longnames["LINEAR_REF"], "Table")
    sldtab = erebus.getlongname(arcpy.env.workspace, longnames["SLD_ROUTE"], "Table")
except:
    pass


domains = arcpy.da.ListDomains(arcpy.env.workspace)
Domains = {}
roaddomains = [u'TRAVEL_DIR_TYPE', u'SURFACE_TYPE', u'SEGMENT_TYPE', u'CHANGE_TYPE', u'GNIS_NAME', u'SHIELD_SUBTYPE', u'ROUTE_TYPE', u'LRS_TYPE', u'JURIS_TYPE', u'SHIELD_TYPE', u'ACCESS_TYPE', u'DATA_SOURCE_TYPE', u'ELEV_TYPE', u'REVIEW_TYPE', u'SYMBOL_TYPE', u'NAME_TYPE', u'STATUS_TYPE']
for domain in domains:
    if domain.name in roaddomains:
        Domains[domain.name] = domain.codedValues


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "NJRE"
        self.alias = "njre"

        # List of tool classes associated with this toolbox
        self.tools = [Delete, NewSegment, Split, SplitSegment, Merge, MergeCleanup, BatchBuildName,LRS, BatchPost, EditNames]

class Delete(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Delete"
        self.description = "Delete a road feature and update the NJ Road Centerline Database."
        self.canRunInBackground = False

        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Create record in SEGMENT_CHANGE?
        param0 = arcpy.Parameter(
            displayName="Create record in SEGMENT_CHANGE?",
            name="create SEGMENT_CHANGE",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param0.value = True

        #
        param1 = arcpy.Parameter(
            displayName="Delete all existing records in SEGMENT_COMMENTS?",
            name="delete SEGMENT_COMMENTS",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param1.value = True

        #
        param2 = arcpy.Parameter(
            displayName="Create new record in SEGMENT_COMMENTS?",
            name="new_comment",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param2.value = False

        #
        param3 = arcpy.Parameter(
            displayName="COMMENTS",
            name="comments",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param3.enabled = False

        #
        param4 = arcpy.Parameter(
            displayName="RANK",
            name="rank",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param4.enabled = False

        params = [param0,param1,param2,param3,param4]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # if you are going to create a new SEGMENT_COMMENTS record, dont delete old ones
        if parameters[2].value == True:
            parameters[0].value = True
            parameters[0].enabled = False
            parameters[3].enabled = True
            parameters[4].enabled = True
        else:
            parameters[3].enabled = False
            parameters[4].enabled = False
            parameters[0].enabled = True
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        import traceback

        if parameters[2].value == True:
            if parameters[3].value:
                parameters[3].clearMessage()
            else:
                parameters[3].setErrorMessage("Please enter text for COMMENTS for the SEGMENT COMMENTS table.")
            if parameters[4].value:
                parameters[4].clearMessage()
            else:
                try:
                    with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            segguid = row[0]
                    seg_sql = erebus.sqlGUID("SEG_GUID", segguid)
                    ranklist = []
                    with arcpy.da.SearchCursor(segcommtab, ['RANK'],seg_sql) as cursor:
                        for row in cursor:
                            ranklist.append(row[0])
                    if ranklist:
                        ranklist = sorted(ranklist)
                        maxrank = max(ranklist)
                        parameters[4].setWarningMessage("Rank has been autopopulated to be the next integer in the sequence. Current RANK values for this segment are: {0}".format(ranklist))
                        parameters[4].value = int(maxrank) + 1
                except:
                    parameters[4].setErrorMessage(traceback.format_exc())

                if not parameters[4].value:
                    parameters[4].value = 1



        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        import arcpy
        import os
        import pickle
        import sys
        import traceback
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        set_tool_indicator(arcpy.env.scratchWorkspace, True)
        change_tf = parameters[0].valueAsText
        delcomm_tf = parameters[1].valueAsText
        newcomm_tf = parameters[2].valueAsText
        scomm = parameters[3].valueAsText
        srank = parameters[4].value
        delete_result = {'block1': False}

        # Set up the segment dictionary
        des_change = arcpy.Describe(segmentchangetab)
        des_change_fields = des_change.fields
        segchangefields = {}
        for field in des_change_fields:
            segchangefields[str(field.name)] = ''

        des_comm = arcpy.Describe(segcommtab)
        des_comm_fields = des_comm.fields
        commfields = {}
        for field in des_comm_fields:
            commfields[str(field.name)] = ''
        try:
            deletepath = arcpy.env.scratchWorkspace + "\\deleteselection.p"
            if os.path.exists(deletepath):
                with open(deletepath,'rb') as delopen:
                    delete_pickle = pickle.load(delopen)
            seg_sql = delete_pickle[1]
            segguid = delete_pickle[0]
        except:
            trace = traceback.format_exc()
            delete_result['trace'] = trace
            arcpy.AddMessage(trace)
            sys.exit('block 01')
            set_tool_indicator(arcpy.env.scratchWorkspace, False)

        ########################################################################
        ## Copy over to SEG_CHANGE
        if change_tf == "true":

            try:
                arcpy.SelectLayerByAttribute_management(segmentfc, 'NEW_SELECTION',seg_sql)
                # ACTUALLY COPY THE SEGMENT TO THE SEGMENT_CHANGE FC
                userwkspc = arcpy.env.workspace
                arcpy.env.workspace = "in_memory"  # Change the current workspace
                rdselcopy = arcpy.env.workspace + "\segmentcopy"
                arcpy.CopyFeatures_management(segmentfc, rdselcopy)
                fieldmappings = arcpy.FieldMappings()
                fieldmappings.addTable(segmentchangetab) # target fc

                guidind = fieldmappings.findFieldMapIndex("SEG_GUID_ARCH")
                fieldmap = fieldmappings.getFieldMap(guidind)
                fieldmap.addInputField(rdselcopy, "SEG_GUID")
                fieldmappings.replaceFieldMap(guidind,fieldmap)

                idind = fieldmappings.findFieldMapIndex("SEG_ID_ARCH")
                fieldmap2 = fieldmappings.getFieldMap(idind)
                fieldmap2.addInputField(rdselcopy, "SEG_ID")
                fieldmappings.replaceFieldMap(idind,fieldmap2)
                arcpy.Append_management(rdselcopy, segmentchangetab, "NO_TEST", fieldmappings, "")

                arcpy.AddMessage("Selected feature successfully copied and appended to SEGMENT_CHANGE")

                ################################################################
                ## Update the new row in SEGMENT_CHANGE with user input

                # Get the field attributes from the segment that you copied
                with arcpy.da.SearchCursor(rdselcopy, ["SEG_ID", "SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        copysegid = row[0]
                        copysegguid = row[1]

                # Get the GlobalID values for any SEGMENT_COMMENTS records. This will enable deleting/retaining the record in
                # SEGMENT_COMMENTS since the "simple" relationship class will remove the SEG_GUID upon SEGMENT delete.
                commSql = erebus.sqlGUID('SEG_GUID', copysegguid)
                commGlobals = []

                with arcpy.da.SearchCursor(segcommtab, ["GLOBALID"], commSql) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        commGlobals.append(row[0])

                arcpy.Delete_management("in_memory") # clean out the memory
                arcpy.env.workspace = userwkspc # reset the workspace to the user's workspace
                segArch_sql = erebus.sqlGUID("SEG_GUID_ARCH", segguid)
                cursor = arcpy.UpdateCursor(segmentchangetab, segArch_sql)
                for row in cursor:
                    row.setValue('CHANGE_TYPE_ID', 'R')
                    if newcomm_tf == 'true':
                        row.setValue('COMMENTS', 'Y')
                    cursor.updateRow(row)
                try: del row
                except: pass
                try: del cursor
                except: pass
                arcpy.AddMessage("CHANGE_TYPE_ID and COMMENTS updated in SEGMENT_CHANGE")
            except:
                trace = traceback.format_exc()
                delete_result['trace'] = trace
                arcpy.AddMessage(trace)
                set_tool_indicator(arcpy.env.scratchWorkspace, False)
                try: row; del row
                except: pass
                try: cursor; del cursor
                except: pass
                sys.exit('block 1')

        ########################################################################
        ## Delete Records
        try:

            # Do this before deleting the SEGMENT record, so that the SEG_GUIDs dont get wiped away.
            if delcomm_tf == "true":
                sci = False
                cursor = arcpy.UpdateCursor(segcommtab, seg_sql)
                for row in cursor:
                    cursor.deleteRow(row)
                    arcpy.AddMessage("Deleted record in SEGMENT_COMMENTS")
                    sci = True
                try: del row
                except: pass
                try: del cursor
                except: pass
                if not sci:
                    arcpy.AddMessage("No records in SEGMENT_COMMENTS with matching SEG_GUID")
            # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
            # SEGMENT DELETE
            cursor = arcpy.UpdateCursor(segmentfc, seg_sql)
            for row in cursor:
                cursor.deleteRow(row)
            try: del row
            except: pass
            try: del cursor
            except: pass
            arcpy.AddMessage("Deleted record in SEGMENT")

            # Operation 2: Delete row from SEG_NAME
            sn = False
            cursor = arcpy.UpdateCursor(segnametab, seg_sql)
            for row in cursor:
                cursor.deleteRow(row)
                arcpy.AddMessage("Deleted record in SEG_NAME")
                sn = True
            try: del row
            except: pass
            try: del cursor
            except: pass
            if not sn:
                arcpy.AddMessage("No records in SEG_NAME with matching SEG_GUID")

            # Operation 3: Delete row from LINEAR_REF
            lrs = False
            cursor = arcpy.UpdateCursor(linreftab, seg_sql)
            for row in cursor:
                cursor.deleteRow(row)
                arcpy.AddMessage("Deleted record in LINEAR_REF")
                lrs = True
            try: del row
            except: pass
            try: del cursor
            except: pass
            if not lrs:
                arcpy.AddMessage("No records in LINEAR_REF with matching SEG_GUID")

            # Operation 5: Delete row from SEG_SHIELD
            ssi = False
            cursor = arcpy.UpdateCursor(segshieldtab, seg_sql)
            for row in cursor:
                cursor.deleteRow(row)
                arcpy.AddMessage("Deleted record in SEG_SHIELD")
                ssi = True
            try: del row
            except: pass
            try: del cursor
            except: pass
            if not ssi:
                arcpy.AddMessage("No records in SEG_SHIELD with matching SEG_GUID")

        except:
            delete_result['trace'] = traceback.format_exc()
            arcpy.AddMessage(traceback.format_exc())
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            sys.exit('block 2')

        ########################################################################
        ## SEGMENT COMMENTS
        # Case 3: Copy the segment over to SEGMENT_CHANGE, and add a new row in COMMENTS, but dont delete old SEGMENT_COMMENTS
        # The record is going to seg_change, all records are not being deleted, and there are some exisitng records
        # in segment comments. Update the SEG_GUIDs to they dont become orphaned.
        if change_tf == 'true' and delcomm_tf == 'false' and len(commGlobals) > 0:
            for comRec in commGlobals:
                csql = erebus.sqlGUID('GLOBALID', comRec)
                cursor = arcpy.UpdateCursor(segcommtab, csql)
                for row in cursor:
                    row.setValue('SEG_GUID', copysegguid)
                    arcpy.AddMessage("Existing record in SEGMENT_COMMENTS retained for SEG_CHANGE record, global id: {0}".format(comRec))
                try: del row
                except: pass
                try: del cursor
                except: pass
        if newcomm_tf == "true":
            try:
                ## 4.1 Insert a row with the SEG_GUID
                cursor = arcpy.InsertCursor(segcommtab)
                row = cursor.newRow()
                row.setValue('SEG_GUID', segguid)
                row.setValue('COMMENTS', scomm)
                row.setValue('RANK', srank)
                cursor.insertRow(row)
                arcpy.AddMessage("New record inserted in SEGMENT_COMMENTS")
                arcpy.AddMessage("COMMENTS and RANK fields updated in SEGMENT_COMMENTS")
                try: del row
                except: pass
                try: del cursor
                except: pass
            except:
                delete_result['trace'] = traceback.format_exc()
                arcpy.AddMessage(traceback.format_exc())
                set_tool_indicator(arcpy.env.scratchWorkspace, False)
                try: row; del row
                except: pass
                try: cursor; del cursor
                except: pass
        arcpy.RefreshActiveView()
        set_tool_indicator(arcpy.env.scratchWorkspace, False)
        return

# END Delete
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||

class NewSegment(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "NewSegment"
        self.description = "Creates a new segment in the NJ Road Centerlines Database"
        self.canRunInBackground = True

        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
        global USER, Domains

    def getParameterInfo(self):
        """Define parameter definitions"""
        #-----------------------------------------------------------------------

        # SEGMENT category
        param0 = arcpy.Parameter(
            displayName="SEG_ID",
            name="SEG_ID",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param0.enabled = False

        #
        param1 = arcpy.Parameter(
            displayName="Create Entry in SEG_NAME and SEGMENT.PRIME_NAME",
            name="Create Entry in SEG_NAME",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        #param1.value = False

        #
        param2 = arcpy.Parameter(
            displayName="ADDR_L_FR",
            name="ADDR_L_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param3 = arcpy.Parameter(
            displayName="ADDR_L_TO",
            name="ADDR_L_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param4 = arcpy.Parameter(
            displayName="ADDR_R_FR",
            name="ADDR_R_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param5 = arcpy.Parameter(
            displayName="ADDR_R_TO",
            name="ADDR_R_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param6 = arcpy.Parameter(
            displayName="ZIPCODE_L",
            name="ZIPCODE_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param7 = arcpy.Parameter(
            displayName="ZIPCODE_R",
            name="ZIPCODE_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param8 = arcpy.Parameter(
            displayName="ZIPNAME_L",
            name="ZIPNAME_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param9 = arcpy.Parameter(
            displayName="ZIPNAME_R",
            name="ZIPNAME_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        gnis = Domains['GNIS_NAME'].values()
        gnis2 = sorted(gnis, key = lambda item: item.split(',')[1] + item.split(',')[0])
        #
        param10 = arcpy.Parameter(
            displayName="MUNI_ID_L",
            name="MUNI_ID_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param10.filter.type = "ValueList"
        param10.filter.list = gnis2

        #
        param11 = arcpy.Parameter(
            displayName="MUNI_ID_R",
            name="MUNI_ID_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param11.filter.type = "ValueList"
        param11.filter.list = gnis2

        #
        param12 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_FR",
            name="ELEV_TYPE_ID_FR",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param12.filter.type = "ValueList"
        param12.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        param12.value = "At Grade"

        #
        param13 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_TO",
            name="ELEV_TYPE_ID_TO",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param13.filter.type = "ValueList"
        param13.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        param13.value = "At Grade"

        #
        param14 = arcpy.Parameter(
            displayName="ACC_TYPE_ID",
            name="ACC_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param14.filter.type = "ValueList"
        param14.filter.list = ["Non-Restricted", "Restricted", "Unknown"]
        param14.value = "Non-Restricted"

        #
        param15 = arcpy.Parameter(
            displayName="SURF_TYPE_ID",
            name="SURF_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param15.filter.type = "ValueList"
        param15.filter.list = ["Improved", "Unimproved", "Unknown"]
        param15.value = "Improved"

        #
        param16 = arcpy.Parameter(
            displayName="STATUS_TYPE_ID",
            name="STATUS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param16.filter.type = "ValueList"
        param16.filter.list = ["Active", "Planned", "Under Construction"]
        param16.value = "Active"

        #
        param17 = arcpy.Parameter(
            displayName="SYMBOL_TYPE_ID",
            name="SYMBOL_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param17.filter.type = "ValueList"
        param17.filter.list = ["Highway Authority Route", "Highway Authority Ramp", "Interstate", "Insterstate Ramp", "US Highway", "US Highway Ramp", "State Highway", "State Highway Ramp", "County 500 Route", "County 500 Ramp", "Other County Route", "Other County Ramp", "Local Road", "Local Ramp", "Alley"]
        #param17.value = "Local Road"

        #
        param18 = arcpy.Parameter(
            displayName="TRAVEL_DIR_TYPE_ID",
            name="TRAVEL_DIR_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param18.filter.type = "ValueList"
        param18.filter.list = ["Both", "Decreasing", "Increasing"]
        param18.value = "Both"

        #
        param19 = arcpy.Parameter(
            displayName="JURIS_TYPE_ID",
            name="JURIS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param19.filter.type = "ValueList"
        param19.filter.list = ["Public", "Private", "Unknown"] #["Public", "Private", "Private (with linear referencing)", "Unknown"]
        param19.value = "Public"

        #
        param20 = arcpy.Parameter(
            displayName="OIT_REV_TYPE_ID",
            name="OIT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param20.filter.type = "ValueList"
        param20.filter.list = ["Draft", "Final", "Incoming"]

        #
        param21 = arcpy.Parameter(
            displayName="DOT_REV_TYPE_ID",
            name="DOT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param21.filter.type = "ValueList"
        param21.filter.list = ["Draft", "Final", "Incoming"]

        #-----------------------------------------------------------------------
        # SEG_NAME category

        #
        param22 = arcpy.Parameter(
            displayName="NAME_TYPE_ID",
            name="NAME_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param22.filter.type = "ValueList"
        param22.filter.list = ["Local Name", "Highway Name"]
        param22.value = "Local Name"

        #
        param23 = arcpy.Parameter(
            displayName="RANK",
            name="RANK (SEG_NAME)",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param23.value = 1


        #
        param24 = arcpy.Parameter(
            displayName="NAME_FULL",
            name="NAME_FULL",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param24.enabled = False

        #
        param25 = arcpy.Parameter(
            displayName="PRE_DIR",
            name="PRE_DIR",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param26 = arcpy.Parameter(
            displayName="PRE_TYPE",
            name="PRE_TYPE",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param27 = arcpy.Parameter(
            displayName="PRE_MOD",
            name="PRE_MOD",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param28 = arcpy.Parameter(
            displayName="NAME",
            name="NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param29 = arcpy.Parameter(
            displayName="SUF_TYPE",
            name="SUF_TYPE",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param30 = arcpy.Parameter(
            displayName="SUF_DIR",
            name="SUF_DIR",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param31 = arcpy.Parameter(
            displayName="SUF_MOD",
            name="SUF_MOD",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param32 = arcpy.Parameter(
            displayName="DATA_SRC_TYPE_ID",
            name="DATA_SRC_TYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param32.filter.type = "ValueList"
        param32.filter.list = ["NJDOT SLD", "Tiger", "County", "MOD IV", "Other", "NJOIT", "Taxmap"]

        param22.category = "SEG_NAME"
        param23.category = "SEG_NAME"
        param24.category = "SEG_NAME"
        param25.category = "SEG_NAME"
        param26.category = "SEG_NAME"
        param27.category = "SEG_NAME"
        param28.category = "SEG_NAME"
        param29.category = "SEG_NAME"
        param30.category = "SEG_NAME"
        param31.category = "SEG_NAME"
        param32.category = "SEG_NAME"

        #-----------------------------------------------------------------------
        # SEG_SHIELD category

        #
        param33 = arcpy.Parameter(
            displayName="RANK (same as SEG_NAME rank)",
            name="RANK (SEG_SHIELD)",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param34 = arcpy.Parameter(
            displayName="SHIELD_TYPE_ID (highway route shield)",
            name="SHIELD_TYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param34.filter.type = "ValueList"
        param34.filter.list = ["Atlantic City Expressway", "Atlantic City Brigantine Connector", "County Route", "Garden State Parkway", "Interstate", "Palisades Interstate Parkway", "State Route","NJ Turnpike","US Route"]

        #
        param35 = arcpy.Parameter(
            displayName="SHIELD_SUBTYPE_ID (highway route shield modifier)",
            name="SHIELD_SUBTYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param35.filter.type = "ValueList"
        param35.filter.list = ["Alternate Route", "Business Route", "Connector Route", "Express Route", "Main Route", "Spur Route", "Truck Route", "Bypass Route"]

        #
        param36 = arcpy.Parameter(
            displayName="SHIELD_NAME (highway route number)",
            name="SHIELD_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param37 = arcpy.Parameter(
            displayName="DATA_SRC_TYPE_ID (same as SEG_NAME DATA_SRC_TYPE_ID)",
            name="DATA_SRC_TYPE_ID (SEG_SHIELD)",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param37.filter.type = "ValueList"
        param37.filter.list = ["NJDOT SLD", "Tiger", "County", "MOD IV", "Other", "NJOIT", "TAXMAP"]

        param33.category = "SEG_SHIELD"
        param34.category = "SEG_SHIELD"
        param35.category = "SEG_SHIELD"
        param36.category = "SEG_SHIELD"
        param37.category = "SEG_SHIELD"

        #-----------------------------------------------------------------------
        # LINEAR_REF category

        #
        param38 = arcpy.Parameter(
            displayName="SRI",
            name="SRI",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param39 = arcpy.Parameter(
            displayName="LRS_TYPE_ID",
            name="LRS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param39.filter.type = "ValueList"
        param39.filter.list = ["NJDOT Multi-Centerline", "NJDOT Parent", "NJDOT Flipped", "MMS Milepost Markers", "NJTA"]
        param39.value = "NJDOT Multi-Centerline"

        #
        param40 = arcpy.Parameter(
            displayName="SEG_TYPE_ID",
            name="SEG_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param40.filter.type = "ValueList"
        param40.filter.list = ["Primary", "Secondary", "Express", "Express Secondary", "Acceleration/Deceleration"]
        param40.value = "Primary"

        #
        param41 = arcpy.Parameter(
            displayName="MILEPOST_FR",
            name="MILEPOST_FR",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        #param41.value = 1

        #
        param42 = arcpy.Parameter(
            displayName="MILEPOST_TO",
            name="MILEPOST_TO",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        #param42.value = 9999

        #
        param43 = arcpy.Parameter(
            displayName="RCF",
            name="RCF",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        param38.category = "LINEAR_REF"
        param39.category = "LINEAR_REF"
        param40.category = "LINEAR_REF"
        param41.category = "LINEAR_REF"
        param42.category = "LINEAR_REF"
        param43.category = "LINEAR_REF"

        #-----------------------------------------------------------------------
        # SLD_ROUTE category

        #
        param44 = arcpy.Parameter(
            displayName="SRI (SLD)",
            name="SRI (SLD)",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param45 = arcpy.Parameter(
            displayName="ROUTE_TYPE_ID",
            name="ROUTE_TYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param45.filter.type = "ValueList"
        param45.filter.list = ["Interstate", "US Highway", "State Highway", "Highway Authority Route", "500 Series Route", "Other County Route", "Local Road", "Ramp", "Alley", "Park / Military"]

        #
        param46 = arcpy.Parameter(
            displayName="SLD_NAME",
            name="SLD_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param47 = arcpy.Parameter(
            displayName="SLD_COMMENT",
            name="SLD_COMMENT",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param48 = arcpy.Parameter(
            displayName="SLD_DIRECTION",
            name="SLD_DIRECTION",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param48.filter.type = "ValueList"
        param48.filter.list = ["North to South", "South to North", "East to West", "West to East"]

        #
        param49 = arcpy.Parameter(
            displayName="SIGN_NAME",
            name="SIGN_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param49.category = ""

        param44.category = "SLD_ROUTE"
        param45.category = "SLD_ROUTE"
        param46.category = "SLD_ROUTE"
        param47.category = "SLD_ROUTE"
        param48.category = "SLD_ROUTE"
        param49.category = "SLD_ROUTE"


        # Wrap up the variables into a nice little box

        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10,param11,param12,param13,param14,param15,param16,param17,param18,param19,param20,param21,param22,param23,param24,param25,param26,param27,param28,param29,param30,param31,param32,param33,param34,param35,param36,param37,param38,param39,param40,param41,param42,param43,param44,param45,param46,param47,param48,param49]


        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        import arcpy
        os.sys.path.append(os.path.dirname(__file__))
        import erebus
        global USER
        # If the SEG_NAME checkbox is selected, turn on the  SEG_NAME category.
        if parameters[1].value == True:
            parameters[22].enabled = True
            parameters[23].enabled = False
            parameters[25].enabled = True
            parameters[26].enabled = True
            parameters[27].enabled = True
            parameters[28].enabled = True
            parameters[29].enabled = True
            parameters[30].enabled = True
            parameters[31].enabled = True
            parameters[32].enabled = True
        else:
            parameters[2].enabled = False
            parameters[3].enabled = False
            parameters[4].enabled = False
            parameters[5].enabled = False
            parameters[2].value = None
            parameters[3].value = None
            parameters[4].value = None
            parameters[5].value = None
            parameters[22].enabled = False
            parameters[23].enabled = False
            parameters[25].enabled = False
            parameters[26].enabled = False
            parameters[27].enabled = False
            parameters[28].enabled = False
            parameters[29].enabled = False
            parameters[30].enabled = False
            parameters[31].enabled = False
            parameters[32].enabled = False


        # -----------------------------------------------------------
        # SEGMENT.ADDR - if it is a ramp, then don't allow addresses
        # SEG_NAME - if it is a ramp, then no segname record will be allowed

        if parameters[17].value in ("Highway Authority Ramp", "Insterstate Ramp", "US Highway Ramp", "State Highway Ramp", "County 500 Ramp"):
            parameters[2].value = None
            parameters[3].value = None
            parameters[4].value = None
            parameters[5].value = None
            parameters[2].enabled = False
            parameters[3].enabled = False
            parameters[4].enabled = False
            parameters[5].enabled = False

            parameters[1].value = False
            parameters[1].enabled = False
            parameters[22].enabled = False
            parameters[23].enabled = False
            parameters[25].enabled = False
            parameters[26].enabled = False
            parameters[27].enabled = False
            parameters[28].enabled = False
            parameters[29].enabled = False
            parameters[30].enabled = False
            parameters[31].enabled = False
            parameters[32].enabled = False
        else:
            parameters[1].enabled = True
            if parameters[1].value == True:
                parameters[2].enabled = True
                parameters[3].enabled = True
                parameters[4].enabled = True
                parameters[5].enabled = True
            else:
                parameters[2].enabled = False
                parameters[3].enabled = False
                parameters[4].enabled = False
                parameters[5].enabled = False
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None


        if parameters[28].value:
        # BUILD THE NAME
            fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
            parameters[24].value = fnn.concatenate()
        else:
            parameters[24].value = None

##        # If JURIS_TYPE is Private or Unknown, leave the LIN_REF alone. Otherwise, enable it.
##        if parameters[19].value == "Private" or parameters[19].value == "Unknown":
##    	    parameters[38].enabled = False
##    	    parameters[39].enabled = False
##    	    parameters[40].enabled = False
##    	    parameters[41].enabled = False
##    	    parameters[42].enabled = False
##    	    parameters[43].enabled = False
##        else:
##    	    parameters[38].enabled = True
##    	    parameters[39].enabled = True
##    	    parameters[40].enabled = True
##    	    parameters[41].enabled = True
##    	    parameters[42].enabled = True
##    	    parameters[43].enabled = True



        if not parameters[20].altered:
            if USER in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                usedict = {'NJ OIT': 'Final', 'NJ DOT': 'Draft', 'County': 'Incoming', 'Other': 'Draft'}
                parameters[20].value = usedict[USER]
            else:
                parameters[20].value = 'Draft'
        if not parameters[21].altered:
            if USER in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                usedict = {'NJ OIT': 'Draft', 'NJ DOT': 'Final', 'County': 'Draft', 'Other': 'Draft'}
                parameters[21].value = usedict[USER]
            else:
                parameters[21].value = 'Draft'

        # check that NAME_TYPE_ID (seg name) parameter has a value, Enable the SEG_SHIELD Category
        if parameters[22].value:
            if parameters[22].value == "Highway Name":
                parameters[34].enabled = True
                parameters[35].enabled = True
                parameters[36].enabled = True
            else:
                parameters[33].enabled = False
                parameters[34].enabled = False
                parameters[35].enabled = False
                parameters[36].enabled = False
                parameters[37].enabled = False

        # if SEG_NAME "RANK" is populated, pass it to SEG_SHIELD "RANK"
        if parameters[23].value:
            parameters[33].value = parameters[23].value

        # if SEG_NAME "DATA_SRC_TYPE_ID" is populated, pass it to SEG_SHIELD "DATA_SRC_TYPE_ID"
        if parameters[32].value:
            parameters[37].value = parameters[32].value

        # If the SEG_NAME box is checked, and 22 is "HIghway", set up the rules from ADDNAME to populate names based on SHIELD TYPE ID
        if parameters[1].value == True and parameters[22].value == "Highway Name":
            emptyval = None
            if parameters[34].value == "Atlantic City Expressway":
                parameters[25].value = emptyval;parameters[26].value = emptyval;parameters[27].value = emptyval;parameters[28].value = emptyval;parameters[29].value = emptyval;parameters[30].value = emptyval;parameters[31].value = emptyval;
                parameters[28].value = "Atlantic City"
                parameters[29].value = "Expressway"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()
            if parameters[34].value == "Atlantic City Brigantine Connector":
                parameters[25].value = emptyval;parameters[26].value = emptyval;parameters[27].value = emptyval;parameters[28].value = emptyval;parameters[29].value = emptyval;parameters[30].value = emptyval;parameters[31].value = emptyval;
                parameters[28].value = "Atlantic City Brigantine"
                parameters[31].value = "Connector"
                parameters[35].value = "Connector Route"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "County Route":
                parameters[26].value = "County Route"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "Garden State Parkway":
                parameters[25].value = emptyval;parameters[26].value = emptyval;parameters[27].value = emptyval;parameters[28].value = emptyval;parameters[29].value = emptyval;parameters[30].value = emptyval;parameters[31].value = emptyval;
                parameters[28].value = "Garden State"
                parameters[29].value = "Parkway"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "Interstate":
                parameters[26].value = "Interstate"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "Palisades Interstate Parkway":
                parameters[25].value = emptyval;parameters[26].value = emptyval;parameters[27].value = emptyval;parameters[28].value = emptyval;parameters[29].value = emptyval;parameters[30].value = emptyval;parameters[31].value = emptyval;
                parameters[28].value = "Palisades Interstate"
                parameters[29].value = "Parkway"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "State Highway":
                parameters[26].value = "State Highway"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "New Jersey Turnpike":
                parameters[25].value = emptyval;parameters[26].value = emptyval;parameters[27].value = emptyval;parameters[28].value = emptyval;parameters[29].value = emptyval;parameters[30].value = emptyval;parameters[31].value = emptyval;                parameters[9].value = "New Jersey"
                parameters[28].value = "New Jersey"
                parameters[29].value = "Turnpike"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            if parameters[34].value == "US Highway":
                parameters[26].value = "US Highway"
                fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                parameters[24].value = fnn.concatenate()

            # Use SHIELD_SUBTYPE_ID to populate name fields
            if parameters[35].value:
                if parameters[35].value != "Main Route":
                    substring = parameters[35].value
                    substring2 = substring.split()
                    parameters[31].value = substring2[0]
                    fnn = erebus.FullName(parameters[25].value, parameters[26].value, parameters[27].value, parameters[28].value, parameters[29].value, parameters[30].value, parameters[31].value)
                    parameters[24].value = fnn.concatenate()


        # If the user enters an SRI, turn the SRI fields on.
        if parameters[44].value:
            parameters[45].enabled = True
            parameters[46].enabled = True
            parameters[47].enabled = True
            parameters[48].enabled = True
            parameters[49].enabled = True
        else:
            parameters[45].enabled = False
            parameters[46].enabled = False
            parameters[47].enabled = False
            parameters[48].enabled = False
            parameters[49].enabled = False



        # If SEG_TYPE_ID is AD, then ROUTE_TYPE_ID must be 8 for a ramp.
        if parameters[40].value == "AD - Acceleration/Deceleration":
            parameters[45].value = "Ramp"


        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        import re

##        domains = arcpy.da.ListDomains(arcpy.env.workspace)
##        Domains = {}
##        for domain in domains:
##            Domains[domain.name] = domain.codedValues

        #-----------------------------------------------------------------------
        # SEGMENT.ZIPCODE Validation

        if parameters[6].value and len(parameters[6].value) == 5:
            parameters[6].clearMessage()
        elif parameters[6].value:
            parameters[6].setErrorMessage("ZIPCODE should not be more (or less) than 5 characters")
        if parameters[7].value and len(parameters[7].value) == 5:
            parameters[7].clearMessage()
        elif parameters[7].value:
            parameters[7].setErrorMessage("ZIPCODE should not be more (or less) than 5 characters")

        #-----------------------------------------------------------------------
        # TRAVEL_DIR_TYPE Validation.
        # If it is a ramp, dir cant be 'both'

        if parameters[17].value in ("Highway Authority Ramp", "Insterstate Ramp", "US Highway Ramp", "State Highway Ramp", "County 500 Ramp", "Other County Ramp", "Local Ramp"):
            parameters[1].value = False
            if parameters[18].value == 'Both':
                parameters[18].setErrorMessage("If SYMBOL_TYPE is a ramp, TRAVEL_DIR cannot be 'Both'.")
            else:
                parameters[18].clearMessage()

        #-----------------------------------------------------------------------
        # If SEG_SHIELD Validation. If "Highway" make parameters required.
        if parameters[22].value == "Highway Name":
            if parameters[33].value not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
                parameters[33].setErrorMessage("RANK (SEG_SHIELD) cannot be empty, please enter an integer")
            else:
                parameters[33].clearMessage()
            if parameters[34].value not in ("Atlantic City Expressway", "Atlantic City Brigantine Connector", "County Route", "Garden State Parkway", "Interstate", "Palisades Interstate Parkway", "State Route","NJ Turnpike","US Route"):
                parameters[34].setErrorMessage("SHIELD_TYPE_ID cannot be empty, please choose from the drop down")
            elif parameters[34].value in ("Atlantic City Expressway", "Atlantic City Brigantine Connector", "Garden State Parkway", "Palisades Interstate Parkway", "New Jersey Turnpike"):
                 parameters[36].clearMessage()
            else:
                parameters[34].clearMessage()
            if parameters[35].value not in ("Alternate Route", "Business Route", "Connector Route", "Express Route", "Main Route", "Spur Route", "Truck Route", "Bypass Route"):
                parameters[35].setErrorMessage("SHIELD_SUBTYPE_ID cannot be empty, please choose from the drop down")
            else:
                parameters[35].clearMessage()

            if parameters[34].value in ("Atlantic City Expressway", "Atlantic City Brigantine Connector", "Garden State Parkway", "Palisades Interstate Parkway", "NJ Turnpike"):
                parameters[36].clearMessage()
            elif parameters[36].value and parameters[34].value in ("County Route", "Interstate", "State Route", "US Route"):
                shname = parameters[36].valueAsText
                # check to see if shield name is numeric, unless it begins with 'C' or 'S' or '9W' or '606A'
                if parameters[36].value == '9W' or parameters[36].value == '606A' or shname[0].upper() == 'C' or shname[0].upper() == 'S':
                    parameters[36].clearMessage()
                else:
                    try:
                        int(parameters[36].value)
                        if len(parameters[36].value) > 5:
                            parameters[36].setErrorMessage("SHIELD_NAME must be no more than 5 digits long.")
                    except ValueError:
                        parameters[36].setErrorMessage("SHIELD_NAME must be numeric. Exceptions are; 'C' and 'S' for Bergen County, '9W', '606A', and Highway Authority Routes.")
            else:
                parameters[36].setErrorMessage("SHIELD_NAME cannot be empty, please enter a name (text).")
            if parameters[37].value not in ("NJDOT", "Tiger", "County", "MOD IV", "Other", "NJOIT", "Taxmap"):
                parameters[37].setErrorMessage("DATA_SRC_TYPE_ID cannot be empty, please choose from the drop down")
            else:
                parameters[37].clearMessage()

        #-----------------------------------------------------------------------
        # SEG_NAME Validation. If the category is enabled, requires: NAME_TYPE_ID, RANK, NAME_FULL, NAME, DATA_SRC_TYPE_ID

        if parameters[1].value:
            if parameters[25].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[25].value):
                    parameters[25].clearMessage()
                else:
                    parameters[25].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[25].clearMessage()
            if parameters[26].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[26].value):
                    parameters[26].clearMessage()
                else:
                    parameters[26].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[26].clearMessage()
            if parameters[27].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[27].value):
                    parameters[27].clearMessage()
                else:
                    parameters[27].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[27].clearMessage()
            if parameters[28].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[28].value):
                    parameters[28].clearMessage()
                else:
                    parameters[27].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[28].setErrorMessage("NAME cannot be empty, please enter a name (text).")
            if parameters[29].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[29].value):
                    parameters[29].clearMessage()
                else:
                    parameters[29].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[29].clearMessage()
            if parameters[30].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[30].value):
                    parameters[30].clearMessage()
                else:
                    parameters[30].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[30].clearMessage()
            if parameters[31].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[31].value):
                    parameters[31].clearMessage()
                else:
                    parameters[31].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[31].clearMessage()
            if parameters[32].value:
                parameters[32].clearMessage()
            else:
                parameters[32].setErrorMessage("DATA_SRC_TYPE_ID cannot be empty, please enter a name (text).")

        #-----------------------------------------------------------------------
        # LINEAR_REF Validation. If the category is enabled, requires: MILEPOST_FR, MILEPOST_TO
        # 1. SRI formatting.
        lre = False
        lrerror = {1: 'If SYMBOL_TYPE is a ramp, then SRI must be 17 characters long.', 2: 'SRI must not contain spaces', 3: 'SRI must be 10 characters long.', 4: 'SRI should have "__" in position 9 and 10'}
        if parameters[38].value and parameters[17].value:
            ss = re.search(' ',parameters[38].value)
            sri1 = parameters[38].value
            if parameters[17].value in ("Highway Authority Ramp", "Insterstate Ramp", "US Highway Ramp", "State Highway Ramp", "County 500 Ramp", "Other County Ramp", "Local Ramp") and len(parameters[38].value) != 17:
                lre = 1
            elif parameters[17].value not in ("Highway Authority Ramp", "Insterstate Ramp", "US Highway Ramp", "State Highway Ramp", "County 500 Ramp", "Other County Ramp", "Local Ramp") and len(parameters[38].value) != 10:
                lre = 3
            elif ss:
                lre = 2
            elif parameters[39].value == '2 - NJDOT Parent':
                if len(parameters[38].value) == 10:
                    if sri1[8] != '_':
                        lre = 4
                    if sri1[9] != '_':
                        lre = 4
            if lre:
                parameters[38].setErrorMessage(lrerror[lre])
            if not lre:
                parameters[38].clearMessage()

        if parameters[39].value == 'NJDOT Multi-Centerline' and (parameters[41].value or parameters[41].value == 0) and (parameters[42].value or parameters[42].value == 0):
            if parameters[41].value > parameters[42].value:
                parameters[41].setErrorMessage('If LRS_TYPE is NJDOT Multi-Centerline, MP_FROM must be less than MP_TO')
                parameters[42].setErrorMessage('If LRS_TYPE is NJDOT Multi-Centerline, MP_FROM must be less than MP_TO')
            elif parameters[41].value == parameters[42].value:
                parameters[41].setWarningMessage('Milepost values are equal. This is acceptable, but rare.')
                parameters[42].setWarningMessage('Milepost values are equal. This is acceptable, but rare.')
        # MP can only be negative when seg_type is AD.
        elif parameters[40].value in ("Primary", "Secondary", "Express", "Express Secondary") and parameters[41].value:
            if parameters[41].value < 0:
      		    parameters[41].setErrorMessage('Negative MP values are only allowed when SEG_TYPE is "AD"')
        elif parameters[40].value in ("Primary", "Secondary", "Express", "Express Secondary") and parameters[42].value:
            if parameters[42].value < 0:
        		parameters[42].setErrorMessage('Negative MP values are only allowed when SEG_TYPE is "AD".')

        #-----------------------------------------------------------------------
        # SLD_ROUTE Validation
        if parameters[44].value:  # if there is an SRI
            if parameters[45].value:

                for key,value in Domains['ROUTE_TYPE'].iteritems():
                    if value == parameters[45].value:
                        rti2 = key
            if parameters[38].value:
                if parameters[44].value != parameters[38].value:
                    parameters[44].setWarningMessage('SRI value does not match the LINEAR_REF SRI value')
            else:
                parameters[44].clearMessage()
            if not parameters[45].value:
                parameters[45].setErrorMessage('Please choose a ROUTE_TYPE_ID')
            else:
                parameters[45].clearMessage()

                if rti2 <= 7 and parameters[48].value not in ("North to South", "South to North", "East to West", "West to East"):
                    if parameters[19].value == 'Public':
                        parameters[48].setErrorMessage('Please choose an SLD_DIRECTION')
                    elif rti2 == 7 and parameters[19].value == 'Public':
                        parameters[48].clearMessage()
                elif rti2 > 7:
                    parameters[48].value = ''
                    parameters[48].clearMessage()


        return

    def execute(self, parameters, messages):
        """The source code of the NewSegment tool."""
        import os
        import traceback
        os.sys.path.append(os.path.dirname(__file__))
        import arcpy
        import erebus
        import pickle

        set_tool_indicator(arcpy.env.scratchWorkspace, True)

        # Construct the DOMAIN Dictionaries
        domains = arcpy.da.ListDomains(arcpy.env.workspace)
        Domains = {}
        for domain in domains:
            Domains[domain.name] = domain.codedValues    #SYMBOL_TYPE JURIS_TYPE ELEV_TYPE CHANGE_TYPE REVIEW_TYPE STATUS_TYPE TRAVEL_DIR_TYPE DATA_SOURCE_TYPE SHIELD_TYPE ACCESS_TYPE SHIELD_SUBTYPE SEGMENT_TYPE NAME_TYPE SURFACE_TYPE GNIS_NAME LRS_TYPE

        newsegmentpath = arcpy.env.scratchWorkspace + "\\newsegmentselection.p"
        if os.path.exists(newsegmentpath):
            with open(newsegmentpath,'rb') as newsegmentopen:
                lastselect, segmentgeo = pickle.load(newsegmentopen)

        ################################################################################

        # Set up the segment dictionary
        des_seg = arcpy.Describe(segmentfc)
        des_seg_fields = des_seg.fields
        segfields = {}
        for field in des_seg_fields:
            segfields[str(field.name)] = ''

        seg_id_switch = "OFF"

        # Set up the seg_name dictionary
        des_sname = arcpy.Describe(segnametab)
        sname_fields = des_sname.fields
        seg_name = {}
        for field in sname_fields:
            seg_name[str(field.name)] = ''

        # Set up the seg_shield dictionary
        des_shame  = arcpy.Describe(segshieldtab)
        des_shame_fields = des_shame.fields
        seg_shield = {}
        for field in des_shame_fields:
            seg_shield[(field.name)] = ''

        # Set up the seg_shield dictionary
        des_linreftab = arcpy.Describe(linreftab)
        linreftab_fields = des_linreftab.fields
        lin_ref = {}
        for field in linreftab_fields:
            lin_ref[(field.name)] = ''

        # Set up the seg_shield dictionary
        des_sldtab = arcpy.Describe(sldtab)
        sldtab_fields = des_sldtab.fields
        sld_route = {}
        for field in sldtab_fields:
            sld_route[(field.name)] = ''

        ################################################################################
        ## ROAD.SEGMENT Parameters

        segfields['SEG_ID'] = parameters[0].valueAsText  # long integer
        #segfields['PRIME_NAME'] = parameters[1].valueAsText # text
        segfields['ADDR_L_FR'] = parameters[2].valueAsText # long integer
        segfields['ADDR_L_TO'] = parameters[3].valueAsText # long integer
        segfields['ADDR_R_FR'] = parameters[4].valueAsText # long integer
        segfields['ADDR_R_TO'] = parameters[5].valueAsText  # long integer
        segfields['ZIPCODE_L'] = parameters[6].valueAsText # text
        segfields['ZIPCODE_R'] = parameters[7].valueAsText # text
        segfields['ZIPNAME_L'] = parameters[8].valueAsText # text
        segfields['ZIPNAME_R'] = parameters[9].valueAsText # text

        if parameters[10].value:
            for key,value in Domains['GNIS_NAME'].iteritems():
                if value == parameters[10].value:
                    segfields['MUNI_ID_L'] = key
        if parameters[11].value:
            for key,value in Domains['GNIS_NAME'].iteritems():
                if value == parameters[11].value:
                    segfields['MUNI_ID_R'] = key

        if parameters[12].valueAsText == 'At Grade': # input is string, long integer
            segfields['ELEV_TYPE_ID_FR'] = 0
        elif parameters[12].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_FR'] = 1
        elif parameters[12].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_FR'] = 2
        elif parameters[12].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_FR'] = 3
        else:
            pass

        if parameters[13].valueAsText == 'At Grade': # input is string, long integer
            segfields['ELEV_TYPE_ID_TO'] = 0
        elif parameters[13].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_TO'] = 1
        elif parameters[13].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_TO'] = 2
        elif parameters[13].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_TO'] = 3
        else:
            pass

        if parameters[14].valueAsText == 'Non-Restricted': #text
            segfields['ACC_TYPE_ID'] = 'N'
        elif parameters[14].valueAsText == 'Restricted':
            segfields['ACC_TYPE_ID'] = 'R'
        elif parameters[14].valueAsText == 'Unknown':
            segfields['ACC_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[15].valueAsText == 'Improved': #text
            segfields['SURF_TYPE_ID'] = 'I'
        elif parameters[15].valueAsText == 'Unimproved':
            segfields['SURF_TYPE_ID'] = 'U'
        elif parameters[15].valueAsText == 'Unknown':
            segfields['SURF_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[16].valueAsText == 'Active': #text
            segfields['STATUS_TYPE_ID'] = 'A'
        elif parameters[16].valueAsText == 'Planned':
            segfields['STATUS_TYPE_ID'] = 'P'
        elif parameters[16].valueAsText == 'Under Construction':
            segfields['STATUS_TYPE_ID'] = 'U'
        else:
            pass

        if parameters[17].valueAsText == 'Highway Authority Route': # input is string, short integer
            segfields['SYMBOL_TYPE_ID'] = 100
        elif parameters[17].valueAsText == 'Highway Authority Ramp':
            segfields['SYMBOL_TYPE_ID'] = 108
        elif parameters[17].valueAsText == 'Interstate':
            segfields['SYMBOL_TYPE_ID'] = 200
        elif parameters[17].valueAsText == 'Interstate Ramp':
            segfields['SYMBOL_TYPE_ID'] = 208
        elif parameters[17].valueAsText == 'US Highway':
            segfields['SYMBOL_TYPE_ID'] = 300
        elif parameters[17].valueAsText == 'US Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 308
        elif parameters[17].valueAsText == 'State Highway':
            segfields['SYMBOL_TYPE_ID'] = 400
        elif parameters[17].valueAsText == 'State Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 408
        elif parameters[17].valueAsText == 'County 500 Route':
            segfields['SYMBOL_TYPE_ID'] = 500
        elif parameters[17].valueAsText == 'County 500 Ramp':
            segfields['SYMBOL_TYPE_ID'] = 508
        elif parameters[17].valueAsText == 'Other County Route':
            segfields['SYMBOL_TYPE_ID'] = 600
        elif parameters[17].valueAsText == 'Other County Ramp':
            segfields['SYMBOL_TYPE_ID'] = 608
        elif parameters[17].valueAsText == 'Local Road':
            segfields['SYMBOL_TYPE_ID'] = 700
        elif parameters[17].valueAsText == 'Local Ramp':
            segfields['SYMBOL_TYPE_ID'] = 708
        elif parameters[17].valueAsText == 'Alley':
            segfields['SYMBOL_TYPE_ID'] = 900
        else:
            pass

        if parameters[18].valueAsText == 'Both': #text
            segfields['TRAVEL_DIR_TYPE_ID'] = 'B'
        elif parameters[18].valueAsText == 'Decreasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'D'
        elif parameters[18].valueAsText == 'Increasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'I'
        else:
            pass

        islinref = True
        if parameters[19].valueAsText == 'Public': #text
            segfields['JURIS_TYPE_ID'] = 'PUB'
            #islinref = True
        elif parameters[19].valueAsText == 'Private' or parameters[19].valueAsText == 'Private (with linear referencing)':
            segfields['JURIS_TYPE_ID'] = 'PRI'
        elif parameters[19].valueAsText == 'Unknown':
            segfields['JURIS_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[20].valueAsText == 'Draft': #text
            segfields['OIT_REV_TYPE_ID'] = 'D'
        elif parameters[20].valueAsText == 'Final':
            segfields['OIT_REV_TYPE_ID'] = 'F'
        elif parameters[20].valueAsText == 'Incoming':
            segfields['OIT_REV_TYPE_ID'] = 'I'
        else:
            pass

        if parameters[21].valueAsText == 'Draft': #text
            segfields['DOT_REV_TYPE_ID'] = 'D'
        elif parameters[21].valueAsText == 'Final':
            segfields['DOT_REV_TYPE_ID'] = 'F'
        elif parameters[21].valueAsText == 'Incoming':
            segfields['DOT_REV_TYPE_ID'] = 'I'
        else:
            pass

        arcpy.AddMessage("SEGMENT variables validated")

        ############################################################################
        ## SEG_NAME Parameters

        if parameters[1].value == True:  # if the user is trying to insert segname
            if parameters[22].valueAsText == "Local Name":
                seg_name['NAME_TYPE_ID'] = "L"
            elif parameters[22].valueAsText == "Highway Name":
                seg_name['NAME_TYPE_ID'] = "H"
            if parameters[23].value:
                seg_name['RANK'] = parameters[23].valueAsText
            if parameters[24].value:
                seg_name['NAME_FULL'] = parameters[24].valueAsText

            # The 7 part names must be scrubbed for errors...use FullNames class function
            if parameters[25].value:
                seg_name['PRE_DIR'] = erebus.FullName(predir=parameters[25].valueAsText).concatenate()
            if parameters[26].value:
                seg_name['PRE_TYPE'] = erebus.FullName(pretype=parameters[26].valueAsText).concatenate()
            if parameters[27].value:
                seg_name['PRE_MOD'] = erebus.FullName(premod=parameters[27].valueAsText).concatenate()
            if parameters[28].value:
                seg_name['NAME'] = erebus.FullName(name=parameters[28].valueAsText).concatenate()
            if parameters[29].value:
                seg_name['SUF_TYPE'] = erebus.FullName(suftype=parameters[29].valueAsText).concatenate()
            if parameters[30].value:
                seg_name['SUF_DIR'] = erebus.FullName(sufdir=parameters[30].valueAsText).concatenate()
            if parameters[31].value:
                seg_name['SUF_MOD'] = erebus.FullName(sufmod=parameters[31].valueAsText).concatenate()

            # DATA_SRC_TYPE_ID
            if parameters[32].value:
                for key,value in Domains['DATA_SOURCE_TYPE'].iteritems():
                    if value == parameters[32].value:
                        seg_name['DATA_SRC_TYPE_ID'] = key

            arcpy.AddMessage("SEG_NAME variables validated")
        ############################################################################
        ## SEG_SHIELD Parameters
        if seg_name['NAME_TYPE_ID'] == "H":  # only populate if the seg name is "highway"
            # RANK
            if parameters[33].value:
                seg_shield['RANK'] = parameters[33].value

            # SEG_SHIELD_TYPE_ID
            if parameters[34].value:
                for key,value in Domains['SHIELD_TYPE'].iteritems():
                    if value == parameters[34].value:
                        seg_shield['SHIELD_TYPE_ID'] = key

            # SHIELD_SUBTYPE_ID
            if parameters[35].value:
                for key,value in Domains['SHIELD_SUBTYPE'].iteritems():
                    if value == parameters[35].value:
                        seg_shield['SHIELD_SUBTYPE_ID'] = key

            # SHIELD_NAME
            if parameters[36].value:
                seg_shield['SHIELD_NAME'] = parameters[36].value

            # DATA_SRC_TYPE_ID
            # DATA_SRC_TYPE_ID
            if seg_name['DATA_SRC_TYPE_ID']:
                seg_shield['DATA_SRC_TYPE_ID'] = seg_name['DATA_SRC_TYPE_ID']


            arcpy.AddMessage("SEG_SHIELD variables validated")

        ############################################################################
        ## LINEAR_REF Parameters

        # parameters 38-43, the switch for these params is "islinref" which is tied to parameter 19 (juris type)
        if islinref == True:
            if parameters[38].value:
                lin_ref['SRI'] = parameters[38].valueAsText

            # SHIELD_SUBTYPE_ID
            if parameters[39].value:
                for key,value in Domains['LRS_TYPE'].iteritems():
                    if value == parameters[39].value:
                        lin_ref['LRS_TYPE_ID'] = key

            # SEGMENT_TYPE
            if parameters[40].value:
                for key,value in Domains['SEGMENT_TYPE'].iteritems():
                    if value == parameters[40].value:
                        lin_ref['SEG_TYPE_ID'] = key

            # arcpy.AddMessage('from value {0}'.format(parameters[41].value))
            # if parameters[42].value and not parameters[41].value:
            #     lin_ref['MILEPOST_FR'] = 0
            # else:
            lin_ref['MILEPOST_FR'] = parameters[41].value
            lin_ref['MILEPOST_TO'] = parameters[42].value
            lin_ref['RCF'] = parameters[43].valueAsText
            arcpy.AddMessage("LINEAR_REF variables validated")

        ############################################################################
        ## SLD_ROUTE Parameters
        # parameters 44-49


        if islinref == True:
            #sld_route['SRI'] = parameters[44].valueAsText
            sldcase = 0
            if parameters[38].value and parameters[44].value: # if there is a value in lin_ref SRI...
                # check to see if this is a new or existing SRI
                sld_route['SRI'] = parameters[44].valueAsText
                sldquery = erebus.sqlcursor("SRI", sld_route['SRI'])
                sldqlen = 0
                with arcpy.da.SearchCursor(sldtab,"*", sldquery) as cursor:
                    for row in cursor:
                        sldqlen = len(row)
                if sldqlen > 0: # 2) if SRI already exists, no new record in SLD_ROUTE
                    sldcase = 2
                    arcpy.AddWarning("NEW FEATURE: SRI " + sld_route['SRI'] + " already exists in SLD_ROUTE. 1 record will be inserted in LIN_REF. 0 records will be inserted in SLD_ROUTE")
                if sldqlen == 0: # 3) SRI matches, and there is no existing record. Insert a new record in SLD_ROUTE
                    sldcase = 3
                    # Route Type ID
                    if parameters[45].value:
                        for key,value in Domains['ROUTE_TYPE'].iteritems():
                            if value == parameters[45].value:
                                sld_route['ROUTE_TYPE_ID'] = key
                    if parameters[46].value:
                        sld_route['SLD_NAME'] = parameters[46].valueAsText
                    if parameters[47].value:
                        sld_route['SLD_COMMENT'] = parameters[47].valueAsText
                    if parameters[48].value:
                        sld_route['SLD_DIRECTION'] = parameters[48].valueAsText
                    if parameters[49].value:
                        sld_route['SIGN_NAME'] = parameters[49].valueAsText

                arcpy.AddMessage("SLD_ROUTE variables validated")

        ############################################################################
        ############################################################################
        ############################################################################

        globalid = lastselect['SEGMENT'][0]['GLOBALID']  #globalid = lastselect[26]  # this is the global id of SEGMENT

        seg_guid = erebus.calcGUID()
        segfields['SEG_GUID'] = seg_guid
        seg_name['SEG_GUID'] = seg_guid
        seg_shield['SEG_GUID'] = seg_guid
        lin_ref['SEG_GUID'] = seg_guid

        segfields['GLOBALID'] = globalid
        seg_name['GLOBALID'] = globalid
        seg_shield['GLOBALID'] = globalid
        lin_ref['GLOBALID'] = globalid

        try:
            arcpy.AddMessage("SEG_GUID of new segment is {0}".format(seg_guid))
            arcpy.AddMessage("GLOBALID of new segment is {0}".format(globalid))
        except:
            arcpy.AddError("GLOBALID of new segment not found")

        seg_sql = "GLOBALID = '%s'" % (globalid)


        ################################################################################
        ## 2) Add user input to ROAD.SEG_NAME
        ################################################################################

        if parameters[1].valueAsText == "true":

            ## 2.1 Insert a row with the SEG_GUID
            cursor = arcpy.InsertCursor(segnametab)
            row = cursor.newRow()
            row.setValue('SEG_GUID', segfields['SEG_GUID'])
            if seg_name['NAME_TYPE_ID']:
                row.setValue('NAME_TYPE_ID', seg_name['NAME_TYPE_ID'])
            if seg_name['RANK']:
                row.setValue('RANK', seg_name['RANK'])
            if seg_name['NAME_FULL']:
                row.setValue('NAME_FULL', seg_name['NAME_FULL'])
            if seg_name['PRE_DIR']:
                row.setValue('PRE_DIR', seg_name['PRE_DIR'])
            if seg_name['PRE_TYPE']:
                row.setValue('PRE_TYPE', seg_name['PRE_TYPE'])
            if seg_name['PRE_MOD']:
                row.setValue('PRE_MOD', seg_name['PRE_MOD'])
            if seg_name['NAME']:
                row.setValue('NAME', seg_name['NAME'])
            if seg_name['SUF_TYPE']:
                row.setValue('SUF_TYPE', seg_name['SUF_TYPE'])
            if seg_name['SUF_DIR']:
                row.setValue('SUF_DIR', seg_name['SUF_DIR'])
            if seg_name['SUF_MOD']:
                row.setValue('SUF_MOD', seg_name['SUF_MOD'])
            if seg_name['DATA_SRC_TYPE_ID']:
                row.setValue('DATA_SRC_TYPE_ID', seg_name['DATA_SRC_TYPE_ID'])
            cursor.insertRow(row)
            arcpy.AddMessage("SEG_NAME record inserted")
            try: del row
            except: pass
            try: del cursor
            except: pass

        ################################################################################
        ## 3) Add user input to ROAD.SEG_SHIELD
        ################################################################################

        if seg_name['NAME_TYPE_ID'] == "H":
            ## 2.1 Insert a row with the SEG_GUID
            cursor = arcpy.InsertCursor(segshieldtab)
            row = cursor.newRow()
            row.setValue('SEG_GUID', segfields['SEG_GUID'])
            if seg_shield['RANK']:
                row.setValue('RANK', seg_shield['RANK'])
            if seg_shield['SHIELD_TYPE_ID']:
                row.setValue('SHIELD_TYPE_ID', seg_shield['SHIELD_TYPE_ID'])
            if seg_shield['SHIELD_SUBTYPE_ID']:
                row.setValue('SHIELD_SUBTYPE_ID', seg_shield['SHIELD_SUBTYPE_ID'])
            if seg_shield['SHIELD_NAME']:
                row.setValue('SHIELD_NAME', seg_shield['SHIELD_NAME'])
            if seg_shield['DATA_SRC_TYPE_ID']:
                row.setValue('DATA_SRC_TYPE_ID', seg_shield['DATA_SRC_TYPE_ID'])
            cursor.insertRow(row)
            arcpy.AddMessage("SEG_SHIELD record inserted")
            try: del row
            except: pass
            try: del cursor
            except: pass

        ################################################################################
        ## 4) Add user input to ROAD.LINEAR_REF
        ################################################################################

        if islinref == True:

            cursor = arcpy.InsertCursor(linreftab)
            row = cursor.newRow()
            row.setValue('SEG_GUID', segfields['SEG_GUID'])
            if lin_ref['SRI']:
                row.setValue('SRI', lin_ref['SRI'])
            if lin_ref['LRS_TYPE_ID']:
                row.setValue('LRS_TYPE_ID', lin_ref['LRS_TYPE_ID'])
            if lin_ref['SEG_TYPE_ID']:
                row.setValue('SEG_TYPE_ID', lin_ref['SEG_TYPE_ID'])
            if lin_ref['MILEPOST_FR'] or lin_ref['MILEPOST_FR'] == 0:
                row.setValue('MILEPOST_FR', lin_ref['MILEPOST_FR'])
            if lin_ref['MILEPOST_TO'] or lin_ref['MILEPOST_TO'] == 0:
                row.setValue('MILEPOST_TO', lin_ref['MILEPOST_TO'])
            if lin_ref['RCF']:
                row.setValue('RCF', lin_ref['RCF'])
            cursor.insertRow(row)
            arcpy.AddMessage("LINEAR_REF record inserted")
            try: del row
            except: pass
            try: del cursor
            except: pass


        ################################################################################
        ## 5) Add user input to ROAD.SLD_ROUTE
        ################################################################################

        if islinref == True:
            if sldcase == 3: # new SRI in both the SLD and LINREF

                cursor = arcpy.InsertCursor(sldtab)
                row = cursor.newRow()
                row.setValue('SRI', sld_route['SRI'])
                if sld_route['ROUTE_TYPE_ID']:
                    row.setValue('ROUTE_TYPE_ID', sld_route['ROUTE_TYPE_ID'])
                if sld_route['SLD_NAME']:
                    row.setValue('SLD_NAME', sld_route['SLD_NAME'])
                if sld_route['SLD_COMMENT']:
                    row.setValue('SLD_COMMENT', sld_route['SLD_COMMENT'])
                if sld_route['SLD_DIRECTION']:
                    row.setValue('SLD_DIRECTION', sld_route['SLD_DIRECTION'])
                if sld_route['SIGN_NAME']:
                    row.setValue('SIGN_NAME', sld_route['SIGN_NAME'])
                cursor.insertRow(row)
                arcpy.AddMessage("SLD_ROUTE record inserted")
                try: del row
                except: pass
                try: del cursor
                except: pass


        ################################################################################
        ## 1) Add user input to ROAD.SEGMENT
        ################################################################################

        # PRIME_NAME Logic. Prime name gets populated with RANK = 1, and "Local" by default.
        # Next, if  (1, "local") is not there, look for (1,"Highway"). By default, a new segment
        # (i.e. this tool), the rank is 1, so push whatever name is there to PRIME_NAME...if
        # there is an entry. The switch is parameters[1].valueAsText.

        seg_sql = "GLOBALID = '%s'" % (globalid)


        # If there are MILEPOST values, insert them as M-Values
        if islinref == True and parameters[39].value == 'NJDOT Multi-Centerline' and (parameters[41].value or parameters[41].value == 0) and (parameters[42].value or parameters[42].value == 0):
            print('IN MP LOGIC #######################')
            try:

# this works with exception on 10.2.1, still would need to delete the original segment.

##                FROM = lin_ref['MILEPOST_FR']
##                TO = lin_ref['MILEPOST_TO']
##                # get the current geometry, make a new polyline geometry with new M-values (pline)
##                with arcpy.da.SearchCursor(segmentfc,["SHAPE@"], seg_sql) as cursor:
##                    for row in cursor:
##                        fulldist = row[0].getLength('PLANAR', 'FEET')
##                        geometry = row[0]
##
##                        json_obj = erebus.wkt_to_esrijson(geometry)['esrijson']
##                        mp_to = len(json_obj['paths'][0]) - 1
##                        conversionfactor = (math.fabs(TO - FROM) / fulldist)
##                        for i,v in enumerate(json_obj['paths'][0]):
##                            if i == 0:
##                                json_obj['paths'][0][i][2] = float(FROM)
##                            elif i == mp_to:
##                                json_obj['paths'][0][i][2] = float(TO)
##                            else:
##                                # distance in map units between last vertex and current vertex
##                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
##                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
##                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
##                                vert_lrdist = vertdist * conversionfactor
##                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)
##                        for feature in json_obj['paths']:
##                            pline = arcpy.Polyline(arcpy.Array([arcpy.Point(X=coords[0], Y=coords[1], M=coords[2]) for coords in feature]), geometry.spatialReference, False, True)
##                        # convert the json back to WKT
##                        wktobj = erebus.esrijson_to_wkt(json_obj)
##
##                # insert the geometry into SEGMENT
##                cursor = arcpy.da.InsertCursor(segmentfc,["SHAPE@"])
##                cursor.insertRow([pline])
##                del cursor


################################################################################

# this works on 10.2.1

                with arcpy.da.SearchCursor(segmentfc,["SHAPE@"], seg_sql) as c1:
                    for r1 in c1:
                        fulldist = r1[0].getLength('PLANAR', 'FEET')
                        geometry = r1[0]


                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@WKT"], seg_sql) as cursor:
                    for row in cursor:

                        json_obj = erebus.wkt_to_esrijson(geometry)['esrijson']
                        mp_to = len(json_obj['paths'][0]) - 1
                        conversionfactor = (math.fabs(lin_ref['MILEPOST_TO'] - lin_ref['MILEPOST_FR']) / fulldist)
                        for i,v in enumerate(json_obj['paths'][0]):
                            if i == 0:
                                json_obj['paths'][0][i][2] = float(lin_ref['MILEPOST_FR'])
                            elif i == mp_to:
                                json_obj['paths'][0][i][2] = float(lin_ref['MILEPOST_TO'])
                            else:
                                # distance in map units between last vertex and current vertex
                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
                                vert_lrdist = vertdist * conversionfactor
                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)

                        # convert the json back to WKT
                        wktobj = erebus.esrijson_to_wkt(json_obj)
                        cursor.updateRow([wktobj['WKT'],])
                        arcpy.AddMessage("SEGMENT M-Values inserted without exception")

##################################################################################################


##                import json, math
##                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@"], seg_sql) as cursor:
##                    for row in cursor:
##                        jj = row[0].JSON
##                        json_obj = json.loads(row[0].JSON)
##                        mp_to = len(json_obj['paths'][0]) - 1
##                        fulldist = row[0].getLength('PLANAR', 'FEET')
##                        conversionfactor = (math.fabs(lin_ref['MILEPOST_TO'] - lin_ref['MILEPOST_FR']) / fulldist)
##                        for i,v in enumerate(json_obj['paths'][0]):
##                            if i == 0:
##                                json_obj['paths'][0][i][2] = float(lin_ref['MILEPOST_FR'])
##                            else:
##                                # distance in map units between last vertex and current vertex
##                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
##                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
##                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
##                                vert_lrdist = vertdist * conversionfactor
##                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)
##                        print json_obj
##                        for feature in json_obj['paths']:
##                            pline = arcpy.Polyline(arcpy.Array([arcpy.Point(X=coords[0], Y=coords[1], M=coords[2]) for coords in feature]), row[0].spatialReference, False, True)
##                        print pline.JSON
##                        row[0] = pline
##                        cursor.updateRow(row)
##                        arcpy.AddMessage("SEGMENT M-Values inserted without exception")


##                with arcpy.da.SearchCursor(segmentfc,["SHAPE@"], seg_sql) as c1:
##                    for r1 in c1:
##                        fulldist = r1[0].getLength('PLANAR', 'FEET')
##
##                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@JSON"], seg_sql) as cursor:
##                    for row in cursor:
##                        json_obj = json.loads(row[0])
##                        mp_to = len(json_obj['paths'][0]) - 1
##                        conversionfactor = (math.fabs(lin_ref['MILEPOST_TO'] - lin_ref['MILEPOST_FR']) / fulldist)
##                        for i,v in enumerate(json_obj['paths'][0]):
##                            if i == 0:
##                                json_obj['paths'][0][i][2] = float(lin_ref['MILEPOST_FR'])
##                            else:
##                                # distance in map units between last vertex and current vertex
##                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
##                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
##                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
##                                vert_lrdist = vertdist * conversionfactor
##                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)
##                        cursor.updateRow([json.dumps(json_obj),])
##                        arcpy.AddMessage("SEGMENT M-Values inserted without exception")


            except SystemError as e:
                arcpy.AddMessage("SEGMENT M-Values inserted with exception")
                print(traceback.format_exc())
            except:
                arcpy.AddMessage("SEGMENT M-Values failed with exception")
                print(traceback.format_exc())


        cursor = arcpy.UpdateCursor(segmentfc, seg_sql)
        for row in cursor:
            if seg_id_switch == "ON":
                row.setValue("SEG_ID", segfields['SEG_ID'])
            row.setValue("SEG_GUID", seg_guid)
            if len(str(seg_name['NAME_FULL'])) > 0:
                row.setValue('PRIME_NAME', seg_name['NAME_FULL'])
            if len(str(segfields['ADDR_L_FR'])) > 0:
                row.setValue('ADDR_L_FR', segfields['ADDR_L_FR'])
            if len(str(segfields['ADDR_L_TO'])) > 0:
                row.setValue('ADDR_L_TO', segfields['ADDR_L_TO'])
            if len(str(segfields['ADDR_R_FR'])) > 0:
                row.setValue('ADDR_R_FR', segfields['ADDR_R_FR'])
            if len(str(segfields['ADDR_R_TO'])) > 0:
                row.setValue('ADDR_R_TO', segfields['ADDR_R_TO'])
            if len(str(segfields['ZIPCODE_L'])) > 0:
                row.setValue('ZIPCODE_L', segfields['ZIPCODE_L'])
            if len(str(segfields['ZIPCODE_R'])) > 0:
                row.setValue('ZIPCODE_R', segfields['ZIPCODE_R'])
            if len(str(segfields['ZIPNAME_L'])) > 0:
                row.setValue('ZIPNAME_L', segfields['ZIPNAME_L'])
            if len(str(segfields['ZIPNAME_R'])) > 0:
                row.setValue('ZIPNAME_R', segfields['ZIPNAME_R'])
            if len(str(segfields['MUNI_ID_L'])) > 0:
                row.setValue('MUNI_ID_L', segfields['MUNI_ID_L'])
            if len(str(segfields['MUNI_ID_R'])) > 0:
                row.setValue('MUNI_ID_R', segfields['MUNI_ID_R'])

            #---
            row.setValue('ELEV_TYPE_ID_FR', segfields['ELEV_TYPE_ID_FR'])
            row.setValue('ELEV_TYPE_ID_TO', segfields['ELEV_TYPE_ID_TO'])
            row.setValue('ACC_TYPE_ID', segfields['ACC_TYPE_ID'])
            row.setValue('SURF_TYPE_ID', segfields['SURF_TYPE_ID'])
            row.setValue('STATUS_TYPE_ID', segfields['STATUS_TYPE_ID'])
            row.setValue('SYMBOL_TYPE_ID', segfields['SYMBOL_TYPE_ID'])
            row.setValue('TRAVEL_DIR_TYPE_ID', segfields['TRAVEL_DIR_TYPE_ID'])
            row.setValue('JURIS_TYPE_ID', segfields['JURIS_TYPE_ID'])
            row.setValue('OIT_REV_TYPE_ID', segfields['OIT_REV_TYPE_ID'])
            row.setValue('DOT_REV_TYPE_ID', segfields['DOT_REV_TYPE_ID'])
            cursor.updateRow(row)
            arcpy.AddMessage("SEGMENT record inserted")
            del cursor, row


        set_tool_indicator(arcpy.env.scratchWorkspace, False)

        return

# END NewSegment
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||

# Split tool (Deprecated)

class Split(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Split"
        self.description = "Split a feature"
        self.canRunInBackground = False

        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab

    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="Update LINEAR_REF MILEPOST_FR and MILEPOST_TO values (if applicable)",
            name="update milepost",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param0.value = True

        params = [param0]
        return params

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
        import arcpy
        import pickle
        import os, sys, traceback
        import pythonaddins

        splitpath = arcpy.env.scratchWorkspace + "\\splitselection.p"
        if os.path.exists(splitpath):
            with open(splitpath,'rb') as splitopen:
                lastselect, segmentgeo = pickle.load(splitopen)
            #os.remove(splitpath)
        splitpath2 = arcpy.env.scratchWorkspace + "\\splitselectionvariables.p"
        if os.path.exists(splitpath2):
            with open(splitpath2,'rb') as splitopen2:
                segfields1,segfields2 = pickle.load(splitopen2)

        splitpath3 = arcpy.env.scratchWorkspace + "\\splitgeometries.p"
        if os.path.exists(splitpath3):
            with open(splitpath3,'rb') as splitopen3:
                ge1, ge2 = pickle.load(splitopen3)

        ########################################################################
        ## Create the two new SEG_GUIDS
        seg_guid1 = erebus.calcGUID()
        seg_guid2 = erebus.calcGUID()

        arcpy.AddMessage("\nNew SEG_GUID for segment 1: {0}\nNew SEG_GUID for segment 2: {1}\n".format(seg_guid1,seg_guid2))

        ########################################################################
        ## Update and Insert (copy)
        splittool_result = {'block1': False, 'block2': False, 'block3': False}
        try:
            updateandcopy = erebus.UpdateCopy(lastselect["SEG_GUID"], seg_guid1, seg_guid2) # UpadateCopy class object

            ## SEG_NAME
            segnameresult = updateandcopy.segname(segnametab)
            if segnameresult['result'] == 'success':
                arcpy.AddMessage('SEG_NAME Attributes copied to the 2 new segments')
            elif segnameresult['result'] == 'no matching records':
                arcpy.AddMessage('No SEG_NAME records in the original segment')
            else:
                arcpy.AddWarning("\nUpdateCopy.segname failed, result is: {0}".format(segnameresult))

            ## SEG_SHIELD
            segshieldresult = updateandcopy.segshield(segshieldtab)
            if segshieldresult['result'] == 'success':
                arcpy.AddMessage('SEG_SHIELD Attributes copied to the 2 new segments')
            elif segshieldresult['result'] == 'no matching records':
                arcpy.AddMessage('No SEG_SHIELD records in the original segment')
            else:
                arcpy.AddWarning("\nUpdateCopy.segshield failed, result is: {0}".format(segshieldresult))

            ## LINEAR_REF
            if parameters[0].value == True:  # check to make sure that there are M-values
                lrM = True
                try:
                    if 'curvePaths' in ge1.keys():
                        # format for true curves
                        xym1 = []; xym2 = [];
                        for i in ge1['curvePaths'][0]:
                            if type(i) is list:
                                xym1.append(i)
                            elif type(i) is dict:
                                xym1.append(i['c'][0])
                        for i in ge2['curvePaths'][0]:
                            if type(i) is list:
                                xym2.append(i)
                            elif type(i) is dict:
                                xym2.append(i['c'][0])
                    elif 'paths' in ge1.keys():
                        #format for no true curves
                        xym1 = ge1['paths'][0] # list of lists. each list has [x,y,m]
                        xym2 = ge2['paths'][0]
                    round(xym1[0][2],8)
                    round(xym2[0][2],8)
                except:
                    lrM = False
                    arcpy.AddWarning('LINEAR_REF MILEPOST values were not updated, because there are no M-Values on this segment.')
            lrresult = updateandcopy.linearref(linreftab, ge1, ge2, lrM)
            if lrresult['result'] == 'success':
                arcpy.AddMessage('LINEAR_REF Attributes copied to the 2 new segments')
                arcpy.AddMessage('LINEAR_REF result: {0}'.format(lrresult))
            elif lrresult['result'] == 'no matching records':
                arcpy.AddMessage('No LINEAR_REF records in the original segment')
            else:
                arcpy.AddWarning("\nUpdateCopy.linearref failed, result is: {0}\n\n The purpose of this function is to update the MILEPOST values based on the new M-Values. The failure is most likely due to the segment not having M-Values.\n".format(lrresult))

            ## SEGMENT_COMMENTS
            commdelresult = erebus.delete(lastselect["SEG_GUID"],segcommtab)
            if commdelresult['result'] == 'success':
                arcpy.AddMessage('SEGMENT_COMMENTS records deleted')
            elif commdelresult['result'] == 'no matches':
                arcpy.AddMessage('No SEGMENT_COMMENTS records found')
            elif commdelresult['trace']:
                arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(lrresult))
            splittool_result['block1'] = True; splittool_result['segnameresult'] = segnameresult; splittool_result['segshieldresult'] = segshieldresult; splittool_result['lrresult'] = lrresult; splittool_result['commentsdelete'] = commdelresult
        except:
            trace = traceback.format_exc()
            splittool_result['trace'] = trace
            # write the result
            r_path = arcpy.env.scratchWorkspace + "\\splittool_result.p"
            with open(r_path, 'wb') as output:
                pickle.dump(splittool_result, output, -1)
            # end the tool
            sys.exit('NJRE Split block1 error')

        ########################################################################
        ## SEGMENT
        # create sql queries
        globalsql1 = erebus.sqlGUID("GLOBALID",segfields1['GLOBALID'])
        globalsql2 = erebus.sqlGUID("GLOBALID",segfields2['GLOBALID'])
        try:
            # update cursor for both segments
            cursor = arcpy.UpdateCursor(segmentfc, globalsql1)
            for row in cursor:
                row.setValue('SEG_GUID', seg_guid1)
                if segfields1['ADDR_L_FR']:
                    row.setValue('ADDR_L_FR', segfields1['ADDR_L_FR'])
                if segfields1['ADDR_L_TO']:
                    row.setValue('ADDR_L_TO', segfields1['ADDR_L_TO'])
                if segfields1['ADDR_R_FR']:
                    row.setValue('ADDR_R_FR', segfields1['ADDR_R_FR'])
                if segfields1['ADDR_R_TO']:
                    row.setValue('ADDR_R_TO', segfields1['ADDR_R_TO'])
                if segfields1['ZIPCODE_L']:
                    row.setValue('ZIPCODE_L', segfields1['ZIPCODE_L'])
                if segfields1['ZIPCODE_R']:
                    row.setValue('ZIPCODE_R', segfields1['ZIPCODE_R'])
                if segfields1['ZIPNAME_L']:
                    row.setValue('ZIPNAME_L', segfields1['ZIPNAME_L'])
                if segfields1['ZIPNAME_R']:
                    row.setValue('ZIPNAME_R', segfields1['ZIPNAME_R'])
                if segfields1['MUNI_ID_L']:
                    row.setValue('MUNI_ID_L', segfields1['MUNI_ID_L'])
                if segfields1['MUNI_ID_R']:
                    row.setValue('MUNI_ID_R', segfields1['MUNI_ID_R'])
                if segfields1['ELEV_TYPE_ID_FR']:
                    row.setValue('ELEV_TYPE_ID_FR', segfields1['ELEV_TYPE_ID_FR'])
                if segfields1['ELEV_TYPE_ID_TO']:
                    row.setValue('ELEV_TYPE_ID_TO', segfields1['ELEV_TYPE_ID_TO'])
                if segfields1['ACC_TYPE_ID']:
                    row.setValue('ACC_TYPE_ID', segfields1['ACC_TYPE_ID'])
                if segfields1['SURF_TYPE_ID']:
                    row.setValue('SURF_TYPE_ID', segfields1['SURF_TYPE_ID'])
                if segfields1['STATUS_TYPE_ID']:
                    row.setValue('STATUS_TYPE_ID', segfields1['STATUS_TYPE_ID'])
                if segfields1['SYMBOL_TYPE_ID']:
                    row.setValue('SYMBOL_TYPE_ID', segfields1['SYMBOL_TYPE_ID'])
                if segfields1['TRAVEL_DIR_TYPE_ID']:
                    row.setValue('TRAVEL_DIR_TYPE_ID', segfields1['TRAVEL_DIR_TYPE_ID'])
                if segfields1['JURIS_TYPE_ID']:
                    row.setValue('JURIS_TYPE_ID', segfields1['JURIS_TYPE_ID'])
                if segfields1['OIT_REV_TYPE_ID']:
                    row.setValue('OIT_REV_TYPE_ID', segfields1['OIT_REV_TYPE_ID'])
                if segfields1['DOT_REV_TYPE_ID']:
                    row.setValue('DOT_REV_TYPE_ID', segfields1['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            del row, cursor

            cursor = arcpy.UpdateCursor(segmentfc, globalsql2)
            for row in cursor:
                row.setValue('SEG_GUID', seg_guid2)
                if segfields2['ADDR_L_FR']:
                    row.setValue('ADDR_L_FR', segfields2['ADDR_L_FR'])
                if segfields2['ADDR_L_TO']:
                    row.setValue('ADDR_L_TO', segfields2['ADDR_L_TO'])
                if segfields2['ADDR_R_FR']:
                    row.setValue('ADDR_R_FR', segfields2['ADDR_R_FR'])
                if segfields2['ADDR_R_TO']:
                    row.setValue('ADDR_R_TO', segfields2['ADDR_R_TO'])
                if segfields2['ZIPCODE_L']:
                    row.setValue('ZIPCODE_L', segfields2['ZIPCODE_L'])
                if segfields2['ZIPCODE_R']:
                    row.setValue('ZIPCODE_R', segfields2['ZIPCODE_R'])
                if segfields2['ZIPNAME_L']:
                    row.setValue('ZIPNAME_L', segfields2['ZIPNAME_L'])
                if segfields2['ZIPNAME_R']:
                    row.setValue('ZIPNAME_R', segfields2['ZIPNAME_R'])
                if segfields2['MUNI_ID_L']:
                    row.setValue('MUNI_ID_L', segfields2['MUNI_ID_L'])
                if segfields2['MUNI_ID_R']:
                    row.setValue('MUNI_ID_R', segfields2['MUNI_ID_R'])
                if segfields2['ELEV_TYPE_ID_FR']:
                    row.setValue('ELEV_TYPE_ID_FR', segfields2['ELEV_TYPE_ID_FR'])
                if segfields2['ELEV_TYPE_ID_TO']:
                    row.setValue('ELEV_TYPE_ID_TO', segfields2['ELEV_TYPE_ID_TO'])
                if segfields2['ACC_TYPE_ID']:
                    row.setValue('ACC_TYPE_ID', segfields2['ACC_TYPE_ID'])
                if segfields2['SURF_TYPE_ID']:
                    row.setValue('SURF_TYPE_ID', segfields2['SURF_TYPE_ID'])
                if segfields2['STATUS_TYPE_ID']:
                    row.setValue('STATUS_TYPE_ID', segfields2['STATUS_TYPE_ID'])
                if segfields2['SYMBOL_TYPE_ID']:
                    row.setValue('SYMBOL_TYPE_ID', segfields2['SYMBOL_TYPE_ID'])
                if segfields2['TRAVEL_DIR_TYPE_ID']:
                    row.setValue('TRAVEL_DIR_TYPE_ID', segfields2['TRAVEL_DIR_TYPE_ID'])
                if segfields2['JURIS_TYPE_ID']:
                    row.setValue('JURIS_TYPE_ID', segfields2['JURIS_TYPE_ID'])
                if segfields2['OIT_REV_TYPE_ID']:
                    row.setValue('OIT_REV_TYPE_ID', segfields2['OIT_REV_TYPE_ID'])
                if segfields2['DOT_REV_TYPE_ID']:
                    row.setValue('DOT_REV_TYPE_ID', segfields2['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            del row, cursor

            splittool_result['block2'] = True

        except:
            trace = traceback.format_exc()
            splittool_result['trace'] = trace
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            # write the result
            r_path = arcpy.env.scratchWorkspace + "\\splittool_result.p"
            with open(r_path, 'wb') as output:
                pickle.dump(splittool_result, output, -1)
            sys.exit("NJRE Split block2 Segment update error")



        try:

            ########################################################################
            ## Insert two new records into SEGMENT_TRANS

            #segment_trans(oldguid, newguid, table, seg_id_arch)
            trans_result1 = erebus.segment_trans(lastselect["SEG_GUID"], seg_guid1, transtab, lastselect["SEGMENT"][0]["SEG_ID"])
            trans_result2 = erebus.segment_trans(lastselect["SEG_GUID"], seg_guid2, transtab, lastselect["SEGMENT"][0]["SEG_ID"])

            if trans_result1['result'] == 'success':
                arcpy.AddMessage('New record inseted into SEGMENT_TRANS for segment 1')
            else:
                arcpy.AddWarning("\neFailed to insert record into SEGMENT_TRANS, result is: {0}".format(trans_result1))
            if trans_result2['result'] == 'success':
                arcpy.AddMessage('New record inseted into SEGMENT_TRANS for segment 1')
            else:
                arcpy.AddWarning("\neFailed to insert record into SEGMENT_TRANS, result is: {0}".format(trans_result2))

            ########################################################################
            ## Insert one new record into SEGMENT_CHANGE

            sc_obj = erebus.SegmentChange(lastselect["SEG_GUID"], segmentchangetab)
            scresult = sc_obj.insert(segmentgeo, seg_id_arch = lastselect["SEGMENT"][0]["SEG_ID"]) # insert(self, segmentgeo, change_type_id = 'R', comments = None, seg_id_arch = None)
            if scresult['result'] == 'success':
                arcpy.AddMessage('New record inseted into SEGMENT_CHANGE')
                arcpy.AddMessage('New record inseted into SEGMENT_CHANGE {0}'.format(scresult['method']))
            else:
                arcpy.AddWarning("\neFailed to insert record into SEGMENT_CHANGE, result is: {0}".format(scresult))

            splittool_result['block3'] = True; splittool_result['trans_result1'] = trans_result1; splittool_result['trans_result2'] = trans_result2; splittool_result['scresult'] = scresult

            # write the successful result

            r_path = arcpy.env.scratchWorkspace + "\\splittool_result.p"
            with open(r_path, 'wb') as output:
                pickle.dump(splittool_result, output, -1)

        except:
            trace = traceback.format_exc()
            splittool_result['trace'] = trace
            # write the result
            r_path = arcpy.env.scratchWorkspace + "\\splittool_result.p"
            with open(r_path, 'wb') as output:
                pickle.dump(splittool_result, output, -1)




        return

# END Split
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

class SplitSegment(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "SplitSegment"
        self.description = "SplitSegment"
        self.canRunInBackground = False
        self.tester = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
    def getParameterInfo(self):
        """Define parameter definitions"""
        param0 = arcpy.Parameter(
            displayName="SEG_ID",
            name="SEG_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param0.enabled = False

        #
        param1 = arcpy.Parameter(
            displayName="PRIME_NAME",
            name="PRIME_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param1.enabled = False

        #
        param2 = arcpy.Parameter(
            displayName="ADDR_L_FR",
            name="ADDR_L_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param3 = arcpy.Parameter(
            displayName="ADDR_L_TO",
            name="ADDR_L_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param4 = arcpy.Parameter(
            displayName="ADDR_R_FR",
            name="ADDR_R_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param5 = arcpy.Parameter(
            displayName="ADDR_R_TO",
            name="ADDR_R_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param6 = arcpy.Parameter(
            displayName="ZIPCODE_L",
            name="ZIPCODE_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param7 = arcpy.Parameter(
            displayName="ZIPCODE_R",
            name="ZIPCODE_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param8 = arcpy.Parameter(
            displayName="ZIPNAME_L",
            name="ZIPNAME_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param9 = arcpy.Parameter(
            displayName="ZIPNAME_R",
            name="ZIPNAME_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param10 = arcpy.Parameter(
            displayName="MUNI_ID_L",
            name="MUNI_ID_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param11 = arcpy.Parameter(
            displayName="MUNI_ID_R",
            name="MUNI_ID_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param12 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_FR",
            name="ELEV_TYPE_ID_FR",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param12.filter.type = "ValueList"
        param12.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        #param12.value = "At Grade"

        #
        param13 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_TO",
            name="ELEV_TYPE_ID_TO",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param13.filter.type = "ValueList"
        param13.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        #param13.value = "At Grade"

        #
        param14 = arcpy.Parameter(
            displayName="ACC_TYPE_ID",
            name="ACC_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param14.filter.type = "ValueList"
        param14.filter.list = ["Non-Restricted", "Restricted", "Unknown"]
        #param14.value = "Non-Restricted"

        #
        param15 = arcpy.Parameter(
            displayName="SURF_TYPE_ID",
            name="SURF_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param15.filter.type = "ValueList"
        param15.filter.list = ["Improved", "Unimproved", "Unknown"]
        #param15.value = "Improved"

        #
        param16 = arcpy.Parameter(
            displayName="STATUS_TYPE_ID",
            name="STATUS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param16.filter.type = "ValueList"
        param16.filter.list = ["Active", "Planned", "Under Construction"]
        #param16.value = "Active"

        #
        param17 = arcpy.Parameter(
            displayName="SYMBOL_TYPE_ID",
            name="SYMBOL_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param17.filter.type = "ValueList"
        param17.filter.list = ["Highway Authority Route", "Highway Authority Ramp", "Interstate", "Insterstate Ramp", "US Highway", "US Highway Ramp", "State Highway", "State Highway Ramp", "County 500 Route", "County 500 Ramp", "Other County Route", "Other County Ramp", "Local Road", "Local Ramp", "Alley"]
        #param17.value = "Local Road"

        #
        param18 = arcpy.Parameter(
            displayName="TRAVEL_DIR_TYPE_ID",
            name="TRAVEL_DIR_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param18.filter.type = "ValueList"
        param18.filter.list = ["Both", "Decreasing", "Increasing"]
        #param18.value = "Both"

        #
        param19 = arcpy.Parameter(
            displayName="JURIS_TYPE_ID",
            name="JURIS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param19.filter.type = "ValueList"
        param19.filter.list = ["Public", "Private", "Unknown"]
        #param19.value = "Private"

        #
        param20 = arcpy.Parameter(
            displayName="OIT_REV_TYPE_ID",
            name="OIT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param20.filter.type = "ValueList"
        param20.filter.list = ["Draft", "Final", "Incoming"]
        #param20.value = "Draft"

        #
        param21 = arcpy.Parameter(
            displayName="DOT_REV_TYPE_ID",
            name="DOT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param21.filter.type = "ValueList"
        param21.filter.list = ["Draft", "Final", "Incoming"]
        #param21.value = "Draft"

        #-----------------------------------------------------------------------
        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10,param11,param12,param13,param14,param15,param16,param17,param18,param19,param20,param21]
        return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # ----------------------------------------------------------------------
        # Define globals
        global split_left_interp, split_right_interp, split_elevation, currentG, bis_start_end, addintmess

        # ----------------------------------------------------------------------
        # GET THE SEGMENT THAT IS CURRENTLY SELECTED
        import arcpy, os, sys, pickle
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        with arcpy.da.SearchCursor(segmentfc, "*") as cursor:  # insert a cursor to access fields, print names
            for row in cursor:
                segmentrow = row

        currentglobal = segmentrow[26]

        gg = arcpy.env.scratchWorkspace + "\\global1global2.p"
        if os.path.exists(gg):
            with open(gg,'rb') as open3:
                global1global2 = pickle.load(open3)

        if currentglobal == global1global2['global1']:
            currentG = 1
        elif currentglobal == global1global2['global2']:
            currentG = 2

        parameters[0].value = segmentrow[1]
        parameters[1].value = segmentrow[3]

        ########################################################################
        ## INTERPOLATE ADDRESSES

        addintmess = {'even': None, 'odd': None, 'result': 'na', 'message': 'na', 'primename': False, 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}

        if segmentrow[3]: # if there is a prime name. If not, there is no geocode anyway
            addintmess['primename'] = True
            def is_even(num):
                return num % 2 == 0
            if (segmentrow[4] and segmentrow[5]): # if there are values on the left side
                if is_even(segmentrow[4]) and is_even(segmentrow[5]):
                    addintmess['even'] = 'left'
                elif not is_even(segmentrow[4]) and not is_even(segmentrow[5]):
                    addintmess['odd'] = 'left'

            if (segmentrow[6] and segmentrow[7]):
                if is_even(segmentrow[6]) and is_even(segmentrow[7]):
                    addintmess['even'] = 'right'
                elif not is_even(segmentrow[6]) and not is_even(segmentrow[7]):
                    addintmess['odd'] = 'right'

            if addintmess['even'] and (addintmess['even'] == addintmess['odd']): # if theres a value in one and they are equal
                addintmess['result'] = 'fail'
                addintmess['message'] = 'addresses on either side are both odd or both even'

            if (addintmess['odd'] or addintmess['even']) and addintmess['result'] == 'na': # we have a left and a right and they arent both odd or even

                # get the geometry (in dictionary json format) for both segments
                splitpath3 = arcpy.env.scratchWorkspace + "\\splitgeometries.p"
                if os.path.exists(splitpath3):
                    with open(splitpath3,'rb') as splitopen3:
                        ge1, ge2 = pickle.load(splitopen3)

                # now we have both geometries. Get the bisector points on either side of the split
                bisector = erebus.bisect_points(ge1, ge2, droplength = 10, plot = False)
                print 'bisector', bisector
                gc = erebus.Geocode('http://geodata.state.nj.us/arcgis/rest/services/Tasks/Addr_NJ_road/GeocodeServer')
                # reverse geocode the first side of the road
                rgcside1 = gc.reverse_geocode(bisector['bisect_x1'], bisector['bisect_y1'], f = 'pjson', distance = 10)
                rgcside2 = gc.reverse_geocode(bisector['bisect_x2'], bisector['bisect_y2'], f = 'pjson', distance = 10)
                print 'geocode1', rgcside1
                print 'geocode2', rgcside2

                # which segment are we working on?
                if currentG == 1:
                    bis_start_end = bisector['splitstartend 1']
                if currentG == 2:
                    bis_start_end = bisector['splitstartend 2']

                print 'result1', rgcside1['result']
                print 'result2', rgcside2['result']
                print 'bis_start_end', bis_start_end

                # First Geocode
                if rgcside1['result'] == 'success':
                    print 'trap1'
                    if is_even(int(rgcside1['address number'])): # drop point 1 is even
                        print 'trap2'
                        if addintmess['even'] == 'left':
                            print 'trap3'
                            if int(rgcside1['address number']) <= max(segmentrow[4], segmentrow[5]) and int(rgcside1['address number']) >= min(segmentrow[4], segmentrow[5]): # if the geocoded address is within the range of the left side of the road
                                # now the geocoded address should match the FR or the TO
                                if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                    print 'trap4'
                                    if not parameters[2].altered:
                                        print 'trap5'
                                        parameters[2].value = int(rgcside1['address number'])
                                        parameters[3].value = segmentrow[5]
                                        addintmess['addrlfr'] = True
                                if bis_start_end == 'end': # if this is the end of guid1, the reassign left TO
                                    print 'trap6'
                                    if not parameters[3].altered:
                                        print 'trap7'
                                        # descending or ascending?
                                        if segmentrow[4] - int(rgcside1['address number']) < 0: # ascending
                                            parameters[3].value = int(rgcside1['address number']) -2
                                        elif segmentrow[4] - int(rgcside1['address number']) > 0: # descending
                                            parameters[3].value = int(rgcside1['address number']) + 2
                                        else:
                                            parameters[3].value = int(rgcside1['address number'])
                                        parameters[2].value = segmentrow[4]
                                        addintmess['addrlto'] = True

                        if addintmess['even'] == 'right':
                            print 'trap8'
                            if int(rgcside1['address number']) <= max(segmentrow[6], segmentrow[7]) and int(rgcside1['address number']) >= min(segmentrow[6], segmentrow[7]): # if the geocoded address is within the range of the left side of the road
                                print 'trap9'
                                if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                    print 'trap10'
                                    if not parameters[4].altered:
                                        print 'trap11'
                                        parameters[4].value = int(rgcside1['address number'])
                                        parameters[5].value = segmentrow[7]
                                        addintmess['addrrfr'] = True
                                if bis_start_end == 'end': # if this is the end of guid1, the reassign left TO
                                    print 'trap12'
                                    if not parameters[5].altered:
                                        print 'trap13'
                                         # descending or ascending?
                                        if segmentrow[6] - int(rgcside1['address number']) < 0: # ascending
                                            parameters[5].value = int(rgcside1['address number']) - 2
                                        elif segmentrow[6] - int(rgcside1['address number']) > 0: # descending
                                            parameters[5].value = int(rgcside1['address number']) + 2
                                        else:
                                            parameters[5].value = int(rgcside1['address number'])
                                        parameters[4].value = segmentrow[6]
                                        addintmess['addrrto'] = True

                # Second Geocode
                if rgcside2['result'] == 'success':
                    if is_even(int(rgcside2['address number'])) == False: # drop point 2 is odd
                        if addintmess['odd'] == 'left':
                            if int(rgcside2['address number']) <= max(segmentrow[4], segmentrow[5]) and int(rgcside2['address number']) >= min(segmentrow[4], segmentrow[5]): # if the geocoded address is within the range of the left side of the road
                                # now the geocoded address should match the FR or the TO
                                if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                    if not parameters[2].altered:
                                        parameters[2].value = int(rgcside2['address number'])
                                        parameters[3].value = segmentrow[5]
                                        addintmess['addrlfr'] = True
                                if bis_start_end == 'end': # if this is the start of guid1, the reassign left TO
                                    if not parameters[3].altered:
                                        # descending or ascending?
                                        if segmentrow[4] - int(rgcside2['address number']) < 0: # ascending
                                            parameters[3].value = int(rgcside2['address number']) -2
                                        elif segmentrow[4] - int(rgcside1['address number']) > 0: # descending
                                            parameters[3].value = int(rgcside2['address number']) + 2
                                        else:
                                            parameters[3].value = int(rgcside2['address number'])
                                        parameters[2].value = segmentrow[4]
                                        addintmess['addrlto'] = True

                        if addintmess['odd'] == 'right':
                            if int(rgcside2['address number']) <= max(segmentrow[6], segmentrow[7]) and int(rgcside2['address number']) >= min(segmentrow[6], segmentrow[7]): # if the geocoded address is within the range of the left side of the road
                                if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                    if not parameters[4].altered:
                                        parameters[4].value = int(rgcside2['address number'])
                                        parameters[5].value = segmentrow[7]
                                        addintmess['addrrfr'] = True
                                if bis_start_end == 'end': # if this is the start of guid1, the reassign left TO
                                    if not parameters[5].altered:

                                         # descending or ascending?
                                        if segmentrow[6] - int(rgcside2['address number']) < 0: # ascending
                                            parameters[5].value = int(rgcside2['address number']) - 2
                                        elif segmentrow[6] - int(rgcside2['address number']) > 0: # descending
                                            parameters[5].value = int(rgcside2['address number']) + 2
                                        else:
                                            parameters[5].value = int(rgcside2['address number'])
                                        parameters[4].value = segmentrow[6]
                                        addintmess['addrrto'] = True

        if not parameters[2].altered and addintmess['addrlfr'] == False:
            parameters[2].value = segmentrow[4]
        if not parameters[3].altered and addintmess['addrlto'] == False:
            parameters[3].value = segmentrow[5]
        if not parameters[4].altered and addintmess['addrrfr'] == False:
            parameters[4].value = segmentrow[6]
        if not parameters[5].altered and addintmess['addrrto'] == False:
            parameters[5].value = segmentrow[7]



##{'json': {u'location': {u'y': 491765.18603470136, u'x': 605979.1088344229, u'spatialReference': {u'wkid': 102711, u'latestWkid': 3424}}, u'address': {u'City': u'BELMAR', u'State': u'NJ', u'Street': u'2098 Pilgrim Rd', u'ZIP': u'07719'}}, 'location': {u'y': 491765.18603470136, u'x': 605979.1088344229, u'spatialReference': {u'wkid': 102711, u'latestWkid': 3424}}, 'address number': u'2098', 'result': 'na', 'address': {u'City': u'BELMAR', u'State': u'NJ', u'Street': u'2098 Pilgrim Rd', u'ZIP': u'07719'}}

        ########################################################################

        for i in range(6,11):
            if segmentrow[i+2]:
                if not parameters[i].altered:
                    parameters[i].value = segmentrow[i+2]

        if segmentrow[13]:
            if not parameters[11].altered:
                parameters[11].value = segmentrow[13]


        ########################################################################
        ### Elevation Validation

        if not parameters[12].altered and not parameters[13].altered:

            splitpath3 = arcpy.env.scratchWorkspace + "\\splitgeometries.p"
            if os.path.exists(splitpath3):
                with open(splitpath3,'rb') as splitopen3:
                    ge1, ge2 = pickle.load(splitopen3)

            # now we have both geometries. Get the bisector points on either side of the split
            bisector = erebus.bisect_points(ge1, ge2, droplength = 10, plot = False)
            # which segment are we working on?
            if currentG == 1:
                bis_start_end = bisector['splitstartend 1']
            if currentG == 2:
                bis_start_end = bisector['splitstartend 2']


            elevdict = {0: 'At Grade', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3'}
            if currentG == 1:
                if bis_start_end == 'end':
                    parameters[12].value = elevdict[segmentrow[14]]
                if bis_start_end == 'start':
                    parameters[13].value = elevdict[segmentrow[15]]
            if currentG == 2:
                if bis_start_end == 'end':
                    parameters[12].value = elevdict[segmentrow[14]]
                if bis_start_end == 'start':
                    parameters[13].value = elevdict[segmentrow[15]]

        if segmentrow[16]:
            if not parameters[14].altered:
                if segmentrow[16] == 'N':
                    parameters[14].value = 'Non-Restricted'
                if segmentrow[16] == 'R':
                    parameters[14].value = 'Restricted'
                if segmentrow[16] == 'UNK':
                    parameters[14].value = 'Unknown'
        if segmentrow[17]:
            if not parameters[15].altered:
                if segmentrow[17] == 'I':
                    parameters[15].value = 'Improved'
                if segmentrow[17] == 'U':
                    parameters[15].value = 'Unimproved'
                if segmentrow[17] == 'UNK':
                    parameters[15].value = 'Unknown'
        if segmentrow[18]:
            if not parameters[16].altered:
                if segmentrow[18] == 'A':
                    parameters[16].value = 'Active'
                if segmentrow[18] == 'P':
                    parameters[16].value = 'Planned'
                if segmentrow[18] == 'U':
                    parameters[16].value = 'Under Construction'
        if segmentrow[19]:
            if not parameters[17].altered:
                symboltypedict = {100: "Highway Authority Route", 108: "Highway Authority Ramp", 200: "Interstate", 208: "Insterstate Ramp", 300: "US Highway", 308: "US Highway Ramp", 400: "State Highway", 408: "State Highway Ramp", 500: "County 500 Route", 508: "County 500 Ramp", 600: "Other County Route", 608: "Other County Ramp", 700: "Local Road", 708: "Local Ramp", 900: "Alley"}
                parameters[17].value = symboltypedict[int(segmentrow[19])]
        if segmentrow[20]:
            if not parameters[18].altered:
                if segmentrow[20] == 'B':
                    parameters[18].value = 'Both'
                if segmentrow[20] == 'D':
                    parameters[18].value = 'Decreasing'
                if segmentrow[20] == 'I':
                    parameters[18].value = 'Increasing'
        if segmentrow[21]:
            if not parameters[19].altered:
                if segmentrow[21] == 'PUB':
                    parameters[19].value = 'Public'
                if segmentrow[21] == 'PRI':
                    parameters[19].value = 'Private'
                if segmentrow[21] == 'UNK':
                    parameters[19].value = 'Unknown'
        if segmentrow[22]:
            if not parameters[20].altered:
                if segmentrow[22] == 'D':
                    parameters[20].value = 'Draft'
                if segmentrow[22] == 'F':
                    parameters[20].value = 'Final'
                if segmentrow[22] == 'I':
                    parameters[20].value = 'Incoming'
        if segmentrow[23]:
            if not parameters[21].altered:
                if segmentrow[23] == 'D':
                    parameters[21].value = 'Draft'
                if segmentrow[23] == 'F':
                    parameters[21].value = 'Final'
                if segmentrow[23] == 'I':
                    parameters[21].value = 'Incoming'


        return

    def updateMessages(self, parameters):

        global currentG, bis_start_end, addintmess

        ########################################################################
        ## Address Validation
        #addintmess = {'even': None, 'odd': None, 'result': 'na', 'message': 'na', 'primename': False, 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}

        if not addintmess['addrlfr'] and not addintmess['addrlto'] and parameters[2].value and parameters[3].value and not parameters[2].altered and not parameters[3].altered:
            parameters[2].setWarningMessage('This value has NOT been interpolated. Please check to make sure this address is valid')
            parameters[3].setWarningMessage('This value has NOT been interpolated. Please check to make sure this address is valid')
        if not addintmess['addrrfr'] and not addintmess['addrrto'] and parameters[4].value and parameters[5].value and not parameters[4].altered and not parameters[5].altered:
            parameters[4].setWarningMessage('This value has NOT been interpolated. Please check to make sure this address is valid')
            parameters[5].setWarningMessage('This value has NOT been interpolated. Please check to make sure this address is valid')
        ########################################################################
        ## Elevation Validation

        elevdict = {0: 'At Grade', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3'}
        if currentG == 1:
            if bis_start_end == 'end' and not parameters[13].altered:
                parameters[13].setWarningMessage('Please select a valid elevation type')
            if bis_start_end == 'start' and not parameters[12].altered:
                parameters[12].setWarningMessage('Please select a valid elevation type')
        if currentG == 2:
            if bis_start_end == 'end' and not parameters[13].altered:
                parameters[13].setWarningMessage('Please select a valid elevation type')
            if bis_start_end == 'start' and not parameters[12].altered:
                parameters[12].setWarningMessage('Please select a valid elevation type')

        if parameters[12].altered:
            parameters[12].clearMessage()
        if parameters[13].altered:
            parameters[13].clearMessage()

        return

    def execute(self, parameters, messages):
        import arcpy
        import pickle
        import os, sys
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        # Set up the segment dictionary
        des_seg = arcpy.Describe(segmentfc)
        des_seg_fields = des_seg.fields
        segfields = {}
        for field in des_seg_fields:
            segfields[str(field.name)] = ''

        with arcpy.da.SearchCursor(segmentfc, ["GLOBALID"]) as cursor:  # insert a cursor to access fields, print names
            for row in cursor:
                globalid = row[0]

##{'SHAPE.LEN': 28, 'ZIPNAME_R': 11, 'TRAVEL_DIR_TYPE_ID': 20, 'ADDR_R_FR': 6, 'SEG_ID': 1, 'ADDR_L_TO': 5, 'ZIPNAME_L': 10, 'JURIS_TYPE_ID': 21, 'OBJECTID': 0, 'DOT_REV_TYPE_ID': 23, 'SHAPE': 27, 'SYMBOL_TYPE_ID': 19, 'UPDATE_USER': 24, 'ACC_TYPE_ID': 16, 'ZIPCODE_L': 8, 'SURF_TYPE_ID': 17, 'MUNI_ID_L': 12, 'STATUS_TYPE_ID': 18, 'ELEV_TYPE_ID_TO': 15, 'UPDATEDATE': 25, 'ZIPCODE_R': 9, 'OIT_REV_TYPE_ID': 22, 'ELEV_TYPE_ID_FR': 14, 'PRIME_NAME': 3, 'SEG_GUID': 2, 'GLOBALID': 26, 'ADDR_L_FR': 4, 'MUNI_ID_R': 13, 'ADDR_R_TO': 7}


        ################################################################################
        ## ROAD.SEGMENT Parameters
        segfields['SEG_ID'] = parameters[0].valueAsText  # long integer
        segfields['PRIME_NAME'] = parameters[1].valueAsText # text
        if parameters[2].value:
            segfields['ADDR_L_FR'] = parameters[2].value # long integer
        if parameters[3].value:
            segfields['ADDR_L_TO'] = parameters[3].value # long integer
        if parameters[4].value:
            segfields['ADDR_R_FR'] = parameters[4].value # long integer
        if parameters[5].value:
            segfields['ADDR_R_TO'] = parameters[5].value  # long integer
        segfields['ZIPCODE_L'] = parameters[6].valueAsText # text
        segfields['ZIPCODE_R'] = parameters[7].valueAsText # text
        segfields['ZIPNAME_L'] = parameters[8].valueAsText # text
        segfields['ZIPNAME_R'] = parameters[9].valueAsText # text
        segfields['MUNI_ID_L'] = parameters[10].valueAsText # text
        segfields['MUNI_ID_R'] = parameters[11].valueAsText # text


        if parameters[12].valueAsText == 'At Grade': # input is string, long integer
            segfields['ELEV_TYPE_ID_FR'] = 0
        elif parameters[12].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_FR'] = 1
        elif parameters[12].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_FR'] = 2
        elif parameters[12].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_FR'] = 3
        else:
            pass

        if parameters[13].valueAsText == 'At Grade': # input is string, long integer
            segfields['ELEV_TYPE_ID_TO'] = 0
        elif parameters[13].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_TO'] = 1
        elif parameters[13].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_TO'] = 2
        elif parameters[13].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_TO'] = 3
        else:
            pass

        if parameters[14].valueAsText == 'Non-Restricted': #text
            segfields['ACC_TYPE_ID'] = 'N'
        elif parameters[14].valueAsText == 'Restricted':
            segfields['ACC_TYPE_ID'] = 'R'
        elif parameters[14].valueAsText == 'Unknown':
            segfields['ACC_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[15].valueAsText == 'Improved': #text
            segfields['SURF_TYPE_ID'] = 'I'
        elif parameters[15].valueAsText == 'Unimproved':
            segfields['SURF_TYPE_ID'] = 'U'
        elif parameters[15].valueAsText == 'Unknown':
            segfields['SURF_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[16].valueAsText == 'Active': #text
            segfields['STATUS_TYPE_ID'] = 'A'
        elif parameters[16].valueAsText == 'Planned':
            segfields['STATUS_TYPE_ID'] = 'P'
        elif parameters[16].valueAsText == 'Under Construction':
            segfields['STATUS_TYPE_ID'] = 'U'
        else:
            pass

        if parameters[17].valueAsText == 'Highway Authority Route': # input is string, short integer
            segfields['SYMBOL_TYPE_ID'] = 100
        elif parameters[17].valueAsText == 'Highway Authority Ramp':
            segfields['SYMBOL_TYPE_ID'] = 108
        elif parameters[17].valueAsText == 'Interstate':
            segfields['SYMBOL_TYPE_ID'] = 200
        elif parameters[17].valueAsText == 'Interstate Ramp':
            segfields['SYMBOL_TYPE_ID'] = 208
        elif parameters[17].valueAsText == 'US Highway':
            segfields['SYMBOL_TYPE_ID'] = 300
        elif parameters[17].valueAsText == 'US Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 308
        elif parameters[17].valueAsText == 'State Highway':
            segfields['SYMBOL_TYPE_ID'] = 400
        elif parameters[17].valueAsText == 'State Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 408
        elif parameters[17].valueAsText == 'County 500 Route':
            segfields['SYMBOL_TYPE_ID'] = 500
        elif parameters[17].valueAsText == 'County 500 Ramp':
            segfields['SYMBOL_TYPE_ID'] = 508
        elif parameters[17].valueAsText == 'Other County Route':
            segfields['SYMBOL_TYPE_ID'] = 600
        elif parameters[17].valueAsText == 'Other County Ramp':
            segfields['SYMBOL_TYPE_ID'] = 608
        elif parameters[17].valueAsText == 'Local Road':
            segfields['SYMBOL_TYPE_ID'] = 700
        elif parameters[17].valueAsText == 'Alley':
            segfields['SYMBOL_TYPE_ID'] = 900
        else:
            pass

        if parameters[18].valueAsText == 'Both': #text
            segfields['TRAVEL_DIR_TYPE_ID'] = 'B'
        elif parameters[18].valueAsText == 'Decreasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'D'
        elif parameters[18].valueAsText == 'Increasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'I'
        else:
            pass

        islinref = False
        if parameters[19].valueAsText == 'Public': #text
            segfields['JURIS_TYPE_ID'] = 'PUB'
            islinref = True
        elif parameters[19].valueAsText == 'Private' or parameters[19].valueAsText == 'Private (with linear referencing)':
            segfields['JURIS_TYPE_ID'] = 'PRI'
        elif parameters[19].valueAsText == 'Private (with linear referencing)':
            islinref = True
        elif parameters[19].valueAsText == 'Unknown':
            segfields['JURIS_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[20].valueAsText == 'Draft': #text
            segfields['OIT_REV_TYPE_ID'] = 'D'
        elif parameters[20].valueAsText == 'Final':
            segfields['OIT_REV_TYPE_ID'] = 'F'
        elif parameters[20].valueAsText == 'Incoming':
            segfields['OIT_REV_TYPE_ID'] = 'I'
        else:
            pass

        if parameters[21].valueAsText == 'Draft': #text
            segfields['DOT_REV_TYPE_ID'] = 'D'
        elif parameters[21].valueAsText == 'Final':
            segfields['DOT_REV_TYPE_ID'] = 'F'
        elif parameters[21].valueAsText == 'Incoming':
            segfields['DOT_REV_TYPE_ID'] = 'I'
        else:
            pass

        segfields['GLOBALID'] = globalid

        splitpath = arcpy.env.scratchWorkspace + "\\splitinput.p"
        with open(splitpath, 'wb') as output:
            pickle.dump(segfields, output, -1)

        arcpy.AddMessage('\n\n----------------------------------------------------\nVariable inputs for this segment of the split were successful.\n----------------------------------------------------\n ')


        return

# END SplitSegment
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
MergeAltered = [False]*4
class Merge(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Merge"
        self.description = "Merge features"
        self.canRunInBackground = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
        global USER, Domains
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="SEG_ID",
            name="SEG_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param0.enabled = False

        #
        param1 = arcpy.Parameter(
            displayName="PRIME_NAME",
            name="PRIME_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param1.enabled = False

        #
        param2 = arcpy.Parameter(
            displayName="ADDR_L_FR",
            name="ADDR_L_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param3 = arcpy.Parameter(
            displayName="ADDR_L_TO",
            name="ADDR_L_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param4 = arcpy.Parameter(
            displayName="ADDR_R_FR",
            name="ADDR_R_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param5 = arcpy.Parameter(
            displayName="ADDR_R_TO",
            name="ADDR_R_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param6 = arcpy.Parameter(
            displayName="ZIPCODE_L",
            name="ZIPCODE_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param7 = arcpy.Parameter(
            displayName="ZIPCODE_R",
            name="ZIPCODE_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param8 = arcpy.Parameter(
            displayName="ZIPNAME_L",
            name="ZIPNAME_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param9 = arcpy.Parameter(
            displayName="ZIPNAME_R",
            name="ZIPNAME_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        gnis = Domains['GNIS_NAME'].values()
        gnis2 = sorted(gnis, key = lambda item: item.split(',')[1] + item.split(',')[0])


        #
        param10 = arcpy.Parameter(
            displayName="MUNI_ID_L",
            name="MUNI_ID_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param10.filter.type = "ValueList"
        param10.filter.list = gnis2

        #
        param11 = arcpy.Parameter(
            displayName="MUNI_ID_R",
            name="MUNI_ID_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param11.filter.type = "ValueList"
        param11.filter.list = gnis2

        #
        param12 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_FR",
            name="ELEV_TYPE_ID_FR",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param12.filter.type = "ValueList"
        param12.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        #param12.value = "At Grade"

        #
        param13 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_TO",
            name="ELEV_TYPE_ID_TO",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param13.filter.type = "ValueList"
        param13.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        #param13.value = "At Grade"

        #
        param14 = arcpy.Parameter(
            displayName="ACC_TYPE_ID",
            name="ACC_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param14.filter.type = "ValueList"
        param14.filter.list = ["Non-Restricted", "Restricted", "Unknown"]
        #param14.value = "Non-Restricted"

        #
        param15 = arcpy.Parameter(
            displayName="SURF_TYPE_ID",
            name="SURF_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param15.filter.type = "ValueList"
        param15.filter.list = ["Improved", "Unimproved", "Unknown"]
        #param15.value = "Improved"

        #
        param16 = arcpy.Parameter(
            displayName="STATUS_TYPE_ID",
            name="STATUS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param16.filter.type = "ValueList"
        param16.filter.list = ["Active", "Planned", "Under Construction"]
        #param16.value = "Active"

        #
        param17 = arcpy.Parameter(
            displayName="SYMBOL_TYPE_ID",
            name="SYMBOL_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param17.filter.type = "ValueList"
        param17.filter.list = ["Highway Authority Route", "Highway Authority Ramp", "Interstate", "Insterstate Ramp", "US Highway", "US Highway Ramp", "State Highway", "State Highway Ramp", "County 500 Route", "County 500 Ramp", "Other County Route", "Other County Ramp", "Local Road", "Local Ramp", "Alley"]
        #param17.value = "Local Road"

        #
        param18 = arcpy.Parameter(
            displayName="TRAVEL_DIR_TYPE_ID",
            name="TRAVEL_DIR_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param18.filter.type = "ValueList"
        param18.filter.list = ["Both", "Decreasing", "Increasing"]
        #param18.value = "Both"

        #
        param19 = arcpy.Parameter(
            displayName="JURIS_TYPE_ID",
            name="JURIS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param19.filter.type = "ValueList"
        param19.filter.list = ["Public", "Private", "Unknown"]
        #param19.value = "Private"

        #
        param20 = arcpy.Parameter(
            displayName="OIT_REV_TYPE_ID",
            name="OIT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param20.filter.type = "ValueList"
        param20.filter.list = ["Draft", "Final", "Incoming"]
        #param20.value = "Draft"

        #
        param21 = arcpy.Parameter(
            displayName="DOT_REV_TYPE_ID",
            name="DOT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param21.filter.type = "ValueList"
        param21.filter.list = ["Draft", "Final", "Incoming"]
        #param21.value = "Draft"

        param22 = arcpy.Parameter(
            displayName="Update LINEAR_REF MILEPOST_FR and MILEPOST_TO values (if applicable)",
            name="update milepost",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param22.value = True

        #-----------------------------------------------------------------------
        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10,param11,param12,param13,param14,param15,param16,param17,param18,param19,param20,param21,param22]
        return params


    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        import json, arcpy
        global USER, MergeAltered
        # ----------------------------------------------------------------------
        # Define globals
        global merge_left_interp, merge_right_interp

        # Construct the DOMAIN Dictionaries
        domains = arcpy.da.ListDomains(arcpy.env.workspace)
        Domains = {}
        for domain in domains:
            Domains[domain.name] = domain.codedValues    #SYMBOL_TYPE JURIS_TYPE ELEV_TYPE CHANGE_TYPE REVIEW_TYPE STATUS_TYPE TRAVEL_DIR_TYPE DATA_SOURCE_TYPE SHIELD_TYPE ACCESS_TYPE SHIELD_SUBTYPE SEGMENT_TYPE NAME_TYPE SURFACE_TYPE GNIS_NAME LRS_TYPE


        # ----------------------------------------------------------------------
        # GET THE SEGMENT THAT IS CURRENTLY SELECTED
        import arcpy, os, sys, pickle, json
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        ########################################################################
        ## Figure out which one is merged to
        splitpath = arcpy.env.scratchWorkspace + "\\mergeselection_multiple.p"
        if os.path.exists(splitpath):
            with open(splitpath,'rb') as splitopen:
                lastselect_multiple, segmentgeo_multiple, selectedfootprints_multiple = pickle.load(splitopen) # lastselect is a list of tuples, segmetngeo is a list of polyline geometries
        segmentgeo_multiple2 = []
        for g in segmentgeo_multiple:
            segmentgeo_multiple2.append(arcpy.FromWKT(g))
        segmentgeo_multiple = segmentgeo_multiple2          # now it is a list of polyline [<polyline>, <polyline>]

## lastselect example
##(625860, 447612, u'{0F279EE0-1708-11E3-B5F2-0062151309FF}', u'Corlies Ave', 2211, 2133, 2212, 2132, u'07753', u'07753', u'NEPTUNE', u'NEPTUNE', u'882111', u'885315', 0, 0, u'N', u'I', u'A', 400, u'B', u'PUB', u'F', u'F', u'OAXMITC', datetime.datetime(2013, 10, 4, 13, 43, 12), u'{0A1625A6-037A-4136-97D6-B43937E63A68}', (618802.6774114977, 500535.23189087445), 476.318553700763)

        try:
            ## Figure out which records need to be sent to trans, change, and deleted throughout the database
            ## After the merge is performed we have the two segments that were selected as lastselect_multiple, and the
            ## new segment (merged) is now selected with the same SEG_GUID. So, look through and compare. The SEG_GUID that is still
            ## there will be the one that was merged to. The other segment will have been deleted.
            ismergerlist = []
            for record in lastselect_multiple:
                seg_sql = erebus.sqlGUID("SEG_GUID", record[2])
                find = False
                with arcpy.da.SearchCursor(segmentfc, "*", seg_sql) as cursor:
                    for row in cursor:
                        ismergerlist.append(True)
                        find = True
                if find == False:
                    ismergerlist.append(False)

            newrow = []; delrows = []; newgeom = []; delgeom = []
            indind = 0
            for rec in ismergerlist:
                if rec == True:
                    newrow.append(lastselect_multiple[indind])  #***********
                    newgeom.append(segmentgeo_multiple[indind]) #***********
                if rec == False:
                    delrows.append(lastselect_multiple[indind]) #***********
                    delgeom.append(segmentgeo_multiple[indind]) #***********
                indind += 1
        except:
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass

        # convert the wkt to esrijson
        ej1 = erebus.wkt_to_esrijson(segmentgeo_multiple[0])
        if ej1['result'] == 'success':
            segmentgeo0 = ej1['esrijson']
        ej2 = erebus.wkt_to_esrijson(segmentgeo_multiple[1])
        if ej2['result'] == 'success':
            segmentgeo1 = ej2['esrijson']

        lastselect0 = lastselect_multiple[0]
        lastselect1 = lastselect_multiple[1]
        nrsql = erebus.sqlGUID("SEG_GUID",newrow[0][2])
        with arcpy.da.SearchCursor(segmentfc, "*", nrsql) as cursor:  # insert a cursor to access fields, print names
            for row in cursor:
                segmentrow = row
        parameters[0].value = segmentrow[1]
        parameters[1].value = segmentrow[3]
##        parameters[0].value = newrow[0]["SEGMENT"][0]["SEG_ID"]
##        parameters[1].value = newrow[0]["SEGMENT"][0]["PRIME_NAME"]

        ######################################################################
        ## INTERPOLATE ADDRESSES
        ######################################################################
        addintmess = {'result': 'na', 'message': 'na', 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}

        if segmentrow[4] and segmentrow[5] and delrows[0][4] and delrows[0][5] and not MergeAltered[0] and not MergeAltered[1]:

            new_l_dir = segmentrow[5] - segmentrow[4]
            del_l_dir = delrows[0][5] - delrows[0][4]

            # left side both increasing
            if new_l_dir > 0 and del_l_dir > 0:  # both increasing
                if segmentrow[4] > delrows[0][5]:  # newrow has the larger addresses
                    parameters[2].value = delrows[0][4]
                    parameters[3].value = segmentrow[5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True
                if segmentrow[4] < delrows[0][5]:  # newrow has the lesser addresses
                    parameters[2].value = segmentrow[4]
                    parameters[3].value = delrows[0][5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True

            # left side both decreasing
            if new_l_dir < 0 and del_l_dir < 0:  # both decreasing
                if segmentrow[4] < delrows[0][5]:  # newrow has the lesser addresses
                    parameters[2].value = delrows[0][4]
                    parameters[3].value = segmentrow[5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True
                if segmentrow[4] > delrows[0][5]:  # newrow has the larger addresses
                    parameters[2].value = segmentrow[4]
                    parameters[3].value = delrows[0][5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True

        if segmentrow[6] and segmentrow[7] and delrows[0][6] and delrows[0][7] and not MergeAltered[2] and not MergeAltered[3]:

            new_r_dir = segmentrow[7] - segmentrow[6]
            del_r_dir = delrows[0][7] - delrows[0][6]

            # right side both increasing
            if new_r_dir > 0 and del_r_dir > 0:  # both increasing
                if segmentrow[6] > delrows[0][7]:  # newrow has the larger addresses
                    parameters[4].value = delrows[0][6]
                    parameters[5].value = segmentrow[7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True
                if segmentrow[6] < delrows[0][7]:  # newrow has the lesser addresses
                    parameters[4].value = segmentrow[6]
                    parameters[5].value = delrows[0][7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True

            # right side both decreasing
            if new_r_dir < 0 and del_r_dir < 0:  # both decreasing
                if segmentrow[6] < delrows[0][7]:  # newrow has the lesser addresses
                    parameters[4].value = delrows[0][6]
                    parameters[5].value = segmentrow[7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True
                if segmentrow[6] > delrows[0][7]:  # newrow has the greater addresses
                    parameters[4].value = segmentrow[6]
                    parameters[5].value = delrows[0][7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True

        if not parameters[2].altered and not addintmess['addrlfr'] and parameters[2].value and not MergeAltered[0]:
            if segmentrow[4]:
                parameters[2].value = segmentrow[4]
                MergeAltered[0] = True
        if not parameters[3].altered and not addintmess['addrlto'] and parameters[3].value and not MergeAltered[1]:
            if segmentrow[5]:
                parameters[3].value = segmentrow[5]
                MergeAltered[1] = True
        if not parameters[4].altered and not addintmess['addrrfr'] and parameters[4].value and not MergeAltered[2]:
            if segmentrow[6]:
                parameters[4].value = segmentrow[6]
                MergeAltered[2] = True
        if not parameters[5].altered and not addintmess['addrrto'] and parameters[5].value and not MergeAltered[3]:
            if segmentrow[7]:
                parameters[5].value = segmentrow[7]
                MergeAltered[3] = True
##{'json': {u'location': {u'y': 491765.18603470136, u'x': 605979.1088344229, u'spatialReference': {u'wkid': 102711, u'latestWkid': 3424}}, u'address': {u'City': u'BELMAR', u'State': u'NJ', u'Street': u'2098 Pilgrim Rd', u'ZIP': u'07719'}}, 'location': {u'y': 491765.18603470136, u'x': 605979.1088344229, u'spatialReference': {u'wkid': 102711, u'latestWkid': 3424}}, 'address number': u'2098', 'result': 'na', 'address': {u'City': u'BELMAR', u'State': u'NJ', u'Street': u'2098 Pilgrim Rd', u'ZIP': u'07719'}}
## lastselect example
##(625860, 447612, u'{0F279EE0-1708-11E3-B5F2-0062151309FF}', u'Corlies Ave', 2211, 2133, 2212, 2132, u'07753', u'07753', u'NEPTUNE', u'NEPTUNE', u'882111', u'885315', 0, 0, u'N', u'I', u'A', 400, u'B', u'PUB', u'F', u'F', u'OAXMITC', datetime.datetime(2013, 10, 4, 13, 43, 12), u'{0A1625A6-037A-4136-97D6-B43937E63A68}', (618802.6774114977, 500535.23189087445), 476.318553700763)
        ######################################################################
        for i in range(6,10):
            if segmentrow[i+2]:
                if not parameters[i].altered:
                    parameters[i].value = segmentrow[i+2]
        if segmentrow[12]:
            if not parameters[10].altered:
                for key,value in Domains['GNIS_NAME'].iteritems():
                    if key == segmentrow[12]:
                        parameters[10].value = value
        if segmentrow[13]:
            if not parameters[11].altered:
                for key,value in Domains['GNIS_NAME'].iteritems():
                    if key == segmentrow[13]:
                        parameters[11].value = value

        ######################################################################
        ## INTERPOLATE ELEVATION
        ######################################################################
        global merge_elevation
        if not parameters[12].altered and not parameters[13].altered and ej1['result'] == 'success' and ej2['result'] == 'success':
            if 'curvePaths' in segmentgeo0.keys():
                # format for true curves
                xym1 = []; xym2 = [];
                for i in segmentgeo0['curvePaths'][0]:
                    if type(i) is list:
                        xym1.append(i)
                    elif type(i) is dict:
                        xym1.append(i['c'][0])
                for i in segmentgeo1['curvePaths'][0]:
                    if type(i) is list:
                        xym2.append(i)
                    elif type(i) is dict:
                        xym2.append(i['c'][0])
            elif 'paths' in segmentgeo0.keys():
                #format for no true curves
                xym1 = segmentgeo0['paths'][0] # list of lists. each list has [x,y,m]
                xym2 = segmentgeo1['paths'][0]

            fr0 = xym1[0][0:2]  # x and y list of segment 0 from (i.e. start), [619573.7800000012, 501185.0200000033]
            to0 = xym1[-1][0:2]
            fr1 = xym2[0][0:2]  # x and y list of segment 1 from (i.e. start), [619573.7800000012, 501185.0200000033]
            to1 = xym2[-1][0:2]

            fr0E = lastselect0[14] # from elevation segment0
            to0E = lastselect0[15]
            fr1E = lastselect1[14]
            to1E = lastselect1[15]

            elevdict = {0: 'At Grade', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3'}
            ## Order the coordinates and segments so that we know which ends are touching and which ends are terminal.

            # is the order 0 to 1?
            import math
            dist_to0_fr1 = math.sqrt((to0[0] - fr1[0])**2 + (to0[1] - fr1[1])**2)
            dist_fr0_to1 = math.sqrt((to1[0] - fr0[0])**2 + (to1[1] - fr0[1])**2)
            if dist_to0_fr1 < dist_fr0_to1:  # the order is 0 to 1
                # take care of errors first
                if fr0E == 0 and to0E == 1 and fr1E == 1 and to1E == 0: # error code 1
                    merge_elevation = 1
                elif fr0E == 1 and to0E == 1 and fr1E == 1 and to1E == 0: # error code 2
                    merge_elevation = 2
                elif fr0E == 0 and to0E == 1 and fr1E == 1 and to1E == 1: # error code 3
                    merge_elevation = 3
                else: # no errors, do the inerpolation
                        parameters[12].value = elevdict[fr0E]
                        parameters[13].value = elevdict[to1E]
                        merge_elevation = 0
            if dist_to0_fr1 > dist_fr0_to1:  # the order is 1 to 0
                # take care of errors first
                if fr0E == 1 and to0E == 0 and fr1E == 0 and to1E == 1: # error code 1
                    merge_elevation = 1
                elif fr0E == 1 and to0E == 0 and fr1E == 1 and to1E == 1: # error code 2
                    merge_elevation = 2
                elif fr0E == 1 and to0E == 1 and fr1E == 0 and to1E == 1: # error code 3
                    merge_elevation = 3
                else: # no errors, do the inerpolation
                        parameters[12].value = elevdict[fr1E]
                        parameters[13].value = elevdict[to0E]
                        merge_elevation = 0

        ######################################################################
        if segmentrow[16]:
            if not parameters[14].altered:
                if segmentrow[16] == 'N':
                    parameters[14].value = 'Non-Restricted'
                if segmentrow[16] == 'R':
                    parameters[14].value = 'Restricted'
                if segmentrow[16] == 'UNK':
                    parameters[14].value = 'Unknown'
        if segmentrow[17]:
            if not parameters[15].altered:
                if segmentrow[17] == 'I':
                    parameters[15].value = 'Improved'
                if segmentrow[17] == 'U':
                    parameters[15].value = 'Unimproved'
                if segmentrow[17] == 'UNK':
                    parameters[15].value = 'Unknown'
        if segmentrow[18]:
            if not parameters[16].altered:
                if segmentrow[18] == 'A':
                    parameters[16].value = 'Active'
                if segmentrow[18] == 'P':
                    parameters[16].value = 'Planned'
                if segmentrow[18] == 'U':
                    parameters[16].value = 'Under Construction'
        if segmentrow[19]:
            if not parameters[17].altered:
                symboltypedict = {100: "Highway Authority Route", 108: "Highway Authority Ramp", 200: "Interstate", 208: "Insterstate Ramp", 300: "US Highway", 308: "US Highway Ramp", 400: "State Highway", 408: "State Highway Ramp", 500: "County 500 Route", 508: "County 500 Ramp", 600: "Other County Route", 608: "Other County Ramp", 700: "Local Road", 708: "Local Ramp", 900: "Alley"}
                parameters[17].value = symboltypedict[int(segmentrow[19])]
        if segmentrow[20]:
            if not parameters[18].altered:
                if segmentrow[20] == 'B':
                    parameters[18].value = 'Both'
                if segmentrow[20] == 'D':
                    parameters[18].value = 'Decreasing'
                if segmentrow[20] == 'I':
                    parameters[18].value = 'Increasing'
        if segmentrow[21]:
            if not parameters[19].altered:
                if segmentrow[21] == 'PUB':
                    parameters[19].value = 'Public'
                if segmentrow[21] == 'PRI':
                    parameters[19].value = 'Private'
                if segmentrow[21] == 'UNK':
                    parameters[19].value = 'Unknown'
        if segmentrow[22]:
            if not parameters[20].altered:
                if USER in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                    usedict = {'NJ OIT': 'Final', 'NJ DOT': 'Draft', 'County': 'Incoming', 'Other': 'Draft'}
                    parameters[20].value = usedict[USER]
                else:
                    parameters[20].value = 'Draft'
        if segmentrow[23]:
            if not parameters[21].altered:
                if USER in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                    usedict = {'NJ OIT': 'Draft', 'NJ DOT': 'Final', 'County': 'Draft', 'Other': 'Draft'}
                    parameters[21].value = usedict[USER]
                else:
                    parameters[21].value = 'Draft'
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        global merge_left_interp, merge_right_interp, merge_elevation
        if not merge_left_interp:
            parameters[2].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
            parameters[3].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
        if not merge_right_interp:
            parameters[4].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
            parameters[5].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
        if merge_elevation == 99: # interpolation failed.
            parameters[12].setWarningMessage('Elevation interpolation failed, please choose a valid elevation type.')
            parameters[13].setWarningMessage('Elevation interpolation failed, please choose a valid elevation type.')
        if merge_elevation in (1,2,3): # interpolation failed.
            parameters[12].setWarningMessage('Elevation interpolation failed due to violation of Merge Rule #3, please choose a valid elevation type. ERROR Code: {0}. Is altered {1}'.format(merge_elevation,parameters[12].altered))
            parameters[13].setWarningMessage('Elevation interpolation failed due to violation of Merge Rule #3, please choose a valid elevation type. ERROR Code: {0}'.format(merge_elevation))
        if parameters[12].altered:
            parameters[12].clearMessage()
        if parameters[13].altered:
            parameters[13].clearMessage()

        # parameters[2].setWarningMessage('Altered: {0}'.format(parameters[2].altered))
        # parameters[3].setWarningMessage('Altered: {0}'.format(parameters[3].altered))


        return

    def execute(self, parameters, messages):
        """The source code of the Merge tool."""
        import sys, os, pickle, arcpy, traceback
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        set_tool_indicator(arcpy.env.scratchWorkspace, True)

        # Construct the DOMAIN Dictionaries
        domains = arcpy.da.ListDomains(arcpy.env.workspace)
        Domains = {}
        for domain in domains:
            Domains[domain.name] = domain.codedValues    #SYMBOL_TYPE JURIS_TYPE ELEV_TYPE CHANGE_TYPE REVIEW_TYPE STATUS_TYPE TRAVEL_DIR_TYPE DATA_SOURCE_TYPE SHIELD_TYPE ACCESS_TYPE SHIELD_SUBTYPE SEGMENT_TYPE NAME_TYPE SURFACE_TYPE GNIS_NAME LRS_TYPE
        # Set up the segment dictionary
        des_seg = arcpy.Describe(segmentfc)
        des_seg_fields = des_seg.fields
        segfields = {}
        for field in des_seg_fields:
            segfields[str(field.name)] = ''

        ################################################################################
        ## ROAD.SEGMENT Parameters
        segfields['SEG_ID'] = parameters[0].valueAsText  # long integer
        segfields['PRIME_NAME'] = parameters[1].valueAsText  # text
        segfields['ADDR_L_FR'] = parameters[2].value  # long integer
        segfields['ADDR_L_TO'] = parameters[3].value  # long integer
        segfields['ADDR_R_FR'] = parameters[4].value  # long integer
        segfields['ADDR_R_TO'] = parameters[5].value  # long integer
        segfields['ZIPCODE_L'] = parameters[6].valueAsText  # text
        segfields['ZIPCODE_R'] = parameters[7].valueAsText  # text
        segfields['ZIPNAME_L'] = parameters[8].valueAsText  # text
        segfields['ZIPNAME_R'] = parameters[9].valueAsText  # text

        if parameters[10].value:
            for key,value in Domains['GNIS_NAME'].iteritems():
                if value == parameters[10].value:
                    segfields['MUNI_ID_L'] = key
        if parameters[11].value:
            for key,value in Domains['GNIS_NAME'].iteritems():
                if value == parameters[11].value:
                    segfields['MUNI_ID_R'] = key
        if parameters[12].valueAsText == 'At Grade':  # input is string, long integer
            segfields['ELEV_TYPE_ID_FR'] = 0
        elif parameters[12].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_FR'] = 1
        elif parameters[12].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_FR'] = 2
        elif parameters[12].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_FR'] = 3
        else:
            pass

        if parameters[13].valueAsText == 'At Grade':  # input is string, long integer
            segfields['ELEV_TYPE_ID_TO'] = 0
        elif parameters[13].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_TO'] = 1
        elif parameters[13].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_TO'] = 2
        elif parameters[13].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_TO'] = 3
        else:
            pass

        if parameters[14].valueAsText == 'Non-Restricted':  #text
            segfields['ACC_TYPE_ID'] = 'N'
        elif parameters[14].valueAsText == 'Restricted':
            segfields['ACC_TYPE_ID'] = 'R'
        elif parameters[14].valueAsText == 'Unknown':
            segfields['ACC_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[15].valueAsText == 'Improved': #text
            segfields['SURF_TYPE_ID'] = 'I'
        elif parameters[15].valueAsText == 'Unimproved':
            segfields['SURF_TYPE_ID'] = 'U'
        elif parameters[15].valueAsText == 'Unknown':
            segfields['SURF_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[16].valueAsText == 'Active': #text
            segfields['STATUS_TYPE_ID'] = 'A'
        elif parameters[16].valueAsText == 'Planned':
            segfields['STATUS_TYPE_ID'] = 'P'
        elif parameters[16].valueAsText == 'Under Construction':
            segfields['STATUS_TYPE_ID'] = 'U'
        else:
            pass

        if parameters[17].valueAsText == 'Highway Authority Route': # input is string, short integer
            segfields['SYMBOL_TYPE_ID'] = 100
        elif parameters[17].valueAsText == 'Highway Authority Ramp':
            segfields['SYMBOL_TYPE_ID'] = 108
        elif parameters[17].valueAsText == 'Interstate':
            segfields['SYMBOL_TYPE_ID'] = 200
        elif parameters[17].valueAsText == 'Interstate Ramp':
            segfields['SYMBOL_TYPE_ID'] = 208
        elif parameters[17].valueAsText == 'US Highway':
            segfields['SYMBOL_TYPE_ID'] = 300
        elif parameters[17].valueAsText == 'US Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 308
        elif parameters[17].valueAsText == 'State Highway':
            segfields['SYMBOL_TYPE_ID'] = 400
        elif parameters[17].valueAsText == 'State Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 408
        elif parameters[17].valueAsText == 'County 500 Route':
            segfields['SYMBOL_TYPE_ID'] = 500
        elif parameters[17].valueAsText == 'County 500 Ramp':
            segfields['SYMBOL_TYPE_ID'] = 508
        elif parameters[17].valueAsText == 'Other County Route':
            segfields['SYMBOL_TYPE_ID'] = 600
        elif parameters[17].valueAsText == 'Other County Ramp':
            segfields['SYMBOL_TYPE_ID'] = 608
        elif parameters[17].valueAsText == 'Local Road':
            segfields['SYMBOL_TYPE_ID'] = 700
        elif parameters[17].valueAsText == 'Alley':
            segfields['SYMBOL_TYPE_ID'] = 900
        else:
            pass

        if parameters[18].valueAsText == 'Both': #text
            segfields['TRAVEL_DIR_TYPE_ID'] = 'B'
        elif parameters[18].valueAsText == 'Decreasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'D'
        elif parameters[18].valueAsText == 'Increasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'I'
        else:
            pass

        islinref = False
        if parameters[19].valueAsText == 'Public': #text
            segfields['JURIS_TYPE_ID'] = 'PUB'
            islinref = True
        elif parameters[19].valueAsText == 'Private' or parameters[19].valueAsText == 'Private (with linear referencing)':
            segfields['JURIS_TYPE_ID'] = 'PRI'
        elif parameters[19].valueAsText == 'Private (with linear referencing)':
            islinref = True
        elif parameters[19].valueAsText == 'Unknown':
            segfields['JURIS_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[20].valueAsText == 'Draft': #text
            segfields['OIT_REV_TYPE_ID'] = 'D'
        elif parameters[20].valueAsText == 'Final':
            segfields['OIT_REV_TYPE_ID'] = 'F'
        elif parameters[20].valueAsText == 'Incoming':
            segfields['OIT_REV_TYPE_ID'] = 'I'
        else:
            pass

        if parameters[21].valueAsText == 'Draft': #text
            segfields['DOT_REV_TYPE_ID'] = 'D'
        elif parameters[21].valueAsText == 'Final':
            segfields['DOT_REV_TYPE_ID'] = 'F'
        elif parameters[21].valueAsText == 'Incoming':
            segfields['DOT_REV_TYPE_ID'] = 'I'
        else:
            pass

        ########################################################################
        ## Excecute Things
        newGUID = erebus.calcGUID()
        splitpath = arcpy.env.scratchWorkspace + "\\mergeselection_multiple.p"
        if os.path.exists(splitpath):
            with open(splitpath,'rb') as splitopen:
                lastselect_multiple, segmentgeo_multiple, selectedfootprints_multiple = pickle.load(splitopen) # lastselect is a list of tuples, segmetngeo is a list of polyline geometries
        segmentgeo_multiple2 = []
        for g in segmentgeo_multiple:
            segmentgeo_multiple2.append(arcpy.FromWKT(g))
        segmentgeo_multiple = segmentgeo_multiple2
        merge_result = {'block1': False, 'block2': False, 'block3': False, 'block4': False, 'block5': False, 'block6': False, 'block7': False}
        # Block 1
        try:
            ## Figure out which records need to be sent to trans, change, and deleted throughout the database
            ismergerlist = []
            for record in lastselect_multiple:
                seg_sql = erebus.sqlGUID("SEG_GUID", record[2])
                find = False
                with arcpy.da.SearchCursor(segmentfc, "*", seg_sql) as cursor:
                    for row in cursor:
                        ismergerlist.append(True)
                        find = True
                if find == False:
                    ismergerlist.append(False)
            arcpy.AddMessage("The 2 segments will be merged to: {0}".format(lastselect_multiple[ismergerlist.index(True)]))
            arcpy.AddMessage('New SEG_GUID: {0}'.format(newGUID))
            newrow = []; delrows = []; newgeom = []; delgeom = []
            indind = 0
            for rec in ismergerlist:
                if rec == True:
                    newrow.append(lastselect_multiple[indind]) #*********
                    seg_sql = erebus.sqlGUID("SEG_GUID", lastselect_multiple[indind][2])
                    with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"], seg_sql) as cursor:
                        for row in cursor:
                            newgeom.append(row[0])
                        #newgeom.append(segmentgeo_multiple[indind])#***********
                if rec == False:
                    delrows.append(lastselect_multiple[indind])#***********
                    seg_sql = erebus.sqlGUID("SEG_GUID", lastselect_multiple[indind][2])
                    with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"], seg_sql) as cursor:
                        for row in cursor:
                            delgeom.append(row[0])
                    #delgeom.append(segmentgeo_multiple[indind])#***********
                indind += 1
            merge_result['block1'] = True
        except:
            trace = traceback.format_exc()
            merge_result['trace'] = trace
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            # write the result
            merge_path = arcpy.env.scratchWorkspace + "\\merge_result.p"
            with open(merge_path, 'wb') as output:
                pickle.dump(merge_result, output, -1)
            sys.exit("NJRE Merge block1 error")


        ########################################################################
        ########################################################################
        # Deal with the old segments first

        # Delete all remnants of the old ones & SEGMENT_TRANS insert
        # Block 2
        try:
            ## Run a delete tool for each row
            for dr in delrows:
                #arcpy.AddMessage('dr: {0}'.format(dr))
                del_result_segname = erebus.delete(dr[2], segnametab)
                if del_result_segname['result'] == 'success':
                    arcpy.AddMessage('SEG_NAME records deleted')
                elif del_result_segname['result'] == 'no matches':
                    arcpy.AddMessage('No SEG_NAME records remaining, deleted by relationship class "SEGMENThasSEG_NAME"')
                elif del_result_segname['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_segname))

                del_result_segshield = erebus.delete(dr[2], segshieldtab)
                if del_result_segshield['result'] == 'success':
                    arcpy.AddMessage('SEG_SHIELD records deleted')
                elif del_result_segshield['result'] == 'no matches':
                    arcpy.AddMessage('No SEG_SHIELD records remaining, deleted by relationship class "SEGMENThasSEG_SHIELD"')
                elif del_result_segshield['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_segshield))

                del_result_lrs = erebus.delete(dr[2], linreftab)
                if del_result_lrs['result'] == 'success':
                    arcpy.AddMessage('LINEAR_REF records deleted')
                elif del_result_lrs['result'] == 'no matches':
                    arcpy.AddMessage('No LINEAR_REF records remaining, deleted by relationship class "SEGMENThasLINEAR_REF"')
                elif del_result_lrs['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_lrs))

                # Track down the orphaned seg comments record from "seg_guid 0" segment. Delete it.
                # Get the globalid values for the deleted segment
                sc_recs = []
                for r in selectedfootprints_multiple:
                    if r['SEGMENT'][0]['SEG_GUID'] == dr[2]:
                        ## grab the seg comments records
                        for s in r['SEGMENT_COMMENTS']:
                            sc_recs.append(s['GLOBALID'])
                for sc in sc_recs:
                    del_result_comments = erebus.delete(sc, segcommtab, True)
                    if del_result_comments['result'] == 'success':
                        arcpy.AddMessage('SEGMENT_COMMENTS record deleted from deleted segment')
                    elif del_result_comments['result'] == 'no matches':
                        arcpy.AddMessage('No SEGMENT_COMMENTS record found: res {0}'.format(del_result_comments))
                    elif del_result_comments['trace']:
                        arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_comments))

                del_trans = erebus.segment_trans(dr[2], newGUID, transtab, dr[1])
                if del_trans['result'] == 'success':
                    arcpy.AddMessage('New record inserted into SEGMENT_TRANS')
                else:
                    arcpy.AddWarning("\neFailed to insert record into SEGMENT_TRANS, result is: {0}".format(del_trans))

            merge_result['block2'] = True
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            sys.exit("NJRE Merge block2 error")

        # Insert the old geometries into SEGMENT_CHANGE
        # Block 3
        try:
##            arcpy.AddMessage('Block 3')
##            cc = 0
##            for dg in delgeom:
##
##                #print 'dg.WKT inside merge {0}'.format(dg.WKT)
##                sc_object = erebus.SegmentChange(delrows[cc][2], segmentchangetab)
##                arcpy.AddMessage('sc_object {0}, newrow {1}, segmentchangetab {2}'.format(sc_object, newrow[cc][2], segmentchangetab))
##                changeresult = sc_object.insert(dg, change_type_id = 'R', comments = None, seg_id_arch = delrows[cc][1])
##                arcpy.AddMessage('changeresult {0}, dg {1}'.format(changeresult, dg))
##                cc += 1
##                if changeresult['result'] == 'success':
##                    arcpy.AddMessage('New record inseted into SEGMENT_CHANGE 3')
##                    arcpy.AddMessage(changeresult['method'])
##                else:
##                    arcpy.AddWarning("\neFailed to insert record into SEGMENT_CHANGE, result is: {0}".format(scresult))
##                    arcpy.AddMessage(changeresult['method'])
            merge_result['block3'] = True
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            sys.exit("NJRE Merge block3 error {0}".format(traceback.format_exc()))

        ########################################################################
        ########################################################################
        # Deal with the segment that was merged to. this will become the new GUID.

        # delete SEGMENT_COMMENTS records & SEGMENT_TRANS insert
        # Block 4
        try:
            for nr in newrow:
                delnew_result_comments = erebus.delete(newrow[0][2], segcommtab) # delete segment_comments
                if delnew_result_comments['result'] == 'success':
                    arcpy.AddMessage('SEGMENT_COMMENTS records deleted from target segment')
                elif delnew_result_comments['result'] == 'no matches':
                    arcpy.AddMessage('No SEGMENT_COMMENTS records found for target segment')
                elif delnew_result_comments['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(delnew_result_comments))

                new_trans = erebus.segment_trans(nr[2], newGUID, transtab, nr[1])  #insert segment transt
                if new_trans['result'] == 'success':
                    arcpy.AddMessage('New record inserted in SEGMENT_TRANS')
                else:
                    arcpy.AddWarning("\neFailed to insert record in SEGMENT_TRANS, result is: {0}".format(new_trans))
            merge_result['block4'] = True
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            sys.exit("NJRE Merge block4 error")

        # Insert the old geometry into SEGMENT_CHANGE
        # Block 5
        try:
            #arcpy.AddMessage('block5')
            for dg in segmentgeo_multiple:
                sc_object = erebus.SegmentChange(newrow[0][2], segmentchangetab)
                changeresult = sc_object.insert(dg, change_type_id = 'R', comments = None, seg_id_arch = newrow[0][1])
                if changeresult['result'] == 'success':
                    arcpy.AddMessage('New record inserted in SEGMENT_CHANGE. Geometry inserted using token {0}'.format(changeresult['method']))
                else:
                    arcpy.AddWarning("\neFailed to insert record into SEGMENT_CHANGE, result is: {0}".format(changeresult))
            merge_result['block5'] = True
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            sys.exit("NJRE Merge block5 error")

        ########################################################################
        ## Update and Insert (copy)
        # Block 6
        arcpy.AddMessage('newGuid: {0}'.format(newGUID))
        # arcpy.AddMessage('newrow[0][2]: {0}'.format(newrow[0][2]))
        try:
            updatemerge = erebus.UpdateGuid(newrow[0][2], newGUID) # UpdateCopy class object
            ## SEG_NAME
            segnameresult = updatemerge.segname(segnametab)
            if segnameresult['result'] == 'success':
                arcpy.AddMessage('SEG_NAME SEG_GUID updated for target segment')
            elif segnameresult['result'] == 'no matching records':
                arcpy.AddMessage('No matching SEG_NAME records for target segment')
            else:
                arcpy.AddWarning("\nupdatemerge.segname failed, result is: {0}".format(segnameresult))

            ## SEG_SHIELD
            segshieldresult = updatemerge.segshield(segshieldtab)
            if segshieldresult['result'] == 'success':
                arcpy.AddMessage('SEG_SHIELD SEG_GUID updated for target segment')
            elif segshieldresult['result'] == 'no matching records':
                arcpy.AddMessage('No matching SEG_SHIELD records for target segment')
            else:
                arcpy.AddWarning("\nupdatemerge.segshield failed, result is: {0}".format(segshieldresult))
            # get the MILEPOST_FR and MILEPOST_TO values from the new segment
            import json
            nrsql = erebus.sqlGUID("SEG_GUID",newrow[0][2])
            with arcpy.da.SearchCursor(segmentfc,"SHAPE@",nrsql) as cursor:
                for row in cursor:
                    nrjson = erebus.wkt_to_esrijson(row[0])['esrijson']
                    #nrjson = json.loads(row[0].JSON)
                    #arcpy.AddMessage("\nJSON: the geometry for the new segment {0}".format(nrjson))
            ## LINEAR_REF
            if parameters[22].value == True: intt = True
            else: intt = False
            lrresult = updatemerge.linearref(linreftab, nrjson, parameters[22].value)
            if lrresult['result'] == 'success':
                arcpy.AddMessage('LINEAR_REF SEG_GUID updated for target segment')
            elif lrresult['result'] == 'no matching records':
                arcpy.AddMessage('No matching LINEAR_REF records for target segment')
            else:
                arcpy.AddWarning("\nupdatemerge.linearref failed, result is: {0}".format(lrresult))

            merge_result['block6'] = True; merge_result['segnameresult'] = segnameresult; merge_result['segshieldresult'] = segshieldresult; merge_result['lrresult'] = lrresult

            merge_result['block6'] = True
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            trace = traceback.format_exc()
            merge_result['trace'] = trace
            sys.exit('NJRE Merge block6 error')

        ########################################################################
        ## SEGMENT, update to the new guid and fields
        # Block 7
        try:
            # update cursor for both segments
            cursor = arcpy.UpdateCursor(segmentfc, nrsql)
            for row in cursor:
                row.setValue('SEG_GUID', newGUID)
                row.setValue('ADDR_L_FR', segfields['ADDR_L_FR'])
                row.setValue('ADDR_L_TO', segfields['ADDR_L_TO'])
                row.setValue('ADDR_R_FR', segfields['ADDR_R_FR'])
                row.setValue('ADDR_R_TO', segfields['ADDR_R_TO'])
                row.setValue('ZIPCODE_L', segfields['ZIPCODE_L'])
                row.setValue('ZIPCODE_R', segfields['ZIPCODE_R'])
                row.setValue('ZIPNAME_L', segfields['ZIPNAME_L'])
                row.setValue('ZIPNAME_R', segfields['ZIPNAME_R'])
                if segfields['MUNI_ID_L']:
                    row.setValue('MUNI_ID_L', segfields['MUNI_ID_L'])
                if segfields['MUNI_ID_R']:
                    row.setValue('MUNI_ID_R', segfields['MUNI_ID_R'])
                if segfields['ELEV_TYPE_ID_FR']:
                    row.setValue('ELEV_TYPE_ID_FR', segfields['ELEV_TYPE_ID_FR'])
                if segfields['ELEV_TYPE_ID_TO']:
                    row.setValue('ELEV_TYPE_ID_TO', segfields['ELEV_TYPE_ID_TO'])
                if segfields['ACC_TYPE_ID']:
                    row.setValue('ACC_TYPE_ID', segfields['ACC_TYPE_ID'])
                if segfields['SURF_TYPE_ID']:
                    row.setValue('SURF_TYPE_ID', segfields['SURF_TYPE_ID'])
                if segfields['STATUS_TYPE_ID']:
                    row.setValue('STATUS_TYPE_ID', segfields['STATUS_TYPE_ID'])
                if segfields['SYMBOL_TYPE_ID']:
                    row.setValue('SYMBOL_TYPE_ID', segfields['SYMBOL_TYPE_ID'])
                if segfields['TRAVEL_DIR_TYPE_ID']:
                    row.setValue('TRAVEL_DIR_TYPE_ID', segfields['TRAVEL_DIR_TYPE_ID'])
                if segfields['JURIS_TYPE_ID']:
                    row.setValue('JURIS_TYPE_ID', segfields['JURIS_TYPE_ID'])
                if segfields['OIT_REV_TYPE_ID']:
                    row.setValue('OIT_REV_TYPE_ID', segfields['OIT_REV_TYPE_ID'])
                if segfields['DOT_REV_TYPE_ID']:
                    row.setValue('DOT_REV_TYPE_ID', segfields['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            del row, cursor
            merge_result['block7'] = True
            arcpy.AddMessage('SEGMENT record updated with new SEG_GUID for target segment')
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            trace = traceback.format_exc()
            merge_result['trace'] = trace
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
        set_tool_indicator(arcpy.env.scratchWorkspace, False)
        return

# END Merge
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

class MergeCleanup(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "MergeCleanup"
        self.description = ""
        self.canRunInBackground = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
        global USER, Domains
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="SEG_ID",
            name="SEG_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param0.enabled = False

        #
        param1 = arcpy.Parameter(
            displayName="PRIME_NAME",
            name="PRIME_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param1.enabled = False

        #
        param2 = arcpy.Parameter(
            displayName="ADDR_L_FR",
            name="ADDR_L_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param3 = arcpy.Parameter(
            displayName="ADDR_L_TO",
            name="ADDR_L_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param4 = arcpy.Parameter(
            displayName="ADDR_R_FR",
            name="ADDR_R_FR",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param5 = arcpy.Parameter(
            displayName="ADDR_R_TO",
            name="ADDR_R_TO",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        #
        param6 = arcpy.Parameter(
            displayName="ZIPCODE_L",
            name="ZIPCODE_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param7 = arcpy.Parameter(
            displayName="ZIPCODE_R",
            name="ZIPCODE_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param8 = arcpy.Parameter(
            displayName="ZIPNAME_L",
            name="ZIPNAME_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param9 = arcpy.Parameter(
            displayName="ZIPNAME_R",
            name="ZIPNAME_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        gnis = Domains['GNIS_NAME'].values()
        gnis2 = sorted(gnis, key = lambda item: item.split(',')[1] + item.split(',')[0])
        #
        param10 = arcpy.Parameter(
            displayName="MUNI_ID_L",
            name="MUNI_ID_L",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param10.filter.type = "ValueList"
        param10.filter.list = gnis2

        #
        param11 = arcpy.Parameter(
            displayName="MUNI_ID_R",
            name="MUNI_ID_R",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param11.filter.type = "ValueList"
        param11.filter.list = gnis2

        #
        param12 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_FR",
            name="ELEV_TYPE_ID_FR",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param12.filter.type = "ValueList"
        param12.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        #
        param13 = arcpy.Parameter(
            displayName="ELEV_TYPE_ID_TO",
            name="ELEV_TYPE_ID_TO",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param13.filter.type = "ValueList"
        param13.filter.list = ["At Grade", "Level 1", "Level 2", "Level 3"]
        #
        param14 = arcpy.Parameter(
            displayName="ACC_TYPE_ID",
            name="ACC_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param14.filter.type = "ValueList"
        param14.filter.list = ["Non-Restricted", "Restricted", "Unknown"]

        #
        param15 = arcpy.Parameter(
            displayName="SURF_TYPE_ID",
            name="SURF_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param15.filter.type = "ValueList"
        param15.filter.list = ["Improved", "Unimproved", "Unknown"]

        #
        param16 = arcpy.Parameter(
            displayName="STATUS_TYPE_ID",
            name="STATUS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param16.filter.type = "ValueList"
        param16.filter.list = ["Active", "Planned", "Under Construction"]

        #
        param17 = arcpy.Parameter(
            displayName="SYMBOL_TYPE_ID",
            name="SYMBOL_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param17.filter.type = "ValueList"
        param17.filter.list = ["Highway Authority Route", "Highway Authority Ramp", "Interstate", "Insterstate Ramp", "US Highway", "US Highway Ramp", "State Highway", "State Highway Ramp", "County 500 Route", "County 500 Ramp", "Other County Route", "Other County Ramp", "Local Road", "Local Ramp", "Alley"]

        #
        param18 = arcpy.Parameter(
            displayName="TRAVEL_DIR_TYPE_ID",
            name="TRAVEL_DIR_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param18.filter.type = "ValueList"
        param18.filter.list = ["Both", "Decreasing", "Increasing"]

        #
        param19 = arcpy.Parameter(
            displayName="JURIS_TYPE_ID",
            name="JURIS_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param19.filter.type = "ValueList"
        param19.filter.list = ["Public", "Private", "Unknown"]

        #
        param20 = arcpy.Parameter(
            displayName="OIT_REV_TYPE_ID",
            name="OIT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param20.filter.type = "ValueList"
        param20.filter.list = ["Draft", "Final", "Incoming"]

        #
        param21 = arcpy.Parameter(
            displayName="DOT_REV_TYPE_ID",
            name="DOT_REV_TYPE_ID",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param21.filter.type = "ValueList"
        param21.filter.list = ["Draft", "Final", "Incoming"]

        param22 = arcpy.Parameter(
            displayName="Update LINEAR_REF MILEPOST_FR and MILEPOST_TO values (if applicable)",
            name="update milepost",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param22.value = True

        #-----------------------------------------------------------------------
        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10,param11,param12,param13,param14,param15,param16,param17,param18,param19,param20,param21,param22]
        return params
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True
    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        import arcpy
        global USER
        # ----------------------------------------------------------------------
        # Define globals
        global merge_left_interp, merge_right_interp

        # Construct the DOMAIN Dictionaries
        domains = arcpy.da.ListDomains(arcpy.env.workspace)
        Domains = {}
        for domain in domains:
            Domains[domain.name] = domain.codedValues    #SYMBOL_TYPE JURIS_TYPE ELEV_TYPE CHANGE_TYPE REVIEW_TYPE STATUS_TYPE TRAVEL_DIR_TYPE DATA_SOURCE_TYPE SHIELD_TYPE ACCESS_TYPE SHIELD_SUBTYPE SEGMENT_TYPE NAME_TYPE SURFACE_TYPE GNIS_NAME LRS_TYPE

        # ----------------------------------------------------------------------
        # GET THE SEGMENT THAT IS CURRENTLY SELECTED
        import arcpy, os, sys, pickle, json
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        ########################################################################
        ## Figure out which one is merged to
        splitpath = arcpy.env.scratchWorkspace + "\\mergeselection_multiple.p"
        if os.path.exists(splitpath):
            with open(splitpath,'rb') as splitopen:
                lastselect_multiple, segmentgeo_multiple, selectedfootprints_multiple = pickle.load(splitopen) # lastselect is a list of tuples, segmetngeo is a list of polyline geometries
        try:
            ## Figure out which records need to be sent to trans, change, and deleted throughout the database
            ## After the merge is performed we have the two segments that were selected as lastselect_multiple, and the
            ## new segment (merged) is now selected with the same SEG_GUID. So, look through and compare. The SEG_GUID that is still
            ## there will be the one that was merged to. The other segment will have been deleted.
            ismergerlist = []
            for record in lastselect_multiple:
                seg_sql = erebus.sqlGUID("SEG_GUID", record[2])
                find = False
                with arcpy.da.SearchCursor(segmentfc, "*", seg_sql) as cursor:
                    for row in cursor:
                        ismergerlist.append(True)
                        find = True
                if find == False:
                    ismergerlist.append(False)
            newrow = []; delrows = []; newgeom = []; delgeom = [];
            indind = 0
            for rec in ismergerlist:
                if rec == True:
                    newrow.append(lastselect_multiple[indind]) #***********
                    newgeom.append(segmentgeo_multiple[indind])#***********
                if rec == False:
                    delrows.append(lastselect_multiple[indind])#***********
                    delgeom.append(segmentgeo_multiple[indind])#***********
                indind += 1
        except:
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
        # convert the wkt to esrijson
        ej1 = erebus.wkt_to_esrijson(segmentgeo_multiple[0])
        if ej1['result'] == 'success':
            segmentgeo0 = ej1['esrijson']
        ej2 = erebus.wkt_to_esrijson(segmentgeo_multiple[1])
        if ej2['result'] == 'success':
            segmentgeo1 = ej2['esrijson']
        lastselect0 = lastselect_multiple[0]
        lastselect1 = lastselect_multiple[1]
        nrsql = erebus.sqlGUID("SEG_GUID",newrow[0][2])
        with arcpy.da.SearchCursor(segmentfc, "*", nrsql) as cursor:  # insert a cursor to access fields, print names
            for row in cursor:
                segmentrow = row
        parameters[0].value = segmentrow[1]
        parameters[1].value = segmentrow[3]

        ######################################################################
        ## INTERPOLATE ADDRESSES
        ######################################################################
        addintmess = {'result': 'na', 'message': 'na', 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}

        if segmentrow[4] and segmentrow[5] and delrows[0][4] and delrows[0][5] and not MergeAltered[0] and not MergeAltered[1]:

            new_l_dir = segmentrow[5] - segmentrow[4]
            del_l_dir = delrows[0][5] - delrows[0][4]

            # left side both increasing
            if new_l_dir > 0 and del_l_dir > 0:  # both increasing
                if segmentrow[4] > delrows[0][5]:  # newrow has the larger addresses
                    parameters[2].value = delrows[0][4]
                    parameters[3].value = segmentrow[5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True
                if segmentrow[4] < delrows[0][5]:  # newrow has the lesser addresses
                    parameters[2].value = segmentrow[4]
                    parameters[3].value = delrows[0][5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True

            # left side both decreasing
            if new_l_dir < 0 and del_l_dir < 0:  # both decreasing
                if segmentrow[4] < delrows[0][5]:  # newrow has the lesser addresses
                    parameters[2].value = delrows[0][4]
                    parameters[3].value = segmentrow[5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True
                if segmentrow[4] > delrows[0][5]:  # newrow has the larger addresses
                    parameters[2].value = segmentrow[4]
                    parameters[3].value = delrows[0][5]
                    addintmess['addrlfr'] = True; addintmess['addrlto'] = True
                    merge_left_interp = True
                    MergeAltered[0] = True; MergeAltered[1] = True

        if segmentrow[6] and segmentrow[7] and delrows[0][6] and delrows[0][7] and not MergeAltered[2] and not MergeAltered[3]:

            new_r_dir = segmentrow[7] - segmentrow[6]
            del_r_dir = delrows[0][7] - delrows[0][6]

            # right side both increasing
            if new_r_dir > 0 and del_r_dir > 0:  # both increasing
                if segmentrow[6] > delrows[0][7]:  # newrow has the larger addresses
                    parameters[4].value = delrows[0][6]
                    parameters[5].value = segmentrow[7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True
                if segmentrow[6] < delrows[0][7]:  # newrow has the lesser addresses
                    parameters[4].value = segmentrow[6]
                    parameters[5].value = delrows[0][7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True

            # right side both decreasing
            if new_r_dir < 0 and del_r_dir < 0:  # both decreasing
                if segmentrow[6] < delrows[0][7]:  # newrow has the lesser addresses
                    parameters[4].value = delrows[0][6]
                    parameters[5].value = segmentrow[7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True
                if segmentrow[6] > delrows[0][7]:  # newrow has the greater addresses
                    parameters[4].value = segmentrow[6]
                    parameters[5].value = delrows[0][7]
                    addintmess['addrrfr'] = True; addintmess['addrrto'] = True
                    merge_right_interp = True
                    MergeAltered[2] = True; MergeAltered[3] = True

        if not parameters[2].altered and not addintmess['addrlfr'] and parameters[2].value and not MergeAltered[0]:
            if segmentrow[4]:
                parameters[2].value = segmentrow[4]
                MergeAltered[0] = True
        if not parameters[3].altered and not addintmess['addrlto'] and parameters[3].value and not MergeAltered[1]:
            if segmentrow[5]:
                parameters[3].value = segmentrow[5]
                MergeAltered[1] = True
        if not parameters[4].altered and not addintmess['addrrfr'] and parameters[4].value and not MergeAltered[2]:
            if segmentrow[6]:
                parameters[4].value = segmentrow[6]
                MergeAltered[2] = True
        if not parameters[5].altered and not addintmess['addrrto'] and parameters[5].value and not MergeAltered[3]:
            if segmentrow[7]:
                parameters[5].value = segmentrow[7]
                MergeAltered[3] = True

        ######################################################################
        for i in range(6,10):
            if segmentrow[i+2]:
                if not parameters[i].altered:
                    parameters[i].value = segmentrow[i+2]
        if segmentrow[12]:
            if not parameters[10].altered:
                for key,value in Domains['GNIS_NAME'].iteritems():
                    if key == segmentrow[12]:
                        parameters[10].value = value
        if segmentrow[13]:
            if not parameters[11].altered:
                for key,value in Domains['GNIS_NAME'].iteritems():
                    if key == segmentrow[13]:
                        parameters[11].value = value
##        if segmentrow[13]:
##            if not parameters[11].altered:
##                parameters[11].value = segmentrow[13]

        ######################################################################
        ## INTERPOLATE ELEVATION
        ######################################################################
        global merge_elevation
        if not parameters[12].altered and not parameters[13].altered and ej1['result'] == 'success' and ej2['result'] == 'success':
            if 'curvePaths' in segmentgeo0.keys():
                # format for true curves
                xym1 = []; xym2 = [];
                for i in segmentgeo0['curvePaths'][0]:
                    if type(i) is list:
                        xym1.append(i)
                    elif type(i) is dict:
                        xym1.append(i['c'][0])
                for i in segmentgeo1['curvePaths'][0]:
                    if type(i) is list:
                        xym2.append(i)
                    elif type(i) is dict:
                        xym2.append(i['c'][0])
            elif 'paths' in segmentgeo0.keys():
                #format for no true curves
                xym1 = segmentgeo0['paths'][0] # list of lists. each list has [x,y,m]
                xym2 = segmentgeo1['paths'][0]
            fr0 = xym1[0][0:2]  # x and y list of segment 0 from (i.e. start), [619573.7800000012, 501185.0200000033]
            to0 = xym1[-1][0:2]
            fr1 = xym2[0][0:2]  # x and y list of segment 1 from (i.e. start), [619573.7800000012, 501185.0200000033]
            to1 = xym2[-1][0:2]

            fr0E = lastselect0[14] # from elevation segment0
            to0E = lastselect0[15]
            fr1E = lastselect1[14]
            to1E = lastselect1[15]

            elevdict = {0: 'At Grade', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3'}
            ## Order the coordinates and segments so that we know which ends are touching and which ends are terminal.

            # is the order 0 to 1?
            import math
            dist_to0_fr1 = math.sqrt((to0[0] - fr1[0])**2 + (to0[1] - fr1[1])**2)
            dist_fr0_to1 = math.sqrt((to1[0] - fr0[0])**2 + (to1[1] - fr0[1])**2)
            if dist_to0_fr1 < dist_fr0_to1:  # the order is 0 to 1
                # take care of errors first
                if fr0E == 0 and to0E == 1 and fr1E == 1 and to1E == 0: # error code 1
                    merge_elevation = 1
                elif fr0E == 1 and to0E == 1 and fr1E == 1 and to1E == 0: # error code 2
                    merge_elevation = 2
                elif fr0E == 0 and to0E == 1 and fr1E == 1 and to1E == 1: # error code 3
                    merge_elevation = 3
                else: # no errors, do the inerpolation
                        parameters[12].value = elevdict[fr0E]
                        parameters[13].value = elevdict[to1E]
                        merge_elevation = 0
            if dist_to0_fr1 > dist_fr0_to1:  # the order is 1 to 0
                # take care of errors first
                if fr0E == 1 and to0E == 0 and fr1E == 0 and to1E == 1: # error code 1
                    merge_elevation = 1
                elif fr0E == 1 and to0E == 0 and fr1E == 1 and to1E == 1: # error code 2
                    merge_elevation = 2
                elif fr0E == 1 and to0E == 1 and fr1E == 0 and to1E == 1: # error code 3
                    merge_elevation = 3
                else: # no errors, do the inerpolation
                        parameters[12].value = elevdict[fr1E]
                        parameters[13].value = elevdict[to0E]
                        merge_elevation = 0
        ######################################################################
        if segmentrow[16]:
            if not parameters[14].altered:
                if segmentrow[16] == 'N':
                    parameters[14].value = 'Non-Restricted'
                if segmentrow[16] == 'R':
                    parameters[14].value = 'Restricted'
                if segmentrow[16] == 'UNK':
                    parameters[14].value = 'Unknown'
        if segmentrow[17]:
            if not parameters[15].altered:
                if segmentrow[17] == 'I':
                    parameters[15].value = 'Improved'
                if segmentrow[17] == 'U':
                    parameters[15].value = 'Unimproved'
                if segmentrow[17] == 'UNK':
                    parameters[15].value = 'Unknown'
        if segmentrow[18]:
            if not parameters[16].altered:
                if segmentrow[18] == 'A':
                    parameters[16].value = 'Active'
                if segmentrow[18] == 'P':
                    parameters[16].value = 'Planned'
                if segmentrow[18] == 'U':
                    parameters[16].value = 'Under Construction'
        if segmentrow[19]:
            if not parameters[17].altered:
                symboltypedict = {100: "Highway Authority Route", 108: "Highway Authority Ramp", 200: "Interstate", 208: "Insterstate Ramp", 300: "US Highway", 308: "US Highway Ramp", 400: "State Highway", 408: "State Highway Ramp", 500: "County 500 Route", 508: "County 500 Ramp", 600: "Other County Route", 608: "Other County Ramp", 700: "Local Road", 708: "Local Ramp", 900: "Alley"}
                parameters[17].value = symboltypedict[int(segmentrow[19])]
        if segmentrow[20]:
            if not parameters[18].altered:
                if segmentrow[20] == 'B':
                    parameters[18].value = 'Both'
                if segmentrow[20] == 'D':
                    parameters[18].value = 'Decreasing'
                if segmentrow[20] == 'I':
                    parameters[18].value = 'Increasing'
        if segmentrow[21]:
            if not parameters[19].altered:
                if segmentrow[21] == 'PUB':
                    parameters[19].value = 'Public'
                if segmentrow[21] == 'PRI':
                    parameters[19].value = 'Private'
                if segmentrow[21] == 'UNK':
                    parameters[19].value = 'Unknown'
        if segmentrow[22]:
            if not parameters[20].altered:
                if USER in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                    usedict = {'NJ OIT': 'Final', 'NJ DOT': 'Draft', 'County': 'Incoming', 'Other': 'Draft'}
                    parameters[20].value = usedict[USER]
                else:
                    parameters[20].value = 'Draft'
        if segmentrow[23]:
            if not parameters[21].altered:
                if USER in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                    usedict = {'NJ OIT': 'Draft', 'NJ DOT': 'Final', 'County': 'Draft', 'Other': 'Draft'}
                    parameters[21].value = usedict[USER]
                else:
                    parameters[21].value = 'Draft'
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        global merge_left_interp, merge_right_interp, merge_elevation
        if not merge_left_interp:
            parameters[2].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
            parameters[3].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
        if not merge_right_interp:
            parameters[4].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
            parameters[5].setWarningMessage('This value has NOT been interpolated from the 2 merged segments.')
        #parameters[11].setWarningMessage('Elevation interpolation failed due to violation of Merge Rule #3, please choose an elevation type. ERROR Code: {0}, is 12 altered {1}'.format(merge_elevation, parameters[12].altered))
        if merge_elevation == 99: # interpolation failed.
            parameters[12].setWarningMessage('Elevation interpolation failed, please choose a valid elevation type.')
            parameters[13].setWarningMessage('Elevation interpolation failed, please choose a valid elevation type.')
        if merge_elevation in (1,2,3): # interpolation failed.
            parameters[12].setWarningMessage('Elevation interpolation failed due to violation of Merge Rule #3, please choose a valid elevation type. ERROR Code: {0}. Is altered {1}'.format(merge_elevation,parameters[12].altered))
            parameters[13].setWarningMessage('Elevation interpolation failed due to violation of Merge Rule #3, please choose a valid elevation type. ERROR Code: {0}'.format(merge_elevation))
        if parameters[12].altered:
            parameters[12].clearMessage()
        if parameters[13].altered:
            parameters[13].clearMessage()
        return

    def execute(self, parameters, messages):
        """The source code of the Merge tool."""
        import sys
        import os
        import pickle
        import arcpy
        import traceback
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        set_tool_indicator(arcpy.env.scratchWorkspace, True)
        # Construct the DOMAIN Dictionaries
        domains = arcpy.da.ListDomains(arcpy.env.workspace)
        Domains = {}
        for domain in domains:
            Domains[domain.name] = domain.codedValues    #SYMBOL_TYPE JURIS_TYPE ELEV_TYPE CHANGE_TYPE REVIEW_TYPE STATUS_TYPE TRAVEL_DIR_TYPE DATA_SOURCE_TYPE SHIELD_TYPE ACCESS_TYPE SHIELD_SUBTYPE SEGMENT_TYPE NAME_TYPE SURFACE_TYPE GNIS_NAME LRS_TYPE
        # Set up the segment dictionary
        des_seg = arcpy.Describe(segmentfc)
        des_seg_fields = des_seg.fields
        segfields = {}
        for field in des_seg_fields:
            segfields[str(field.name)] = ''
        ################################################################################
        ## ROAD.SEGMENT Parameters
        segfields['SEG_ID'] = parameters[0].valueAsText  # long integer
        segfields['PRIME_NAME'] = parameters[1].valueAsText # text
        segfields['ADDR_L_FR'] = parameters[2].value # long integer
        segfields['ADDR_L_TO'] = parameters[3].value # long integer
        segfields['ADDR_R_FR'] = parameters[4].value # long integer
        segfields['ADDR_R_TO'] = parameters[5].value  # long integer
        segfields['ZIPCODE_L'] = parameters[6].valueAsText # text
        segfields['ZIPCODE_R'] = parameters[7].valueAsText # text
        segfields['ZIPNAME_L'] = parameters[8].valueAsText # text
        segfields['ZIPNAME_R'] = parameters[9].valueAsText # text
        if parameters[10].value:
            for key,value in Domains['GNIS_NAME'].iteritems():
                if value == parameters[10].value:
                    segfields['MUNI_ID_L'] = key
        if parameters[11].value:
            for key,value in Domains['GNIS_NAME'].iteritems():
                if value == parameters[11].value:
                    segfields['MUNI_ID_R'] = key

        if parameters[12].valueAsText == 'At Grade': # input is string, long integer
            segfields['ELEV_TYPE_ID_FR'] = 0
        elif parameters[12].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_FR'] = 1
        elif parameters[12].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_FR'] = 2
        elif parameters[12].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_FR'] = 3
        else:
            pass

        if parameters[13].valueAsText == 'At Grade': # input is string, long integer
            segfields['ELEV_TYPE_ID_TO'] = 0
        elif parameters[13].valueAsText == 'Level 1':
            segfields['ELEV_TYPE_ID_TO'] = 1
        elif parameters[13].valueAsText == 'Level 2':
            segfields['ELEV_TYPE_ID_TO'] = 2
        elif parameters[13].valueAsText == 'Level 3':
            segfields['ELEV_TYPE_ID_TO'] = 3
        else:
            pass

        if parameters[14].valueAsText == 'Non-Restricted': #text
            segfields['ACC_TYPE_ID'] = 'N'
        elif parameters[14].valueAsText == 'Restricted':
            segfields['ACC_TYPE_ID'] = 'R'
        elif parameters[14].valueAsText == 'Unknown':
            segfields['ACC_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[15].valueAsText == 'Improved': #text
            segfields['SURF_TYPE_ID'] = 'I'
        elif parameters[15].valueAsText == 'Unimproved':
            segfields['SURF_TYPE_ID'] = 'U'
        elif parameters[15].valueAsText == 'Unknown':
            segfields['SURF_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[16].valueAsText == 'Active': #text
            segfields['STATUS_TYPE_ID'] = 'A'
        elif parameters[16].valueAsText == 'Planned':
            segfields['STATUS_TYPE_ID'] = 'P'
        elif parameters[16].valueAsText == 'Under Construction':
            segfields['STATUS_TYPE_ID'] = 'U'
        else:
            pass

        if parameters[17].valueAsText == 'Highway Authority Route': # input is string, short integer
            segfields['SYMBOL_TYPE_ID'] = 100
        elif parameters[17].valueAsText == 'Highway Authority Ramp':
            segfields['SYMBOL_TYPE_ID'] = 108
        elif parameters[17].valueAsText == 'Interstate':
            segfields['SYMBOL_TYPE_ID'] = 200
        elif parameters[17].valueAsText == 'Interstate Ramp':
            segfields['SYMBOL_TYPE_ID'] = 208
        elif parameters[17].valueAsText == 'US Highway':
            segfields['SYMBOL_TYPE_ID'] = 300
        elif parameters[17].valueAsText == 'US Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 308
        elif parameters[17].valueAsText == 'State Highway':
            segfields['SYMBOL_TYPE_ID'] = 400
        elif parameters[17].valueAsText == 'State Highway Ramp':
            segfields['SYMBOL_TYPE_ID'] = 408
        elif parameters[17].valueAsText == 'County 500 Route':
            segfields['SYMBOL_TYPE_ID'] = 500
        elif parameters[17].valueAsText == 'County 500 Ramp':
            segfields['SYMBOL_TYPE_ID'] = 508
        elif parameters[17].valueAsText == 'Other County Route':
            segfields['SYMBOL_TYPE_ID'] = 600
        elif parameters[17].valueAsText == 'Other County Ramp':
            segfields['SYMBOL_TYPE_ID'] = 608
        elif parameters[17].valueAsText == 'Local Road':
            segfields['SYMBOL_TYPE_ID'] = 700
        elif parameters[17].valueAsText == 'Alley':
            segfields['SYMBOL_TYPE_ID'] = 900
        else:
            pass

        if parameters[18].valueAsText == 'Both': #text
            segfields['TRAVEL_DIR_TYPE_ID'] = 'B'
        elif parameters[18].valueAsText == 'Decreasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'D'
        elif parameters[18].valueAsText == 'Increasing':
            segfields['TRAVEL_DIR_TYPE_ID'] = 'I'
        else:
            pass

        islinref = False
        if parameters[19].valueAsText == 'Public': #text
            segfields['JURIS_TYPE_ID'] = 'PUB'
            islinref = True
        elif parameters[19].valueAsText == 'Private' or parameters[19].valueAsText == 'Private (with linear referencing)':
            segfields['JURIS_TYPE_ID'] = 'PRI'
        elif parameters[19].valueAsText == 'Private (with linear referencing)':
            islinref = True
        elif parameters[19].valueAsText == 'Unknown':
            segfields['JURIS_TYPE_ID'] = 'UNK'
        else:
            pass

        if parameters[20].valueAsText == 'Draft': #text
            segfields['OIT_REV_TYPE_ID'] = 'D'
        elif parameters[20].valueAsText == 'Final':
            segfields['OIT_REV_TYPE_ID'] = 'F'
        elif parameters[20].valueAsText == 'Incoming':
            segfields['OIT_REV_TYPE_ID'] = 'I'
        else:
            pass

        if parameters[21].valueAsText == 'Draft': #text
            segfields['DOT_REV_TYPE_ID'] = 'D'
        elif parameters[21].valueAsText == 'Final':
            segfields['DOT_REV_TYPE_ID'] = 'F'
        elif parameters[21].valueAsText == 'Incoming':
            segfields['DOT_REV_TYPE_ID'] = 'I'
        else:
            pass

        ########################################################################
        ## Excecute Things
        splitpath = arcpy.env.scratchWorkspace + "\\mergeselection_multiple.p"
        if os.path.exists(splitpath):
            with open(splitpath,'rb') as splitopen:
                lastselect_multiple, segmentgeo_multiple, selectedfootprints_multiple = pickle.load(splitopen) # lastselect is a list of tuples, segmetngeo is a list of polyline geometries
        merge_result = {'block1': False, 'block2': False, 'block3': False, 'block4': False, 'block5': False, 'block6': False, 'block7': False}
        try:
            ## Figure out which records need to be sent to trans, change, and deleted throughout the database
            ismergerlist = []
            for record in lastselect_multiple:
                seg_sql = erebus.sqlGUID("SEG_GUID", record[2])
                find = False
                with arcpy.da.SearchCursor(segmentfc, "*", seg_sql) as cursor:
                    for row in cursor:
                        ismergerlist.append(True)
                        find = True
                if find == False:
                    ismergerlist.append(False)
            #arcpy.AddMessage("Records that match current SEGMENT records: {0}\nSegments merged to: {1}".format(ismergerlist, lastselect_multiple[ismergerlist.index(True)]))
            newrow = []; delrows = []; newgeom = []; delgeom = [];
            indind = 0
            for rec in ismergerlist:
                if rec == True:
                    newrow.append(lastselect_multiple[indind]) #***********
                    newgeom.append(segmentgeo_multiple[indind])#***********
                if rec == False:
                    delrows.append(lastselect_multiple[indind])#***********
                    delgeom.append(segmentgeo_multiple[indind])#***********
                indind += 1
            merge_result['block1'] = True
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            trace = traceback.format_exc()
            merge_result['trace'] = trace
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            # write the result
            merge_path = arcpy.env.scratchWorkspace + "\\merge_result.p"
            with open(merge_path, 'wb') as output:
                pickle.dump(merge_result, output, -1)
            sys.exit("NJRE Merge block1 error")
        ########################################################################
        ########################################################################
        newGUID = erebus.calcGUID()
        ########################################################################
        ########################################################################
        # Deal with the old segments first
        # Delete all remnants of the old ones & SEGMENT_TRANS insert
        try:
            ## Run a delete tool for each row
            for dr in delrows:
                del_result_segname = erebus.delete(dr[2], segnametab)
                if del_result_segname['result'] == 'success':
                    arcpy.AddMessage('SEG_NAME records deleted')
                elif del_result_segname['result'] == 'no matches':
                    arcpy.AddMessage('No SEG_NAME records found')
                elif del_result_segname['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_segname))

                del_result_segshield = erebus.delete(dr[2], segshieldtab)
                if del_result_segshield['result'] == 'success':
                    arcpy.AddMessage('SEG_SHIELD records deleted')
                elif del_result_segshield['result'] == 'no matches':
                    arcpy.AddMessage('No SEG_SHIELD records found')
                elif del_result_segshield['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_segshield))

                del_result_lrs = erebus.delete(dr[2], linreftab)
                if del_result_lrs['result'] == 'success':
                    arcpy.AddMessage('LINEAR_REF records deleted')
                elif del_result_lrs['result'] == 'no matches':
                    arcpy.AddMessage('No LINEAR_REF records found')
                elif del_result_lrs['trace']:
                    arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_lrs))

                # Track down the orphaned seg comments record from "seg_guid 0" segment. Delete it.
                # Get the globalid values for the deleted segment
                sc_recs = []
                for r in selectedfootprints_multiple:
                    if r['SEGMENT'][0]['SEG_GUID'] == dr[2]:
                        ## grab the seg comments records
                        for s in r['SEGMENT_COMMENTS']:
                            sc_recs.append(s['GLOBALID'])
                for sc in sc_recs:
                    del_result_comments = erebus.delete(sc, segcommtab, True)
                    if del_result_comments['result'] == 'success':
                        arcpy.AddMessage('SEGMENT_COMMENTS record deleted from deleted segment')
                    elif del_result_comments['result'] == 'no matches':
                        arcpy.AddMessage('No SEGMENT_COMMENTS record found: res {0}'.format(del_result_comments))
                    elif del_result_comments['trace']:
                        arcpy.AddWarning("\nerebus.delete failed, result is: {0}".format(del_result_comments))
                del_trans = erebus.segment_trans(dr[2], newGUID, transtab, dr[1])
                if del_trans['result'] == 'success':
                    arcpy.AddMessage('New record inseted into SEGMENT_TRANS')
                else:
                    arcpy.AddWarning("\neFailed to insert record into SEGMENT_TRANS, result is: {0}".format(trans_result1))
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            sys.exit("NJRE Merge block2 error")
        try:
            updatemerge = erebus.UpdateGuid(newrow[0][2], newrow[0][2]) # UpadateCopy class object
            # get the MILEPOST_FR and MILEPOST_TO values from the new segment
            import json
            nrsql = erebus.sqlGUID("SEG_GUID",newrow[0][2])
            with arcpy.da.SearchCursor(segmentfc,"SHAPE@",nrsql) as cursor:
                for row in cursor:
                    nrjson = erebus.wkt_to_esrijson(row[0])['esrijson']
                    #nrjson = json.loads(row[0].JSON)
                    #arcpy.AddMessage("the current geometry for the new segment {0}".format(nrjson))
            ## LINEAR_REF - grab the m-values from the new segment and put them in the current records
            lrresult = updatemerge.linearref(linreftab, nrjson, interp = parameters[22].value)
            if lrresult['result'] == 'success':
                arcpy.AddMessage('LINEAR_REF SEG_GUID updated')
            elif lrresult['result'] == 'no matching records':
                arcpy.AddMessage('No matching LINEAR_REF records')
            else:
                arcpy.AddWarning("\nupdatemerge.linearref failed, result is: {0}".format(lrresult))

            merge_result['block6'] = True; merge_result['lrresult'] = lrresult


        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            trace = traceback.format_exc()
            merge_result['trace'] = trace
            sys.exit('NJRE Merge block6 error')

        ########################################################################
        ## SEGMENT
        nrsql = erebus.sqlGUID("SEG_GUID",newrow[0][2])
        try:
            # update cursor for both segments
            cursor = arcpy.UpdateCursor(segmentfc, nrsql)
            for row in cursor:
                #row.setValue('SEG_GUID', newGUID)
                row.setValue('ADDR_L_FR', segfields['ADDR_L_FR'])
                row.setValue('ADDR_L_TO', segfields['ADDR_L_TO'])
                row.setValue('ADDR_R_FR', segfields['ADDR_R_FR'])
                row.setValue('ADDR_R_TO', segfields['ADDR_R_TO'])
                row.setValue('ZIPCODE_L', segfields['ZIPCODE_L'])
                row.setValue('ZIPCODE_R', segfields['ZIPCODE_R'])
                row.setValue('ZIPNAME_L', segfields['ZIPNAME_L'])
                row.setValue('ZIPNAME_R', segfields['ZIPNAME_R'])
                if segfields['MUNI_ID_L']:
                    row.setValue('MUNI_ID_L', segfields['MUNI_ID_L'])
                if segfields['MUNI_ID_R']:
                    row.setValue('MUNI_ID_R', segfields['MUNI_ID_R'])
                if segfields['ELEV_TYPE_ID_FR']:
                    row.setValue('ELEV_TYPE_ID_FR', segfields['ELEV_TYPE_ID_FR'])
                if segfields['ELEV_TYPE_ID_TO']:
                    row.setValue('ELEV_TYPE_ID_TO', segfields['ELEV_TYPE_ID_TO'])
                if segfields['ACC_TYPE_ID']:
                    row.setValue('ACC_TYPE_ID', segfields['ACC_TYPE_ID'])
                if segfields['SURF_TYPE_ID']:
                    row.setValue('SURF_TYPE_ID', segfields['SURF_TYPE_ID'])
                if segfields['STATUS_TYPE_ID']:
                    row.setValue('STATUS_TYPE_ID', segfields['STATUS_TYPE_ID'])
                if segfields['SYMBOL_TYPE_ID']:
                    row.setValue('SYMBOL_TYPE_ID', segfields['SYMBOL_TYPE_ID'])
                if segfields['TRAVEL_DIR_TYPE_ID']:
                    row.setValue('TRAVEL_DIR_TYPE_ID', segfields['TRAVEL_DIR_TYPE_ID'])
                if segfields['JURIS_TYPE_ID']:
                    row.setValue('JURIS_TYPE_ID', segfields['JURIS_TYPE_ID'])
                if segfields['OIT_REV_TYPE_ID']:
                    row.setValue('OIT_REV_TYPE_ID', segfields['OIT_REV_TYPE_ID'])
                if segfields['DOT_REV_TYPE_ID']:
                    row.setValue('DOT_REV_TYPE_ID', segfields['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            del row, cursor
            merge_result['block7'] = True
            arcpy.AddMessage('SEGMENT record updated with new SEG_GUID')
        except:
            set_tool_indicator(arcpy.env.scratchWorkspace, False)
            trace = traceback.format_exc()
            merge_result['trace'] = trace
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
        set_tool_indicator(arcpy.env.scratchWorkspace, False)
        return

# END MergeCleanup
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

class BatchBuildName(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "BatchBuildName"
        self.description = "Iterate through SEGMENT and build PRIME_NAME and NAME_FULL from the 7 name parts"
        self.canRunInBackground = True
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="SEGMENT feature layer",
            name="SEGMENT_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        #
        param1 = arcpy.Parameter(
            displayName="SEG_NAME table",
            name="SEG_NAME_table",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input")

        #
        param2 = arcpy.Parameter(
            displayName="Database Connection",
            name="workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        param2.value = arcpy.env.workspace
        param2.enabled = False

        #
        param3 = arcpy.Parameter(
            displayName="Database Instance",
            name="instance",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["GIS7D_ABBOTT43", "GIS7T_ABBOTT43", "GIS7P_BARTON44", "GIS6P_BARTON44"]

        #
        param4 = arcpy.Parameter(
            displayName="Username",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        #
        param5 = arcpy.Parameter(
            displayName="Password",
            name="password",
            datatype="GPEncryptedString",
            parameterType="Required",
            direction="Input")

        #
        param6 = arcpy.Parameter(
            displayName="Parent Version",
            name="parent",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param6.filter.type = "ValueList"
        #param6.filter.list = ["DEFAULT"]

        param7 = arcpy.Parameter(
            displayName="Delete Existing Child Versions and Rebuilt Connections",
            name="delete_rebuild",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        params = [param0, param1, param2, param3, param4, param5, param6, param7]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):

        if not parameters[4].altered:
            sdedescribe = arcpy.Describe(arcpy.env.workspace)
            parameters[4].value = sdedescribe.connectionProperties.user

        sdedescribe = arcpy.Describe(arcpy.env.workspace)
        parameters[6].filter.list = [sdedescribe.connectionProperties.version]


        return

    def updateMessages(self, parameters):
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        if parameters[0].valueAsText == segmentfc:
            parameters[0].clearMessage()
        else:
            parameters[0].setErrorMessage('Inpout SEGMENT feature class does not match the SEGMENT feature class in the Current Workspace')

        if parameters[1].valueAsText == segnametab:
            parameters[1].clearMessage()
        else:
            parameters[1].setErrorMessage('Inpout SEG_NAME table class does not match the SEG_NAME table in the Current Workspace')

        return

    def execute(self, parameters, messages):
        global pyexe
        """The source code of the tool."""
        import traceback, os, datetime
        import sys, subprocess
        import numpy as np
        os.sys.path.append(os.path.dirname(__file__))
        import erebus
        from multiprocessing import Process, Lock, Queue
        arcpy.env.overwriteOutput = True
        import time

        arcpy.AddMessage(parameters[0].value)
        arcpy.AddMessage(parameters[1].value)

        count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
        count2 = int(arcpy.GetCount_management(segnametab).getOutput(0))

        ########################################################################
        ##
        batchresult = {'result': 'na'}



        try:

            #text = os.popen('C:\Users\oaxfarr\Documents\Python\PP4E-Examples-1.4\Examples\PP4E\System\helloshell.py').readlines()
            #arcpy.AddMessage(text)

            sdedescribe = arcpy.Describe(arcpy.env.workspace)
            arcpy.AddMessage("Database Username: {0}".format(sdedescribe.connectionProperties.user))
            ####################################################################
            ## Create the 8 Versions
            # 1) make the names
            ROAD_sde = parameters[2].value #"Database Connections\\ROAD@gis7t@1525.sde"
            v_names = ['road_child0', 'road_child1', 'road_child2','road_child3' ,'road_child4' ,'road_child5' ,'road_child6' ,'road_child7']
            v_names_full = []
            for v_name in v_names:
                nn = parameters[4].valueAsText.upper() + '.' + v_name
                v_names_full.append(nn)                              #v_names_full = ['ROAD.road_child0', 'ROAD.road_child1', 'ROAD.road_child2','ROAD.road_child3' ,'ROAD.road_child4' ,'ROAD.road_child5' ,'ROAD.road_child6' ,'ROAD.road_child7']


            if parameters[7].value == True:
                # 2) delete the old ones
                for version in arcpy.da.ListVersions(parameters[2].value):
                    if version.name in v_names_full:
                        arcpy.DeleteVersion_management(parameters[2].value, version.name)
                        arcpy.AddMessage('Deleted existing version: {0}'.format(version.name))

                parent = parameters[6].value
                #parent = arcpy.Describe(parameters[2].value).connectionProperties.version
                #parent = parameters[4].valueAsText + '.' + parameters[6].valueAsText

                # 3) create the versions
                for v_name in v_names:
                    arcpy.CreateVersion_management(parameters[2].value, parent, v_name, "PROTECTED")
                    arcpy.AddMessage('Created version: {0}, from parent: {1}'.format(v_name, parent))


            ####################################################################
            ## Connect to the 8 Versions
            Database_Connections = "Database Connections"
            p = 0
            for v_name in v_names:
                arcpy.CreateDatabaseConnection_management(Database_Connections, v_name, "ORACLE", parameters[3].value, "DATABASE_AUTH", parameters[4].value, parameters[5].value, "SAVE_USERNAME", "", "SDE", "TRANSACTIONAL", v_names_full[p], "")
                arcpy.AddMessage('Connected to version: {0}'.format(v_name))
                p +=1

            ####################################################################
            ## SEG_NAME Mulitprocessing
            bbnpath = os.path.join(os.path.dirname(__file__), 'BatchBuildName.py')
            pipe = subprocess.Popen([pyexe, bbnpath, 'segname_production', parameters[4].value, parameters[2].valueAsText], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
            (stdoutdata, stderrdata) = pipe.communicate()

            arcpy.AddMessage('\nSubprocess out messages "stdoutdata": {0}'.format(stdoutdata))
            arcpy.AddMessage('\nSubprocess error messages "stderrdata": {0}'.format(stderrdata))

            pipe.terminate()

            arcpy.AddMessage('\nSEG_NAME.NAME_FULL is complete\n____________________________________')


            ####################################################################
            ## PRIME_NAME Mulitprocessing
            arcpy.AddMessage('\n\nStarting to build PRIME_NAME...')

            pipe2 = subprocess.Popen([pyexe, bbnpath, 'primename_production', parameters[4].value, parameters[2].valueAsText], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
            (stdoutdata2, stderrdata2) = pipe2.communicate()

            arcpy.AddMessage('\nSubprocess out messages "stdoutdata": {0}'.format(stdoutdata2))
            arcpy.AddMessage('\nSubprocess error messages "stderrdata": {0}'.format(stderrdata2))

            pipe2.terminate()

            #sys.exit(0)

        except:
            trace = traceback.format_exc()
            batchresult['trace'] = trace
            batchresult['result'] = 'fail'
            arcpy.AddMessage(batchresult)

##        block2 = False
##        if block2 == True:
##            try:
##
##                ####################################################################
##                ## The update on SEG_NAME
##
##                def editprocess(workspace, table, fields, values, lock, stop_ed = True):
##                    import arcpy
##                    import datetime
##
##                    edit = arcpy.da.Editor(workspace)
##                    edit.startEditing()
##                    edit.startOperation()
##
####                    with lock:
####                        print 'child process {0} started at {1}...'.format(workspace, str(datetime.datetime.now()))
##
##                    try:
##                        for value in values:
##                            sql_query = "GlobalID = ".format(value[1])
##                            with arcpy.da.UpdateCursor(table, [fields], sql_query) as cursor:
##                                for row in cursor:
##                                    row[0] = value[0]
##                                    cursor.updateRow(row)
##
##                            edit.stopOperation()
##                        edit.stopEditing(stop_ed)
##                    except arcpy.ExecuteError:
##                        with lock:
##                            print arcpy.GetMessages()
##
####                    with lock:
####                        print 'child process {0} completed at {1}.'.format(workspace, str(datetime.datetime.now()))
##
##
##                ####################################################################
##                ## Define Variables
##
##
##                #workspace = r'Database Connections\ROAD@gis7t@1525.sde'
##                #table = r'Database Connections\ROAD@gis7t@1525.sde\ROAD.SEG_NAME'
##                fields = 'NAME_FULL'
##                # "workspace", "start", "end", "table"
##
##                v_names = ['road_child0', 'road_child1', 'road_child2','road_child3' ,'road_child4' ,'road_child5' ,'road_child6' ,'road_child7']
##                wksps = []
##                tables = []
##                for v_name in v_names:
##                    wksps.append(os.path.join('Database Connections', v_name + '.sde'))
##                    tables.append(os.path.join('Database Connections', v_name + '.sde', parameters[4].value + '.SEG_NAME'))
##
##                # break up the job
##                steps = np.round(np.linspace(start=0, stop = snlen, num = 9))  #array([      0.,   85333.,  170666.,  255998.,  341331.,  426664., 511996.,  597329.,  682662.])
##                steps = steps.astype(np.int)
##                steps = steps.tolist()
##                starts = steps[0:8]
##                ends = steps[1:9]
##
##                inputsvars = zip(wksps, starts, ends, tables)
##                arcpy.AddMessage('Variable inputvars: {0}'.format(inputsvars[0:5]))
##                nameglobal = zip(fullname,sn_globalid)
##                arcpy.AddMessage('Variable nameglobal: {0}'.format(nameglobal[0:5]))
##
##                lock2 = Lock()
##
##                ####################################################################
##                ## Run the processes
##                print('Main editing process starting...')
##                # (workspace, table, fields, values, lock, stop_ed = True)
##                gg = 0
##                ps = []
##                for inv in inputsvars:
##                    if gg == 7:
##                        end = inv[2] + 1
##                    else:
##                        end = inv[2]
##                    arcpy.AddMessage('\nChild process: "{0}" started at {1}...'.format(inv[0], str(datetime.datetime.now())))
##
##                    p = Process(target=editprocess, args=(inv[0], inv[3], fields, nameglobal[inv[1]:end], lock2))
##                    p.start()
##                    gg += 1
##                    ps.append(p)
##
##                b = 0
##                for p in ps:
##                    print 'p joining...'
##                    p.join()
##                    arcpy.AddMessage('child process {0} ended at {1}...'.format(inputsvars[b], str(datetime.datetime.now())))
##                    b += 1
##
##                with lock2:
##                    print('Main editing process exit.')
##
##
##            except:
##                trace2 = traceback.format_exc()
##                batchresult['trace2'] = trace2
##                batchresult['result'] = 'fail'
##                arcpy.AddMessage(batchresult)
##                try: nmrow; del nmrow
##                except: pass
##                try: nmcursor; del nmcursor
##                except: pass
##                try: row; del row
##                except: pass
##                try: cursor; del cursor
##                except: pass

        return

# END BatchBuildName
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\


Record_lrs = []
Records_lrs = []
currentR_lrs = ""
Record_sld = []
Records_sld = []
currentR_sld = ""
RecordsCleared_lrs = {'status': ('', False), 'segguid': '', 'altered': False}
RecordsCleared_sld = {'status': ('', False), 'sri': '', 'altered': False}
LRS_ID = ''

class LRS(object):
    def __init__(self):

        #print "\ninit1 \n  RecordsCleared_lrs: {0}\n  Records_lrs {1}".format(RecordsCleared_lrs, Records_lrs)
        """Define the tool (tool name is the name of the class)."""
        self.label = "LRS"
        self.description = "Add, Update, or Delete LRS records"
        self.canRunInBackground = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
        #global Record_lrs, Records_lrs, currentR_lrs, Record_sld, Records_sld, currentR_sld, RecordsCleared_lrs, RecordsCleared_sld, LRS_ID

        import traceback

        self.Records = []
        self.RecordsDict = {}
        self.Records_sld = []
        self.RecordsDict_sld = {}
        self.sri = []

        try:
            global Record_lrs, Records_lrs, currentR_lrs, Record_sld, Records_sld, currentR_sld, RecordsCleared_lrs, RecordsCleared_sld, LRS_ID
            lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
            if os.path.exists(lrspath):
                with open(lrspath,'rb') as lrsopen:
                    lrs_pickle = pickle.load(lrsopen)

                if lrs_pickle['linreftab'][0]:
                    self.Records = lrs_pickle['linreftab'][1]
                    self.RecordsDict = lrs_pickle['linreftab'][2]
                    self.sri = lrs_pickle['linreftab'][1][0][2]
                if lrs_pickle['sldtab'][0]:
                    self.Records_sld = lrs_pickle['sldtab'][1]
                    self.RecordsDict_sld = lrs_pickle['sldtab'][2]
                if lrs_pickle['segment'][0]:
                    self.segguid = lrs_pickle['segment'][1]

                self.lrs_pickle = lrs_pickle

                if LRS_ID == '':
                    LRS_ID = lrs_pickle['ID']
                elif LRS_ID == lrs_pickle['ID']:
                    pass
                elif LRS_ID != lrs_pickle['ID']:# new ID, clear out vars, reassign
                    Record_lrs = []
                    Records_lrs = []
                    currentR_lrs = ""
                    Record_sld = []
                    Records_sld = []
                    currentR_sld = ""
                    RecordsCleared_lrs = {'status': ('', False), 'segguid': '', 'altered': False}
                    RecordsCleared_sld = {'status': ('', False), 'sri': '', 'altered': False}
                    LRS_ID = lrs_pickle['ID']

        except:
            print(traceback.format_exc())
            Record_lrs = []
            Records_lrs = []
            currentR_lrs = ""
            Record_sld = []
            Records_sld = []
            currentR_sld = ""
            RecordsCleared_lrs = {'status': ('', False), 'segguid': '', 'altered': False}
            RecordsCleared_sld = {'status': ('', False), 'sri': '', 'altered': False}


##        if segmentfc:
##            with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
##                for row in cursor:
##                    self.segguid = row[0]
##
##            seg_sql = erebus.sqlGUID("SEG_GUID", self.segguid)
##            gg = 1                                  #    0      1           2           3               4               5           6       7
##            with arcpy.da.SearchCursor(linreftab, ["SEG_GUID", "SRI", "LRS_TYPE_ID", "SEG_TYPE_ID", "MILEPOST_FR", "MILEPOST_TO", "RCF","GLOBALID"], seg_sql) as cursor:  # insert a cursor to access fields, print names
##                for row in cursor:
##                    self.Records.append(['Record {0}'.format(gg),row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
##                    self.RecordsDict['Record {0}'.format(gg)] = [row[7],""]
##                    if row[1]:
##                        srilist.append(row[1])
##                    gg += 1
##
##            if srilist:
##                [self.sri.append(item) for item in srilist if item not in self.sri]  #remove duplicates
##                gg = 1
##                for i,v in enumerate(self.sri):
##                    sri_sql = erebus.sqlGUID("SRI", v) #  0           1             2            3               4               5           6
##                    with arcpy.da.SearchCursor(sldtab, ["SRI", "ROUTE_TYPE_ID", "SLD_NAME", "SLD_COMMENT", "SLD_DIRECTION", "SIGN_NAME","GLOBALID"], sri_sql) as cursor2:
##                        for row2 in cursor2:
##                            self.Records_sld.append(['Record {0}'.format(gg),row2[0], row2[1], row2[2], row2[3], row2[4], row2[5]])
##                            self.RecordsDict_sld['Record {0}'.format(gg)] = [row2[6],""]
##                    gg += 1
##
##            #################
##            if RecordsCleared_lrs['status'][0] == self.segguid:  # if youre in the same tool, don't do anything. If it is new tool, clear it out
##                print('  1')
##                pass
##            else:
##                RecordsCleared_lrs['status'] = ('', False)
##                print('  2')
##
##            if RecordsCleared_lrs['segguid'] == self.segguid:
##                print('  3')
##                pass
##            elif RecordsCleared_lrs['segguid'] == '':
##                RecordsCleared_lrs['segguid'] = self.segguid
##                print('  4')
##            else: #its not the smae, and not empty, so it is a new tool, so clear out the garbage
##                Records_lrs = []
##                Record_lrs = []
##                currentR_lrs = ""
##                RecordsCleared_lrs['segguid'] = self.segguid
##                print('  5')
##
##            ################
##            if RecordsCleared_sld['status'][0] == self.sri:  # if youre in the same tool, don't do anything. If it is new tool, clear it out
##                pass
##            else:
##                RecordsCleared_sld['status'] = ('', False)
##            if RecordsCleared_sld['sri'] == self.sri:
##                pass
##            elif RecordsCleared_sld['sri'] == '':
##                RecordsCleared_sld['sri'] = self.sri
##            else: #its not the smae, and not empty, so it is a new tool, so clear out the garbage
##                Records_sld = []
##                Record_sld = []
##                currentR_sld = ""
##                RecordsCleared_sld['sri'] = self.sri

        #print "init2 \n  RecordsCleared_lrs: {0}\n  Records_lrs {1}".format(RecordsCleared_lrs, Records_lrs)

    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Add and Delete LINEAR_REF Records",
            name="lrs_value_table",
            datatype="GPValueTable",
            parameterType="Optional",
            direction="Input")
        param0.columns = [['String', 'Record ID'], ['String', '*SEG_GUID'], ['String', 'SRI'], ['GPLong','*LRS_TYPE_ID'], ['String', '*SEG_TYPE_ID'], ['GPDouble', 'MILEPOST_FR'], ['GPDouble', 'MILEPOST_TO'], ['String', 'RCF']]

        #
        param1 = arcpy.Parameter(
            displayName="Current LINEAR_REF Record",
            name="current_record",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param1.filter.type = "ValueList"


        param2 = arcpy.Parameter(
            displayName="SRI",
            name="SRI",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param3 = arcpy.Parameter(
            displayName="LRS_TYPE_ID",
            name="LRS_TYPE_ID",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = [1,2,3,4,5]
        #param2.value = "1 - NJDOT Multi-Centerline"
        #param2.enabled = False

        #
        param4 = arcpy.Parameter(
            displayName="SEG_TYPE_ID",
            name="SEG_TYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param4.filter.type = "Optional"
        param4.filter.list = ["P", "S", "E", "ES", "AD"]
        #param3.value = "P - Primary"

        #
        param5 = arcpy.Parameter(
            displayName="MILEPOST_FR",
            name="MILEPOST_FR",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")

        #
        param6 = arcpy.Parameter(
            displayName="MILEPOST_TO",
            name="MILEPOST_TO",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")


        #
        param7 = arcpy.Parameter(
            displayName="RCF",
            name="RCF",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")


        ########################################################################
        ## SLD

        param8 = arcpy.Parameter(
            displayName="Add and Delete SLD_ROUTE Records",
            name="lrs_value_table2",
            datatype="GPValueTable",
            parameterType="Optional",
            direction="Input")
        param8.columns = [['String', 'Record ID'], ['String', '*SRI'], ['GPLong','*ROUTE_TYPE_ID'], ['String', 'SLD_NAME'], ['String', 'SLD_COMMENT'], ['String', 'SLD_DIRECTION'], ['String', 'SIGN_NAME']]

        #
        param9 = arcpy.Parameter(
            displayName="Current SLD Record",
            name="current_record2",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param9.filter.type = "ValueList"

        #
        param10 = arcpy.Parameter(
            displayName="SRI",
            name="SRI2",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param11 = arcpy.Parameter(
            displayName="ROUTE_TYPE_ID",
            name="ROUTE_TYPE_ID",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param11.filter.type = "ValueList"
        param11.filter.list = [1,2,3,4,5,6,7,8,9,10]

        #
        param12 = arcpy.Parameter(
            displayName="SLD_NAME",
            name="SLD_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param13 = arcpy.Parameter(
            displayName="SLD_COMMENT",
            name="SLD_COMMENT",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #
        param14 = arcpy.Parameter(
            displayName="SLD_DIRECTION",
            name="SLD_DIRECTION",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param14.filter.type = "ValueList"
        param14.filter.list = ["<null>", "North to South", "South to North", "East to West", "West to East"]

        #
        param15 = arcpy.Parameter(
            displayName="SIGN_NAME",
            name="SIGN_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

##        param52.filter.list = ["1 - Interstate", "2 - US Route", "3 - State Route", "4 - Highway Authority Route", "5 - County 500 Route", "6 - Other County Route", "7 - Local Road", "8 - Ramp", "9 - Alley", "10 - Park/Military"]

        params = [param0,param1,param2,param3,param4,param5,param6,param7,param8,param9,param10,param11,param12,param13,param14,param15]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        import erebus
        global Record_lrs, Records_lrs, currentR_lrs, Record_sld, Records_sld, currentR_sld, RecordsCleared_lrs, RecordsCleared_sld

        #import
        lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
        if os.path.exists(lrspath):
            with open(lrspath,'rb') as lrsopen:
                lrs_pickle = pickle.load(lrsopen)
        lrs_pickle['UPDATECOUNT'] += 1
        updatecount = lrs_pickle['UPDATECOUNT']
        #print('\nUPDATECOUNT: {0}'.format(updatecount))
        #output
        lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
        with open(lrspath, 'wb') as output:
            pickle.dump(lrs_pickle, output, -1)



        #print("\nupdateParameters1 \n  RecordsCleared_lrs: {0} \n  param0.values: {1}, \n  Records_lrs: {2}\n  parameters[0].altered: {3}".format(RecordsCleared_lrs, parameters[0].values, Records_lrs, parameters[0].altered) )


        ########################################################################
        ########################################################################
        ## LINEAR_REF

##        if Records_lrs and not parameters[0].values:
##            currentR_lrs = ""
##        elif not parameters[0].altered and self.Records: # and not Records: # first time around
##            parameters[0].values = self.Records
##            Records_lrs = self.Records
##        else:
##            if parameters[0].values:
##                Records_lrs = parameters[0].values
##                for uu in range(len(Records_lrs)):
##                    Records_lrs[uu][1] = self.segguid
##                parameters[0].values = Records_lrs

##        if Records_lrs and not parameters[0].values and RecordsCleared_lrs['segguid'] == self.segguid and RecordsCleared_lrs['altered'] and len(Records_lrs) != len(self.Records):
##            print('CHANGE \n  Records_lrs: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records_lrs, parameters[0].values, parameters[0].altered, self.Records))
##            RecordsCleared_lrs['status'] = (self.segguid,True)
##        elif not parameters[0].altered and self.Records and not RecordsCleared_lrs['status'][1]: # and not Records: # first time around
##            parameters[0].values = self.Records
##            Records_lrs = self.Records
##            print('  U1')
##        else:
##            Records_lrs = parameters[0].values
##            if Records_lrs:
##                for uu in range(len(Records_lrs)):
##                    Records_lrs[uu][1] = self.segguid
##            parameters[0].values = Records_lrs
##            print('  U2')
  #Records_lrs: [['Record 1', u'{02B5FF1C-1708-11E3-B5F2-0062151309FF}', u'00000444__', 2, u'P', 76.847, 76.301, None], ['Record 2', u'{02B5FF1C-1708-11E3-B5F2-0062151309FF}', u'00000444__', 1, u'P', 76.301, 76.847, None], ['Record 3', u'{02B5FF1C-1708-11E3-B5F2-0062151309FF}', u'00000444__', 3, u'P', 76.301, 76.847, None]]


        if not Records_lrs and not self.Records:
            #Records_lrs = [['', '', '', '', '', None, None, None]]
            Records_lrs = [['Record 1', self.segguid, '', '', '', None, None, None]]
            parameters[0].values = Records_lrs
        if not Records_lrs and not parameters[0].values and not parameters[0].altered and not RecordsCleared_lrs['status'][1] and self.Records and not self.lrs_pickle['lrslocked']:  # first population
            parameters[0].values = self.Records
            Records_lrs = self.Records
            #print('  LRS 0 \n  Records_lrs: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records_lrs, parameters[0].values, parameters[0].altered, self.Records))
            #import
            lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
            if os.path.exists(lrspath):
                with open(lrspath,'rb') as lrsopen:
                    lrs_pickle = pickle.load(lrsopen)
            lrs_pickle['lrslocked'] = True
            #output
            with open(lrspath, 'wb') as output:
                pickle.dump(lrs_pickle, output, -1)
        elif not Records_lrs and not parameters[0].values and not parameters[0].altered and not RecordsCleared_lrs['status'][1] and self.Records and self.lrs_pickle['lrslocked']: #unlocked
            #print('  LRS 1 \n  Records_lrs: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records_lrs, parameters[0].values, parameters[0].altered, self.Records))
            pass
        else:
            if Records_lrs and parameters[0].values:
                if len(Records_lrs) == len(parameters[0].values):  # no change
                    #Records_lrs = parameters[0].values
                    if Records_lrs:
                        for uu in range(len(Records_lrs)):
                            Records_lrs[uu][1] = self.segguid
                    parameters[0].values = Records_lrs
                    #print('  LRS 2 \n  Records_lrs: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records_lrs, parameters[0].values, parameters[0].altered, self.Records))
                if len(Records_lrs) < len(parameters[0].values):  # insert
                    Records_lrs = parameters[0].values
                    if Records_lrs:
                        for uu in range(len(Records_lrs)):
                            Records_lrs[uu][1] = self.segguid
                    parameters[0].values = Records_lrs
                    #print('  LRS 2 \n  Records_lrs: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records_lrs, parameters[0].values, parameters[0].altered, self.Records))

                if len(Records_lrs) > len(parameters[0].values):
                    #print 'Delete !!!!'
                    Records_lrs = parameters[0].values

## #                 0      1           2           3               4               5           6       7
##            "SEG_GUID", "SRI", "LRS_TYPE_ID", "SEG_TYPE_ID", "MILEPOST_FR", "MILEPOST_TO", "RCF","GLOBALID"]
##(['Record {0}',row[0], row[1], row[2],           row[3],         row[4],       row[5],    row[6]])
##      0           1      2       3                 4               5              6          7


        #################
        ## Updates
        try:
            if parameters[0].values:
                parameters[1].filter.list = [val[0] for val in parameters[0].values]
            else:
                parameters[1].filter.list = []
        except:
            parameters[1].filter.list = []

        if currentR_lrs and parameters[1].value:
            if currentR_lrs == parameters[1].value:  # they match on this refresh. So go through and only update things that are different in Records

                if parameters[2].value and Record_lrs[2] != parameters[2].value:
                    Record_lrs[2] = parameters[2].value
                if parameters[3].value and  Record_lrs[3] != parameters[3].value:
                    Record_lrs[3] = parameters[3].value
                if parameters[4].value and  Record_lrs[4] != parameters[4].value:
                    Record_lrs[4] = parameters[4].value
##                if parameters[5].value and  Record_lrs[5] != parameters[5].value:
##                    Record_lrs[5] = parameters[5].value
##                if parameters[6].value and  Record_lrs[6] != parameters[6].value:
##                    Record_lrs[6] = parameters[6].value
                #print 'From value: {0}, from type: {1}'.format(parameters[5].value, type(parameters[5].value))

                if Record_lrs[5] != parameters[5].value:
                    Record_lrs[5] = parameters[5].value
                if Record_lrs[6] != parameters[6].value:
                    Record_lrs[6] = parameters[6].value

                if parameters[7].value and  Record_lrs[7] != parameters[7].value:
                    Record_lrs[7] = parameters[7].value

                #if there is a value in Record, but no value in the field, take the Record value
                if not parameters[2].value and Record_lrs[2]:
                    parameters[2].value = Record_lrs[2]
                if not parameters[3].value and Record_lrs[3]:
                    parameters[3].value = Record_lrs[3]
                if not parameters[4].value and Record_lrs[4]:
                    parameters[4].value = Record_lrs[4]
                if not parameters[5].value and parameters[5].value != 0 and Record_lrs[5]:
                    parameters[5].value = Record_lrs[5]
                if not parameters[6].value and parameters[6].value != 0 and Record_lrs[6]:
                    parameters[6].value = Record_lrs[6]
                if not parameters[7].value and Record_lrs[7]:
                    parameters[7].value = Record_lrs[7]

                i = 0
                for r in Records_lrs:
                    if parameters[1].value == r[0]:
                        Records_lrs[i] = Record_lrs
                    i += 1
                parameters[0].values = Records_lrs

            if currentR_lrs != parameters[1].value:  #if the "Current Record" is refreshed, and doesnt match the last one...refresh the fields
                currentR_lrs = parameters[1].value
                for r in Records_lrs:
                    if parameters[1].value == r[0]:
                        Record_lrs = r
                parameters[2].value = Record_lrs[2]
                parameters[3].value = Record_lrs[3]
                parameters[4].value = Record_lrs[4]
                parameters[5].value = Record_lrs[5]
                parameters[6].value = Record_lrs[6]
                parameters[7].value = Record_lrs[7]

        if not currentR_lrs:  # the original field population...now we have currentR in memory
            if parameters[1].value and parameters[1].altered:
                currentR_lrs = parameters[1].value
                for r in Records_lrs:
                    if parameters[1].value == r[0]:
                        Record_lrs = r
                if Record_lrs[2]:
                    parameters[2].value = Record_lrs[2]
                if Record_lrs[3]:
                    parameters[3].value = Record_lrs[3]
                if Record_lrs[4]:
                    parameters[4].value = Record_lrs[4]
                if Record_lrs[5] or Record_lrs[5] == 0:
                    # print 'Record_lrs: {0}'.format(Record_lrs)
                    # print 'Record_lrs[5]: {0}'.format(Record_lrs[5])
                    # print 'type: {0}'.format(type(Record_lrs[5]))
                    parameters[5].value = Record_lrs[5]
                if Record_lrs[6] or Record_lrs[6] == 0:
                    parameters[6].value = Record_lrs[6]
                if Record_lrs[7]:
                    parameters[7].value = Record_lrs[7]

        ########################################################################
        ########################################################################
        ## SLD_ROUTE

        #                                                  ["SRI",  "ROUTE_TYPE_ID", "SLD_NAME", "SLD_COMMENT", "SLD_DIRECTION", "SIGN_NAME","GLOBALID"], sri_sql) as cursor2:
        # self.Records_sld.append(['Record {0}'.format(gg),row[0],       row[1],        row[2],      row[3],         row[4],       row[5]])
        #                                      0               1               2               3           4               5           6

        #print('SLD updateParameters1 \n  Records_sld: {0} \n  param8.values: {1} \n  param8.altered: {2}\n  self.Records_sld: {3}\n  RecordsCleared_sld: {4}'.format(Records_sld, parameters[8].values, parameters[8].altered, self.Records_sld, RecordsCleared_sld))

        #[['Record 1', u'15000085__', 6, u'OCEAN COUNTY 85', u'Ocean County Ref # 85', u'North to South', u'Western Boulevard']]

        if not Records_sld and not self.Records_sld:
            Records_sld = [['Record 1', '', None, '', '', '', '']]
            parameters[8].values = Records_sld
            print '1'
        elif not Records_sld and not parameters[8].values and not parameters[8].altered and not RecordsCleared_sld['status'][1] and self.Records_sld and not self.lrs_pickle['sldlocked']:  # first population
            parameters[8].values = self.Records_sld
            Records_sld = self.Records_sld
            #print('  SLD 0 \n  Records_sld: {0} \n  param8.values: {1} \n  param8.altered: {2}\n  self.Records_sld: {3}'.format(Records_sld, parameters[8].values, parameters[8].altered, self.Records_sld))
            #import
            lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
            if os.path.exists(lrspath):
                with open(lrspath,'rb') as lrsopen:
                    lrs_pickle = pickle.load(lrsopen)
            lrs_pickle['sldlocked'] = True
            #output
            with open(lrspath, 'wb') as output:
                pickle.dump(lrs_pickle, output, -1)

            print '2'
        elif not Records_sld and not parameters[8].values and not parameters[8].altered and not RecordsCleared_sld['status'][1] and self.Records_sld and self.lrs_pickle['sldlocked']: #unlocked
            #print('  SLD 1 \n  Records_sld: {0} \n  param8.values: {1} \n  param8.altered: {2}\n  self.Records_sld: {3}'.format(Records_sld, parameters[8].values, parameters[8].altered, self.Records_sld))
            pass
            print '3'
        else:
            if Records_sld and parameters[8].values:
                if len(Records_sld) == len(parameters[8].values):  # no change
                    #Records_lrs = parameters[0].values
##                    if Records_lrs:
##                        for uu in range(len(Records_sld)):
##                            Records_sld[uu][1] = self.sri
                    parameters[8].values = Records_sld

                if len(Records_sld) < len(parameters[8].values):  # insert
                    Records_sld = parameters[8].values
                    parameters[8].values = Records_sld

                if len(Records_sld) > len(parameters[8].values):
                    print 'sld delete'
                    Records_sld = parameters[8].valuues

            print '4'


        #################
        ## Updates
        try:
            if parameters[8].values:
                parameters[9].filter.list = [val[0] for val in parameters[8].values]
            else:
                parameters[9].filter.list = []
        except:
            parameters[9].filter.list = []

        if currentR_sld and parameters[9].value:
            if currentR_sld == parameters[9].value:  # they match on this refresh. So go through and only update things that are different in Records

                # if there is a value in the field and its different...update Record
                if parameters[10].value and Record_sld[1] != parameters[10].value:
                    Record_sld[1] = parameters[10].value
                if parameters[11].value and Record_sld[2] != parameters[11].value:
                    if parameters[11].value > 7:
                        Record_sld[5] = None
                        parameters[14].value = None
                    Record_sld[2] = parameters[11].value
                if parameters[12].value and Record_sld[3] != parameters[12].value:
                    Record_sld[3] = parameters[12].value
                if parameters[13].value and Record_sld[4] != parameters[13].value:
                    Record_sld[4] = parameters[13].value
                if parameters[14].value and Record_sld[5] != parameters[14].value:
                    if parameters[11].value > 7:
                        Record_sld[5] = None
                        parameters[14].value = None
                    else:
                        Record_sld[5] = parameters[14].value
                if parameters[15].value and Record_sld[6] != parameters[15].value:
                    Record_sld[6] = parameters[15].value

                #if there is a value in Record, but no value in the field, take the Record value
                if not parameters[10].value and Record_sld[1]:
                    parameters[10].value = Record_sld[1]
                if not parameters[11].value and Record_sld[2]:
                    parameters[11].value = Record_sld[2]
                if not parameters[12].value and Record_sld[3]:
                    parameters[12].value = Record_sld[3]
                if not parameters[13].value and Record_sld[4]:
                    parameters[13].value = Record_sld[4]
                if not parameters[14].value and Record_sld[5]:
                    parameters[14].value = Record_sld[5]
                if not parameters[15].value and Record_sld[6]:
                    parameters[15].value = Record_sld[6]

                i = 0
                for r in Records_sld:
                    if parameters[9].value == r[0]:
                        Records_sld[i] = Record_sld
                    i += 1
                parameters[8].values = Records_sld

            if currentR_sld != parameters[9].value:  #if the "Current Record" is refreshed, and doesnt match the last one...refresh the fields
                currentR_sld = parameters[9].value
                for r in Records_sld:
                    if parameters[9].value == r[0]:
                        Record_sld = r
                parameters[10].value = Record_sld[1]
                parameters[11].value = Record_sld[2]
                parameters[12].value = Record_sld[3]
                parameters[13].value = Record_sld[4]
                parameters[14].value = Record_sld[5]
                parameters[15].value = Record_sld[6]

        if not currentR_sld:  # the original field population...now we have currentR in memory
            if parameters[8].values and parameters[9].altered:
                currentR_sld = parameters[9].value
                for r in Records_sld:
                    if parameters[9].value == r[0]:
                        Record_sld = r

                parameters[10].value = Record_sld[1]
                if Record_sld[2]:
                    parameters[11].value = Record_sld[2]
                if Record_sld[3]:
                    parameters[12].value = Record_sld[3]
                if Record_sld[4]:
                    parameters[13].value = Record_sld[4]
                if Record_sld[5]:
                    parameters[14].value = Record_sld[5]
                if Record_sld[6]:
                    parameters[15].value = Record_sld[6]

        RecordsCleared_lrs['altered'] = parameters[0].altered
        RecordsCleared_sld['altered'] = parameters[8].altered

        #print("updateParameters2\n  RecordsCleared_lrs: {0} \n  parameters[0].values: {1}, \n  Records_lrs {2}\n  parameters[0].altered: {3}".format(RecordsCleared_lrs, parameters[0].values, Records_lrs,parameters[0].altered) )
        #print('SLD updateParameters2 \n  Records_sld: {0} \n  param8.values: {1} \n  param8.altered: {2}\n  self.Records_sld: {3}\n  RecordsCleared_sld: {4}'.format(Records_sld, parameters[8].values, parameters[8].altered, self.Records_sld, RecordsCleared_sld))

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        #print("\nupdateMessages1\n  RecordsCleared_lrs: {0}, \n  parameters[0].values: {1}, \n  Records_lrs: {2}".format(RecordsCleared_lrs, parameters[0].values, Records_lrs) )

        import re

        if parameters[1].value:
            if parameters[3].value in (1,2,3,4,5):
                parameters[3].clearMessage()
            else:
                parameters[3].setErrorMessage("Please Choose an LRS_TYPE_ID")
            if parameters[4].value in ("P","S","E","ES","AD"):
                parameters[4].clearMessage()
            else:
                parameters[4].setErrorMessage("Please Choose a SEG_TYPE_ID")
##            if parameters[5].value:
##                parameters[5].clearMessage()
##            else:
##                parameters[5].setErrorMessage("Please enter a valid MILEPOST_FR value")
##            if parameters[6].value:
##                parameters[6].clearMessage()
##            else:
##                parameters[6].setErrorMessage("Please enter a valid MILEPOST_TO value")

        if parameters[9].value:
            if parameters[10].value:
                parameters[10].clearMessage()
            else:
                parameters[10].setErrorMessage("Please enter an SRI")
            if parameters[11].value in (1,2,3,4,5,6,7,8,9,10):
                parameters[11].clearMessage()
            else:
                parameters[11].setErrorMessage("Please Choose a ROUTE_TYPE_ID")
            if parameters[11].value < 7 and parameters[14].value not in ("North to South", "South to North", "East to West", "West to East"):
                parameters[14].setErrorMessage("Please Choose an SLD_DIRECTION")
            elif parameters[11].value >= 7 and parameters[14].value in ("North to South", "South to North", "East to West", "West to East"):
                parameters[14].setErrorMessage("Please make SLD_DIRECTION <null>")
            else:
                parameters[14].clearMessage()

        walkXsegname = {1: 'SEG_GUID', 2: 'SRI', 3: 'LRS_TYPE_ID', 4: 'SEG_TYPE_ID', 5: 'MILEPOST_FR', 6: 'MILEPOST_TO', 7: 'RCF'}
        lre = False
        lrerror = {1: 'If SYMBOL_TYPE is a ramp, then SRI must be 17 characters long.', 2: 'SRI must not contain spaces', 3: 'SRI must be 10 characters long.', 4: 'SRI should have "__" in position 9 and 10'}
        err = False
        if parameters[0].values:
            for rec in parameters[0].values:
                ss = re.search(' ',rec[2])
                if rec[3]:
                    if rec[3] not in (1,2,3,4,5):
                        parameters[0].setErrorMessage('Missing Required Value in {0} in {1}'.format(walkXsegname[3], rec[0]))
                        err = True; break
                    if rec[3] == 1 and rec[5] and rec[6]:
                        if rec[5] > rec[6]:
                            parameters[0].setErrorMessage('If LRS_TYPE is 1, then MP_FR must be less than MP_TO. Error in {0} in {1}'.format(walkXsegname[3], rec[0]))
                            err = True; break
                elif rec[4]:
                    if rec[4] not in ("P","S","E","ES","AD"):
                        parameters[0].setErrorMessage('Missing Required Value in {0} in {1}'.format(walkXsegname[4], rec[0]))
                        err = True; break
                elif rec[5] in (None, 'None') or rec[6] in (None, 'None'):
                    parameters[0].setErrorMessage('Missing Required Value in {0} in {1}'.format(walkXsegname[5], rec[0]))
                    err = True; break
                if rec[5] < 0 and rec[4] in ("P","S","E","ES"):
                    parameters[0].setErrorMessage('Negative MP values are only allowed when SEG_TYPE is "AD". Error in {0} in {1}'.format(walkXsegname[5], rec[0]))
                    err = True; break
                if rec[6] < 0 and rec[4] in ("P","S","E","ES"):
                    parameters[0].setErrorMessage('Negative MP values are only allowed when SEG_TYPE is "AD". Error in {0} in {1}'.format(walkXsegname[5], rec[0]))
                    err = True; break
                if (rec[5] or rec[5] == 0) and (rec[6] or rec[6] == 0):
                    if rec[5] == 0 and rec[6] == 0:
                        pass
                    elif rec[5] == rec[6]:
                        parameters[0].setWarningMessage('Milepost values are equal, which is acceptable but rare.')
                        err = True; break
                if rec[2] and ss:
                    parameters[0].setErrorMessage('{0} in {1}'.format(lrerror[2], rec[0]))
                    err = True; break
                if rec[2]:
                    if len(rec[2]) not in (10, 17):
                        parameters[0].setErrorMessage('SRI must be 10 or 17 characters long in {0}'.format(rec[0]))
                        err = True; break
                if rec[3] == 2:
                    if rec[2]:
                        if len(rec[2]) == 10:
                            if rec[2][9] != '_':
                                parameters[0].setErrorMessage('Invalid SRI Value in {0}. If LRS_TYPE is 2, then position 10 must be "_" '.format(rec[0]))
                                err = True; break
            if not err:
                parameters[0].clearMessage()


        walkXsld = {1: 'SRI', 2: 'ROUTE_TYPE_ID', 3: 'SLD_NAME', 4: 'SLD_COMMENT', 5: 'SLD_DIRECTION', 6: 'SIGN_NAME'}
        err2 = False
        if parameters[8].values:
            for rec2 in parameters[8].values:
                ss2 = re.search(' ',rec2[1])
                if rec2[1] and ss2:
                    parameters[8].setErrorMessage('{0} in {1}'.format(lrerror[2], rec2[0]))
                    err = True; break
                if rec2[1] and rec2[2]:
                    if  rec2[2] == 8 and len(rec2[1]) != 17 :
                        parameters[8].setErrorMessage('SRI must be 17 characters long in {0}'.format(rec2[0]))
                        err = True; break
                    if  rec2[2] != 8 and len(rec2[1]) != 10 :
                        parameters[8].setErrorMessage('SRI must be 10 characters long in {0}'.format(rec2[0]))
                        err = True; break
                if rec2[2]:
                    if rec2[2] not in (1,2,3,4,5,6,7,8,9,10):
                        parameters[8].setErrorMessage('Missing Required Value in {0} in {1}'.format(walkXsld[2], rec2[0]))
                        err2 = True; break
                elif rec2[2] and rec2[5]:
                    if rec2[2] < 7 and rec2[5] not in ("North to South", "South to North", "East to West", "West to East"):
                        parameters[8].setErrorMessage('Missing Required Value in {0} in {1}'.format(walkXsld[5], rec2[0]))
                        err2 = True; break
                    elif rec2[2] >= 7 and rec2[5]:
                        parameters[8].setErrorMessage('Please make SLD_DIRECTION a blank (clear the field) in {0} in {1}'.format(walkXsld[5], rec2[0]))
                        err2 = True; break
            if not err2:
                parameters[8].clearMessage()

        #print("updateMessages2 \n  RecordsCleared_lrs: {0}, \n  parameters[0].values {1}, \n  Records_lrs: {2}".format(RecordsCleared_lrs, parameters[0].values, Records_lrs) )

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        #arcpy.AddMessage('\nexecute ')
        #print("\nexecute1 \n  RecordsCleared_lrs: {0}, \n  Records_lrs: {1}".format(RecordsCleared_lrs, Records_lrs) )
        import os, sys, traceback
        import numpy as np
        global Record_lrs, Records_lrs, currentR_lrs, Record_sld, Records_sld, currentR_sld, RecordsCleared_lrs, RecordsCleared_sld

        lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
        if os.path.exists(lrspath):
            with open(lrspath,'rb') as lrsopen:
                lrs_pickle = pickle.load(lrsopen)
        updatecount = lrs_pickle['UPDATECOUNT']


        if arcpy.GetInstallInfo()['Version'] == '10.2.1':
            if updatecount <= 4:
                if lrs_pickle['linreftab'][0]:
                    RecordsValues_lrs = lrs_pickle['linreftab'][1]
                    #self.Records = lrs_pickle['linreftab'][1]
                    #self.RecordsDict = lrs_pickle['linreftab'][2]
                    #self.sri = lrs_pickle['linreftab'][1][2]
                else:
                    RecordsValues_lrs = lrs_pickle['linreftab'][0]
                if lrs_pickle['sldtab'][0]:
                    RecordsValues_sld = lrs_pickle['sldtab'][1]
                    #self.RecordsDict_sld = lrs_pickle['sldtab'][2]
                else:
                    RecordsValues_sld = lrs_pickle['sldtab'][0]
                if lrs_pickle['segment'][0]:
                    pass
                    #self.segguid = lrs_pickle['segment'][1]
                lrs_pickle = lrs_pickle
            else:
                RecordsValues_lrs = parameters[0].values
                if RecordsValues_lrs:
                    for i,v in enumerate(RecordsValues_lrs):
                        #print(i,v)
                        if v[5] == 0.0:
                            #print('Here it is: {0}'.format(RecordsValues_lrs))
                            RecordsValues_lrs[i][5] = 0.0
                RecordsValues_sld = parameters[8].values

        if arcpy.GetInstallInfo()['Version'] == '10.2.2' or arcpy.GetInstallInfo()['Version'] == '10.3' or arcpy.GetInstallInfo()['Version'] == '10.3.1':
            if updatecount <= 3:
                if lrs_pickle['linreftab'][0]:
                    RecordsValues_lrs = lrs_pickle['linreftab'][1]
                    #self.Records = lrs_pickle['linreftab'][1]
                    #self.RecordsDict = lrs_pickle['linreftab'][2]
                    #self.sri = lrs_pickle['linreftab'][1][2]
                else:
                    RecordsValues_lrs = lrs_pickle['linreftab'][0]
                if lrs_pickle['sldtab'][0]:
                    RecordsValues_sld = lrs_pickle['sldtab'][1]
                    #self.RecordsDict_sld = lrs_pickle['sldtab'][2]
                else:
                    RecordsValues_sld = lrs_pickle['sldtab'][0]
                if lrs_pickle['segment'][0]:
                    pass
                    #self.segguid = lrs_pickle['segment'][1]
                lrs_pickle = lrs_pickle
            else:
                RecordsValues_lrs = parameters[0].values
                if RecordsValues_lrs:
                    for i,v in enumerate(RecordsValues_lrs):
                        #print(i,v)
                        if v[5] == 0.0:
                            #print('Here it is: {0}'.format(RecordsValues_lrs))
                            RecordsValues_lrs[i][5] = 0.0
                RecordsValues_sld = parameters[8].values










        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        # LRS Delete Update

        # Delete or Update?
        for key,value in self.RecordsDict.iteritems():
            arcpy.AddMessage('\n____________________________________________________\nEvaluating {0}...'.format(key))
            present = False
            if RecordsValues_lrs:
                for i,rec in enumerate(RecordsValues_lrs):
                    if key == rec[0]:  #
                        present = True
                        presentInd = i
                        break
            if not present: #-------------------------Delete
                # delete the seg_name record
                seg_sql = erebus.sqlGUID("GLOBALID", value[0])
                try:
                    cursor =  arcpy.UpdateCursor(linreftab, seg_sql)
                    for row in cursor:
                        cursor.deleteRow(row)
                        arcpy.AddMessage('\nDeleted {0} LINEAR_REF Record. {1}'.format(key, seg_sql))
                    del row, cursor
                except:
                    Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                    try: row; del row
                    except: pass
                    try: cursor; del cursor
                    except: pass
                    trace = traceback.format_exc()
                    arcpy.AddMessage(trace)
                    sys.exit('block1')

            if present: #--------------------------Update
                try:
                    # compare RecordsValues to self.Records
                    changed= False
                    changeInds = []

                    for ij,rece in enumerate(self.Records):  #find the index in self.Roecords...because they wont necisarily be the same..
                        if key == rece[0]:  #
                            selfInd = ij
                            break

                    for j,field in enumerate(RecordsValues_lrs[presentInd]): # this is the record in RecordsValues that matches Dict
                        if j in (1,3,4,5,6) and not field:
                            if j in (5,6) and field == 0:
                                pass
                            else:
                                arcpy.AddError('Missing Required Field in LRS Record')
                                sys.exit('Missing Required Field')
                        if field != self.Records[selfInd][j]:
                            if self.Records[selfInd][j] in ('', None, 'None') and field in ('', None, 'None'):
                                pass
                            else:
                                arcpy.AddMessage('\nFields are different: Original {0}, New {1}'.format(self.Records[selfInd][j], field))
                                changed = True  # there is a changed value...we need to update
                                changeInds.append(j)
                    #check for missing values that are required



                    if changed:

                        # First determine if LRS type 1 exists, then figure out if's milepost values are different than the M-values (start and end). If they are, update the M-values.
                        if RecordsValues_lrs[presentInd][3] == 1 and (5 in changeInds or 6 in changeInds): # LRS type is 1, and there are differnt values in mileposts
                            try:
                                import json, math
                                segment_sql = erebus.sqlGUID("SEG_GUID", self.segguid)

                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
                                for row in cursor:
                                    bogus = row.getValue('ACC_TYPE_ID')
                                    row.setValue('ACC_TYPE_ID', bogus)
                                    cursor.updateRow(row)
                                del row, cursor

                                with arcpy.da.SearchCursor(segmentfc,["SHAPE@"], segment_sql) as c1:
                                    for r1 in c1:
                                        fulldist = r1[0].getLength('PLANAR', 'FEET')
                                        geometry = r1[0]

                                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@WKT"], segment_sql) as cursor:
                                    for row in cursor:

                                        json_obj = erebus.wkt_to_esrijson(geometry)['esrijson']
                                        mp_to = len(json_obj['paths'][0]) - 1
                                        conversionfactor = (math.fabs(RecordsValues_lrs[presentInd][6] - RecordsValues_lrs[presentInd][5]) / fulldist)
                                        for i,v in enumerate(json_obj['paths'][0]):
                                            if i == 0:
                                                json_obj['paths'][0][i][2] = float(RecordsValues_lrs[presentInd][5])
                                            elif i == mp_to:
                                                json_obj['paths'][0][i][2] = float(RecordsValues_lrs[presentInd][6])
                                            else:
                                                # distance in map units between last vertex and current vertex
                                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
                                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
                                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
                                                vert_lrdist = vertdist * conversionfactor
                                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)

                                        # convert the json back to WKT
                                        wktobj = erebus.esrijson_to_wkt(json_obj)
                                        cursor.updateRow([wktobj['WKT'],])
                                        arcpy.AddMessage("SEGMENT M-Values inserted without exception")

                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)

                                for row in cursor:
                                    bogus = row.getValue('ACC_TYPE_ID')
                                    row.setValue('ACC_TYPE_ID', bogus)
                                    cursor.updateRow(row)
                                del row, cursor

##                                import json, math
##                                segment_sql = erebus.sqlGUID("SEG_GUID", self.segguid)
##
##                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
##                                for row in cursor:
##                                    bogus = row.getValue('ACC_TYPE_ID')
##                                    row.setValue('ACC_TYPE_ID', bogus)
##                                    cursor.updateRow(row)
##                                del row, cursor
##
##                                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@"], segment_sql) as cursor:
##                                    for row in cursor:
##                                        jj = row[0].JSON
##                                        json_obj = json.loads(row[0].JSON)
##                                        mp_to = len(json_obj['paths'][0]) - 1
##                                        fulldist = row[0].getLength('PLANAR', 'FEET')
##                                        conversionfactor = (math.fabs(RecordsValues_lrs[presentInd][6] - RecordsValues_lrs[presentInd][5]) / fulldist)
##                                        for i,v in enumerate(json_obj['paths'][0]):
##                                            if i == 0:
##                                                json_obj['paths'][0][i][2] = float(RecordsValues_lrs[presentInd][5])
##                                            else:
##                                                # distance in map units between last vertex and current vertex
##                                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
##                                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
##                                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
##                                                vert_lrdist = vertdist * conversionfactor
##                                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)
##                                        for feature in json_obj['paths']:
##                                            pline = arcpy.Polyline(arcpy.Array([arcpy.Point(X=coords[0], Y=coords[1], M=coords[2]) for coords in feature]), row[0].spatialReference, False, True)
##                                        row[0] = pline
##                                        cursor.updateRow(row)
##                                        arcpy.AddMessage("SEGMENT M-Values inserted")
##
##                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
##
##                                for row in cursor:
##                                    bogus = row.getValue('ACC_TYPE_ID')
##                                    row.setValue('ACC_TYPE_ID', bogus)
##                                    cursor.updateRow(row)
##                                del row, cursor

                            except SystemError as e:
                                arcpy.AddMessage("SEGMENT M-Values inserted with exception")
                                print(traceback.format_exc())
                            except:
                                arcpy.AddMessage("SEGMENT M-Values failed with exception")
                                print(traceback.format_exc())

                            cursor = arcpy.UpdateCursor(segmentfc, segment_sql)

                            for row in cursor:
                                bogus = row.getValue('ACC_TYPE_ID')
                                row.setValue('ACC_TYPE_ID', bogus)
                                cursor.updateRow(row)
                            del row, cursor


                        walkXsegname = {1: 'SEG_GUID', 2: 'SRI', 3: 'LRS_TYPE_ID', 4: 'SEG_TYPE_ID', 5: 'MILEPOST_FR', 6: 'MILEPOST_TO', 7: 'RCF'}
                        seg_sql = erebus.sqlGUID("GLOBALID", value[0])
                        cursor = arcpy.UpdateCursor(linreftab, seg_sql)
                        for row in cursor:
                            for cc in changeInds:
                                row.setValue(walkXsegname[cc], RecordsValues_lrs[presentInd][cc])
                                arcpy.AddMessage('\nUpdated {0} in LINEAR_REF. {1}, \nUpdated {2} from {3} to {4}'.format(key ,seg_sql, walkXsegname[cc], self.Records[ij][cc], RecordsValues_lrs[presentInd][cc]))
                            cursor.updateRow(row)
                        del row, cursor
                except:
                    Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                    trace = traceback.format_exc()
                    try: row; del row
                    except: pass
                    try: cursor; del cursor
                    except: pass
                    arcpy.AddMessage(trace)
                    arcpy.AddMessage('\nchangeinds: {0}, cc {1}, RecordsValues {2}'.format(changeInds, cc ,RecordsValues_lrs[presentInd][cc]))
                    sys.exit('Error: Delete and Update Block')

        ## #                 0      1           2           3               4               5           6       7
        ##            "SEG_GUID", "SRI", "LRS_TYPE_ID", "SEG_TYPE_ID", "MILEPOST_FR", "MILEPOST_TO", "RCF","GLOBALID"]
        ##(['Record {0}',row[0], row[1], row[2],           row[3],         row[4],       row[5],    row[6]])
        ##      0           1      2       3                 4               5              6          7

        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        # LRS Insert

        if RecordsValues_lrs:
            for y,rec in enumerate(RecordsValues_lrs):
                match = False
                for key,value in self.RecordsDict.iteritems():
                    if rec[0] == key:
                        match = True
                if not match: # no matching records, do an insert
                    arcpy.AddMessage('\n____________________________________________________\nEvaluating {0}...'.format(rec[0]))
                    if rec[1] and rec[3] and rec[4]:
                        try:
                            cursor = arcpy.InsertCursor(linreftab)
                            row = cursor.newRow()
                            row.setValue("SEG_GUID", rec[1])
                            row.setValue("LRS_TYPE_ID", rec[3])
                            row.setValue("SEG_TYPE_ID", rec[4])
                            if rec[2]:
                                row.setValue("SRI", rec[2])
##                            if rec[5]:
                            row.setValue("MILEPOST_FR", rec[5])
##                            if rec[6]:
                            row.setValue("MILEPOST_TO", rec[6])
                            if rec[7]:
                                row.setValue("RCF", rec[7])

                            cursor.insertRow(row)
                            arcpy.AddMessage('Inserted {0} into LINEAR_REF, values are {1}'.format(rec[0], rec[1:8]))
                            del cursor, row
                        except:
                            Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                            trace = traceback.format_exc()
                            try: row; del row
                            except: pass
                            try: cursor; del cursor
                            except: pass
                            arcpy.AddMessage(trace)
                            sys.exit('Error: Insert 2')


                        # First determine if LRS type 1 exists, then figure out if there are milepost values. If there are, update the M-values.
                        if rec[3] == 1 and (rec[5] == 0 or rec[5]) and (rec[6] == 0 or rec[6]): # LRS type is 1, and there are values in mileposts
                            try:


                                import json, math
                                segment_sql = erebus.sqlGUID("SEG_GUID", self.segguid)

                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
                                for row in cursor:
                                    bogus = row.getValue('ACC_TYPE_ID')
                                    row.setValue('ACC_TYPE_ID', bogus)
                                    cursor.updateRow(row)
                                del row, cursor

                                with arcpy.da.SearchCursor(segmentfc,["SHAPE@"], segment_sql) as c1:
                                    for r1 in c1:
                                        fulldist = r1[0].getLength('PLANAR', 'FEET')
                                        geometry = r1[0]

                                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@WKT"], segment_sql) as cursor:
                                    for row in cursor:

                                        json_obj = erebus.wkt_to_esrijson(geometry)['esrijson']
                                        mp_to = len(json_obj['paths'][0]) - 1
                                        conversionfactor = (math.fabs(rec[6] - rec[5]) / fulldist)
                                        for i,v in enumerate(json_obj['paths'][0]):
                                            if i == 0:
                                                json_obj['paths'][0][i][2] = float(rec[5])
                                            elif i == mp_to:
                                                json_obj['paths'][0][i][2] = float(rec[6])
                                            else:
                                                # distance in map units between last vertex and current vertex
                                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
                                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
                                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
                                                vert_lrdist = vertdist * conversionfactor
                                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)

                                        # convert the json back to WKT
                                        wktobj = erebus.esrijson_to_wkt(json_obj)
                                        cursor.updateRow([wktobj['WKT'],])
                                        arcpy.AddMessage("SEGMENT M-Values inserted without exception")

                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
                                for row in cursor:
                                    bogus = row.getValue('ACC_TYPE_ID')
                                    row.setValue('ACC_TYPE_ID', bogus)
                                    cursor.updateRow(row)
                                del row, cursor




##                                import json, math
##                                segment_sql = erebus.sqlGUID("SEG_GUID", self.segguid)
##
##                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
##                                for row in cursor:
##                                    bogus = row.getValue('ACC_TYPE_ID')
##                                    row.setValue('ACC_TYPE_ID', bogus)
##                                    cursor.updateRow(row)
##                                del row, cursor
##
##                                with arcpy.da.UpdateCursor(segmentfc,["SHAPE@"], segment_sql) as cursor:
##                                    for row in cursor:
##                                        jj = row[0].JSON
##                                        json_obj = json.loads(row[0].JSON)
##                                        mp_to = len(json_obj['paths'][0]) - 1
##                                        fulldist = row[0].getLength('PLANAR', 'FEET')
##                                        conversionfactor = (math.fabs(rec[6] - rec[5]) / fulldist)
##                                        for i,v in enumerate(json_obj['paths'][0]):
##                                            if i == 0:
##                                                json_obj['paths'][0][i][2] = float(rec[5])
##                                            else:
##                                                # distance in map units between last vertex and current vertex
##                                                x1vert = json_obj['paths'][0][i][0] - json_obj['paths'][0][i-1][0]
##                                                y1vert = json_obj['paths'][0][i][1] - json_obj['paths'][0][i-1][1]
##                                                vertdist = math.sqrt(x1vert**2 + y1vert**2)
##                                                vert_lrdist = vertdist * conversionfactor
##                                                json_obj['paths'][0][i][2] =  json_obj['paths'][0][i-1][2] + float(vert_lrdist)
##                                        for feature in json_obj['paths']:
##                                            pline = arcpy.Polyline(arcpy.Array([arcpy.Point(X=coords[0], Y=coords[1], M=coords[2]) for coords in feature]), row[0].spatialReference, False, True)
##                                        row[0] = pline
##                                        cursor.updateRow(row)
##                                        #arcpy.AddMessage("SEGMENT M-Values inserted")
##
##                                cursor = arcpy.UpdateCursor(segmentfc, segment_sql)
##
##                                for row in cursor:
##                                    bogus = row.getValue('ACC_TYPE_ID')
##                                    row.setValue('ACC_TYPE_ID', bogus)
##                                    cursor.updateRow(row)
##                                del row, cursor

                            except SystemError as e:
                                arcpy.AddMessage("SEGMENT M-Values inserted with exception")
                                print(traceback.format_exc())
                            except:
                                arcpy.AddMessage("SEGMENT M-Values failed with exception")
                                print(traceback.format_exc())





                    else:
                        arcpy.AddError('Missing Required Fields. Required fields are; SEG_GUID, LRS_TYPE_ID, and SEG_TYPE_ID.')

        ################################################################################
        ################################################################################
        ################################################################################

        arcpy.AddMessage('\nCompleted LINEAR_REF\n####################################################\n####################################################\n\nStarting SLD_ROUTE...\n')

        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        # SLD Delete Update

        # Delete or Update?
        for key,value in self.RecordsDict_sld.iteritems():
            arcpy.AddMessage('\n____________________________________________________\nEvaluating {0}...'.format(key))
            present = False
            if RecordsValues_sld:
                for i,rec in enumerate(RecordsValues_sld):
                    if key == rec[0]:  #
                        present = True
                        presentInd = i
                        break
            if not present: #-------------------------Delete
                # delete the record
                seg_sql = erebus.sqlGUID("GLOBALID", value[0])
                try:
                    cursor =  arcpy.UpdateCursor(sldtab, seg_sql)
                    for row in cursor:
                        cursor.deleteRow(row)
                        arcpy.AddMessage('\nDeleted {0} SLD_ROUTE Record. {1}'.format(key, seg_sql))
                    del row, cursor
                except:
                    #***************
                    Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                    try: row; del row
                    except: pass
                    try: cursor; del cursor
                    except: pass
                    trace = traceback.format_exc()
                    arcpy.AddMessage(trace)
                    sys.exit('block3')

            if present: #--------------------------Update
                try:
                    # compare RecordsValues to self.Records
                    changed= False
                    changeInds = []

                    for ij,rece in enumerate(self.Records_sld):  #find the index in self.Roecords...because they wont necisarily be the same..
                        if key == rece[0]:  #
                            selfInd = ij
                            break

                    for j,field in enumerate(RecordsValues_sld[presentInd]): # this is the record in RecordsValues that matches Dict
                        if j in (1,2) and not field:
                            Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                            arcpy.AddError('Missing Required Field')
                            sys.exit('Missing Required Field')
                        if field != self.Records_sld[selfInd][j]:
                            if self.Records_sld[selfInd][j] in ('', None, 'None') and field in ('', None, 'None'):
                                pass
                            else:
                                arcpy.AddMessage('\nFields are different: Original {0}, New {1}'.format(self.Records_sld[selfInd][j], field))
                                changed = True  # there is a changed value...we need to update
                                changeInds.append(j)
                    #check for missing values that are required



                    if changed:
                        walkXsld = {1: 'SRI', 2: 'ROUTE_TYPE_ID', 3: 'SLD_NAME', 4: 'SLD_COMMENT', 5: 'SLD_DIRECTION', 6: 'SIGN_NAME'}
                        seg_sql = erebus.sqlGUID("GLOBALID", value[0])
                        cursor = arcpy.UpdateCursor(sldtab, seg_sql)
                        for row in cursor:
                            for cc in changeInds:
                                if cc == 5 and RecordsValues_sld[presentInd][cc]:
                                    row.setValue(walkXsld[cc], None)
                                else:
                                    row.setValue(walkXsld[cc], RecordsValues_sld[presentInd][cc])
                                arcpy.AddMessage('\nUpdated {0} in SLD_ROUTE. {1}, \nUpdated {2} from {3} to {4}'.format(key ,seg_sql, walkXsld[cc], self.Records_sld[ij][cc], RecordsValues_sld[i][cc]))
                            cursor.updateRow(row)
                        del row, cursor

                except:
                    Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                    trace = traceback.format_exc()
                    try: row; del row
                    except: pass
                    try: cursor; del cursor
                    except: pass
                    arcpy.AddMessage(trace)
                    arcpy.AddMessage('\nchangeinds: {0}, cc {1}, RecordsValues_sld {2}'.format(changeInds, cc ,RecordsValues_sld[presentInd][cc]))
                    sys.exit('Error: Delete and Update Block')


        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        # SLD INSERT

        #                                                  ["SRI",  "ROUTE_TYPE_ID", "SLD_NAME", "SLD_COMMENT", "SLD_DIRECTION", "SIGN_NAME","GLOBALID"], sri_sql) as cursor2:
        # self.Records_sld.append(['Record {0}'.format(gg),row[0],       row[1],        row[2],      row[3],         row[4],       row[5]])
        #                                      0               1               2               3           4               5           6

        # Insert and there are existing records
        if RecordsValues_sld:
            for y,rec in enumerate(RecordsValues_sld):
                match = False
                for key,value in self.RecordsDict_sld.iteritems():
                    if rec[0] == key:
                        match = True
                if not match: # no matching records, do an insert
                    arcpy.AddMessage('\n____________________________________________________\nEvaluating {0}...'.format(rec[0]))
                    if rec[1] and rec[2]:
                        try:
                            cursor = arcpy.InsertCursor(sldtab)
                            row = cursor.newRow()
                            row.setValue("SRI", rec[1])
                            row.setValue("ROUTE_TYPE_ID", rec[2])

                            if rec[3]:
                                row.setValue("SLD_NAME", rec[3])
                            if rec[4]:
                                row.setValue("SLD_COMMENT", rec[4])
                            if rec[5] and rec[5] is not '<null>':
                                row.setValue("SLD_DIRECTION", rec[5])
                            if rec[6]:
                                row.setValue("SIGN_NAME", rec[6])

                            cursor.insertRow(row)
                            arcpy.AddMessage('Inserted {0} into SLD_ROUTE, values are {1}'.format(rec[0], rec[1:7]))
                            del cursor, row
                        except:
                            Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                            trace = traceback.format_exc()
                            try: row; del row
                            except: pass
                            try: cursor; del cursor
                            except: pass
                            arcpy.AddMessage(trace)
                            sys.exit('Error: Insert 4')
                    else:
                        Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False
                        arcpy.AddMessage('No SLD Record Inserted')

        arcpy.AddMessage('\n\n')

        Record_lrs = []; Records_lrs = []; currentR = ""; Record_sld = []; Records_sld = []; currentR_sld = ""; RecordsCleared_lrs['status'] = ('',False); RecordsCleared_sld['status'] = ('',False); RecordsCleared_lrs['altered'] = False; RecordsCleared_sld['altered'] = False

        return


# END AddLRS
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

class BatchPost(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "BatchPost"
        self.description = "Post and Reconcile versions, build indices, cleanup versions"
        self.canRunInBackground = True
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Input Database Connection",
            name="input_connection",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        #
        param1 = arcpy.Parameter(
            displayName="Reconcile Mode",
            name="reconcile_mode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param1.filter.type = "ValueList"
        param1.filter.list = ["ALL_VERSIONS", "BLOCKING_VERSIONS"]
        param1.value = "ALL_VERSIONS"

        #
        param2 = arcpy.Parameter(
            displayName="Target Version",
            name="target",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param2.filter.type = "ValueList"

        #
        param3 = arcpy.Parameter(
            displayName="Edit Versions",
            name="edit_versions",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        param3.filter.type = "ValueList"
        param3.filter.list = ['road_child0', 'road_child1', 'road_child2','road_child3' ,'road_child4' ,'road_child5' ,'road_child6' ,'road_child7']

        #
        param4 = arcpy.Parameter(
            displayName="Post Versions After Reconcile",
            name="locks",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param4.value = True

        #
        param5 = arcpy.Parameter(
            displayName="Delete Versions After Post",
            name="abort",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        params = [param0,param1,param2,param3,param4,param5]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        if not parameters[2].altered:
            sdedescribe = arcpy.Describe(arcpy.env.workspace)
            parameters[2].filter.list = [sdedescribe.connectionProperties.version]


##        vlist = []
##        vv = arcpy.ListVersions(arcpy.env.workspace)  #[u'ROAD.road_child0', u'OAXKONO.rd_oaxkono', u'ROAD.road_child1', u'ROAD.road_child2', u'ROAD.road_child3', u'ROAD.road_child4', u'ROAD.road_child5', u'ROAD.road_child6', u'ROAD.road_child7', u'GSVCADDR.test', u'GISTEST.DEP_pull_test', u'OAXPIKO.rd_Yelena', u'ROAD.rd_TestBatchBuildName', u'SDE.DEFAULT', u'SDE.QA_general', u'ROAD.rd_Staging']
##        if not parameters[3].altered:
##            for v in vv:
##                if v.split('.')[1] in ('road_child0', 'road_child1', 'road_child2','road_child3' ,'road_child4' ,'road_child5' ,'road_child6' ,'road_child7'):
##                    vlist.append(v.split('.')[1])
##
##            parameters[3].value = vlist




        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        import arcpy, os, sys
        arcpy.AddMessage('\nVersions to reconcile and post: {0}'.format(parameters[3].values))  #[u'road_child0', u'road_child1', u'road_child2', u'road_child3', u'road_child4', u'road_child5', u'road_child6', u'road_child7']

        vlist = []
        vlistconn = []
        vv = arcpy.ListVersions(arcpy.env.workspace)  #[u'ROAD.road_child0', u'OAXKONO.rd_oaxkono', u'ROAD.road_child1', u'ROAD.road_child2', u'ROAD.road_child3', u'ROAD.road_child4', u'ROAD.road_child5', u'ROAD.road_child6', u'ROAD.road_child7', u'GSVCADDR.test', u'GISTEST.DEP_pull_test', u'OAXPIKO.rd_Yelena', u'ROAD.rd_TestBatchBuildName', u'SDE.DEFAULT', u'SDE.QA_general', u'ROAD.rd_Staging']
        for v in vv:
            if v.split('.')[1] in parameters[3].values:
                vlist.append(v)
                vlistconn.append(v.split('.')[1] + '.sde')

        arcpy.AddMessage(arcpy.ListVersions(arcpy.env.workspace))  #[u'ROAD.road_child0', u'OAXKONO.rd_oaxkono', u'ROAD.road_child1', u'ROAD.road_child2', u'ROAD.road_child3', u'ROAD.road_child4', u'ROAD.road_child5', u'ROAD.road_child6', u'ROAD.road_child7', u'GSVCADDR.test', u'GISTEST.DEP_pull_test', u'OAXPIKO.rd_Yelena', u'ROAD.rd_TestBatchBuildName', u'SDE.DEFAULT', u'SDE.QA_general', u'ROAD.rd_Staging']
        arcpy.AddMessage('\nVersions to reconcile and post: {0}'.format(vlist)) #[u'ROAD.road_child0', u'ROAD.road_child1', u'ROAD.road_child2', u'ROAD.road_child3', u'ROAD.road_child4', u'ROAD.road_child5', u'ROAD.road_child6', u'ROAD.road_child7']

        arcpy.AddMessage(vlistconn)  #[u'road_child0.sde', u'road_child1.sde', u'road_child2.sde', u'road_child3.sde', u'road_child4.sde', u'road_child5.sde', u'road_child6.sde', u'road_child7.sde']


        input_database = parameters[0].value
        reconcile_mode = parameters[1].value
        target_version = parameters[2].value
        edit_versions = vlist
        if parameters[4].value == True:
            with_post = 'POST'
        else:
            with_post = 'NO_POST'
        if parameters[5].value == True:
            with_delete = 'DELETE_VERSION'
        else:
            with_delete = 'KEEP_VERSION'
        out_log = os.path.join(arcpy.env.scratchWorkspace, 'reconcilelog.txt')

        if os.path.exists(out_log):
            os.remove(out_log)

        arcpy.AddMessage('\nInput Database: {0}\nReconcile Mode: {1}\nTarget Version: {2}\nEdit Versions: {3}\nPost: {4}\nDelete: {5}'.format(input_database,reconcile_mode,target_version,edit_versions,with_post,with_delete))


##        arcpy.AddMessage('\nCompressing...')
##        arcpy.Compress_management(input_database)
##        arcpy.AddMessage('\nAny Messages... {0}'.format(arcpy.GetMessages()))
##        arcpy.AddMessage('\nRebuilding Indices...')
##        arcpy.RebuildIndexes_management(input_database, "SYSTEM", "SDE.COMPRESS_LOG", "ALL")
##        arcpy.AddMessage('\nAny Messages... {0}'.format(arcpy.GetMessages()))

        # Execute the ReconcileVersions tool.
        arcpy.AddMessage('\nReconciling and Posting...')
        arcpy.ReconcileVersions_management(input_database, reconcile_mode, target_version, edit_versions, "LOCK_ACQUIRED", "NO_ABORT", "BY_OBJECT", "FAVOR_TARGET_VERSION", with_post, with_delete, out_log)
        arcpy.AddMessage('\nAny Messages... {0}'.format(arcpy.GetMessages()))

##        arcpy.AddMessage('\nCompressing...')
##        arcpy.Compress_management(input_database)
##        arcpy.AddMessage('\nAny Messages... {0}'.format(arcpy.GetMessages()))
##        arcpy.AddMessage('\nRebuilding Indices...')
##        arcpy.RebuildIndexes_management(input_database, "SYSTEM", "SDE.COMPRESS_LOG", "ONLY_DELTAS")
##        arcpy.AddMessage('\nAny Messages... {0}'.format(arcpy.GetMessages()))


        #arcpy.AnalyzeDatasets_management(input_database, "SYSTEM", "ANALYZE_BASE", "ANALYZE_DELTA", "ANALYZE_ARCHIVE")
##        for vconn in vlistconn:
##            arcpy.AddMessage('\nDisconnecting users on {0}'.format(vconn))
##            arcpy.DisconnectUser(os.path.join('Database Connections',vconn), "ALL")


##        # ReconcileVersions_management (input_database, reconcile_mode, {target_version}, {edit_versions}, {acquire_locks}, {abort_if_conflicts}, {conflict_definition}, {conflict_resolution}, {with_post}, {with_delete}, {out_log})

##        arcpy.ReconcileVersions_management('Database Connections/admin.sde', "ALL_VERSIONS", "sde.DEFAULT", versionList, "LOCK_ACQUIRED", "NO_ABORT", "BY_OBJECT", "FAVOR_TARGET_VERSION", "POST", "DELETE_VERSION", "c:/temp/reconcilelog.txt")

##        # Block new connections to the database.
##
##        arcpy.AcceptConnections('Database Connections/admin.sde', False)
##
####        # Wait 15 minutes
####        time.sleep(900)
##
##        # Disconnect all users from the database.
##        arcpy.DisconnectUser('Database Connections/admin.sde', "ALL")
##
##        # Get a list of versions to pass into the ReconcileVersions tool.
##        versionList = arcpy.ListVersions('Database Connections/admin.sde')
##
##        # ReconcileVersions_management (input_database, reconcile_mode, {target_version}, {edit_versions}, {acquire_locks}, {abort_if_conflicts}, {conflict_definition}, {conflict_resolution}, {with_post}, {with_delete}, {out_log})
##
##        # Execute the ReconcileVersions tool.
##        arcpy.ReconcileVersions_management('Database Connections/admin.sde', "ALL_VERSIONS", "sde.DEFAULT", versionList, "LOCK_ACQUIRED", "NO_ABORT", "BY_OBJECT", "FAVOR_TARGET_VERSION", "POST", "DELETE_VERSION", "c:/temp/reconcilelog.txt")
##
##        # Run the compress tool.
##        arcpy.Compress_management('Database Connections/admin.sde')
##
##        # Allow the database to begin accepting connections again
##        arcpy.AcceptConnections('Database Connections/admin.sde', True)
##
##        # Get a list of datasets owned by the admin user
##
##        # Rebuild indexes and analyze the states and states_lineages system tables
##        arcpy.RebuildIndexes_management(workspace, "SYSTEM", "ALL")
##
##        arcpy.AnalyzeDatasets_management(workspace, "SYSTEM", "ANALYZE_BASE", "ANALYZE_DELTA", "ANALYZE_ARCHIVE")

# END BatchPost
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

Records = []
Record = []
currentR = ""
RecordsCleared = {'status': ('', False), 'segguid': ''}
EN_ID = ''

class EditNames(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "EditNames"
        self.description = "Edit SEG_NAME and SEG_SHIELD records"
        self.canRunInBackground = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab
        global Records, Record, currentR, RecordsCleared, EN_ID


        self.Records = []
        self.RecordsDict = {}

        try:
            editnamespath = arcpy.env.scratchWorkspace + "\\editnamesselection.p"
            if os.path.exists(editnamespath):
                with open(editnamespath,'rb') as editnamesopen:
                    editnames_pickle = pickle.load(editnamesopen)

            if editnames_pickle['segment'][0]:
                self.Records = editnames_pickle['segment'][1]
                self.RecordsDict = editnames_pickle['segment'][2]

            self.editnames_pickle = editnames_pickle
            self.segguid = editnames_pickle['segguid']

            if EN_ID == '':
                EN_ID = editnames_pickle['ID']
            elif EN_ID == editnames_pickle['ID']:
                pass
            elif EN_ID != editnames_pickle['ID']:# new ID, clear out vars, reassign
                Record = []
                Records = []
                currentR = ""
                RecordsCleared = {'status': ('', False), 'segguid': ''}
                EN_ID = editnames_pickle['ID']
        except:
            Record = []
            Records = []
            currentR = ""
            RecordsCleared = {'status': ('', False), 'segguid': ''}


    def getParameterInfo(self):
        """Define parameter definitions"""

        param0 = arcpy.Parameter(
            displayName="Add and Delete Records",
            name="seg_name_cols",
            datatype="GPValueTable",
            parameterType="Optional",
            direction="Input")
        param0.columns = [['String', 'Record ID'], ['String', '*SEG_GUID'], ['String', '*NAME_TYPE_ID'], ['Long','*RANK'], ['String', '*NAME_FULL'], ['String', 'PRE_DIR'], ['String', 'PRE_TYPE'], ['String', 'PRE_MOD'], ['String', '*NAME'], ['String', 'SUF_TYPE'], ['String', 'SUF_DIR'], ['String', 'SUF_MOD'], ['Long', '*DATA_SRC_TYPE_ID'], ['String', 'SHIELD_TYPE_ID'], ['String', 'SHIELD_SUBTYPE_ID'], ['String', 'SHIELD_NAME']]
        #param00.values = [[u'L1', u'guid', 'Name Full',False], [u'L2', u'guid', 'Name Full',False]] #"hey you;guys text2"  ['GPBoolean', 'Delete?']
        #param00.enabled = False

        #
        param1 = arcpy.Parameter(
            displayName="Current Record",
            name="current_record",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param1.filter.type = "ValueList"

        #
        param3 = arcpy.Parameter(
            displayName="NAME_TYPE_ID",
            name="NAME_TYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param3.filter.type = "ValueList"
        param3.filter.list = ["L", "H"]

        #-----------------------------------------------------------------------
        # SEG_SHIELD category

        #
        param4 = arcpy.Parameter(
            displayName="SHIELD_TYPE_ID (highway route shield)                              *Only required if Name Type is 'Highway'",
            name="SHIELD_TYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param4.filter.type = "ValueList"
        param4.filter.list = ["ACE", "ACB", "COR", "GSP", "INT", "PIP", "STR", "TPK", "USR"]

        #
        param5 = arcpy.Parameter(
            displayName="SHIELD_SUBTYPE_ID (highway route shield modifier)          *Only required if Name Type is 'Highway'",
            name="SHIELD_SUBTYPE_ID",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param5.filter.type = "ValueList"
        param5.filter.list = ["A", "B", "C", "E", "M", "S", "T", "Y"]

        #
        param6 = arcpy.Parameter(
            displayName="SHIELD_NAME (highway route number)                               *Only required if Name Type is 'Highway'",
            name="SHIELD_NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        #-----------------------------------------------------------------------

        # 6
        param7 = arcpy.Parameter(
            displayName="RANK",
            name="RANK (SEG_NAME)",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")

        # 7
        param8 = arcpy.Parameter(
            displayName="NAME_FULL",
            name="NAME_FULL",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        param8.enabled = False

        # 8
        param9 = arcpy.Parameter(
            displayName="PRE_DIR",
            name="PRE_DIR",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 9
        param10 = arcpy.Parameter(
            displayName="PRE_TYPE",
            name="PRE_TYPE",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 10
        param11 = arcpy.Parameter(
            displayName="PRE_MOD",
            name="PRE_MOD",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 11
        param12 = arcpy.Parameter(
            displayName="NAME",
            name="NAME",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 12
        param13 = arcpy.Parameter(
            displayName="SUF_TYPE",
            name="SUF_TYPE",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 13
        param14 = arcpy.Parameter(
            displayName="SUF_DIR",
            name="SUF_DIR",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 14
        param15 = arcpy.Parameter(
            displayName="SUF_MOD",
            name="SUF_MOD",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # 15
        param16 = arcpy.Parameter(
            displayName="DATA_SRC_TYPE_ID",
            name="DATA_SRC_TYPE_ID",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param16.filter.type = "ValueList"
        param16.filter.list = [1,2,3,4,5,6,7]

        # 16
        param17 = arcpy.Parameter(
            displayName="Build PRIME_NAME in SEGMENT",
            name="build_prime_name",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param17.value = True

        # 18
        param18 = arcpy.Parameter(
            displayName="Parse NAME_FULL",
            name="parse_name_full",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        param18.value = False

        params = [param0,param1,param3,param4,param5,param6,param7,param8,param9,param10,param11,param12,param13,param14,param15,param16,param17,param18]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        os.sys.path.append(os.path.dirname(__file__))
        import erebus
        global Records, Record, currentR, RecordsCleared

        #import
        editnamespath = arcpy.env.scratchWorkspace + "\\editnamesselection.p"
        if os.path.exists(editnamespath):
            with open(editnamespath,'rb') as editnamesopen:
                editnames_pickle = pickle.load(editnamesopen)
        editnames_pickle['UPDATECOUNT'] += 1
        updatecount = editnames_pickle['UPDATECOUNT']
        #print('\nUPDATECOUNT: {0}'.format(updatecount))
        #output
        editnamespath = arcpy.env.scratchWorkspace + "\\editnamesselection.p"
        with open(editnamespath, 'wb') as output:
            pickle.dump(editnames_pickle, output, -1)

        if not Records and not self.Records:
            #Records_lrs = [['Record 1', self.segguid, '', '', '', None, None, None]]
            Records = [['Record 1', self.segguid, '', None, '', '', '', '', '', '', '', '', '', '', '', '']]
            parameters[0].values = Records
        if not Records and not parameters[0].values and not parameters[0].altered and not RecordsCleared['status'][1] and self.Records and not self.editnames_pickle['segmentlocked']:  # first population
            parameters[0].values = self.Records
            Records = self.Records
            #print('  EN 0 \n  Records: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records, parameters[0].values, parameters[0].altered, self.Records))
            #import
            if os.path.exists(editnamespath):
                with open(editnamespath,'rb') as editnamesopen:
                    editnames_pickle = pickle.load(editnamesopen)
            editnames_pickle['segmentlocked'] = True
            #output
            with open(editnamespath, 'wb') as output:
                pickle.dump(editnames_pickle, output, -1)
        elif not Records and not parameters[0].values and not parameters[0].altered and not RecordsCleared['status'][1] and self.Records and self.editnames_pickle['segmentlocked']: #unlocked
            pass
            #print('  EN 1 \n  Records: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records, parameters[0].values, parameters[0].altered, self.Records))
        else:
            if Records and parameters[0].values:
                if len(Records) == len(parameters[0].values):  # no change
                    #Records_lrs = parameters[0].values
                    if Records:
                        for uu in range(len(Records)):
                            Records[uu][1] = self.segguid
                    parameters[0].values = Records
                    #print('  EN 2 \n  Records: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records, parameters[0].values, parameters[0].altered, self.Records))
                if len(Records) < len(parameters[0].values):  # insert
                    Records = parameters[0].values
                    if Records:
                        for uu in range(len(Records)):
                            Records[uu][1] = self.segguid
                    parameters[0].values = Records
                    #print('  EN 3 \n  Records_lrs: {0} \n  param0.values: {1} \n  param0.altered: {2}\n  self.Records: {3}'.format(Records, parameters[0].values, parameters[0].altered, self.Records))
                if len(Records) > len(parameters[0].values):
                    #print 'Delete !!!!'
                    Records = parameters[0].values

        # ----------------------------------------------------------------------

        if parameters[0].values:
            parameters[1].filter.list = [val[0] for val in parameters[0].values]
        else:
            parameters[1].filter.list = []

        if currentR and parameters[1].value:
            if currentR == parameters[1].value:  # they match on this refresh. So go through and only update things that are different in Records
                if parameters[2].value and Record[2] != parameters[2].value:
                    Record[2] = parameters[2].value
                if parameters[3].value and Record[13] != parameters[3].value:
                    Record[13] = parameters[3].value
                if parameters[4].value and Record[14] != parameters[4].value:
                    Record[14] = parameters[4].value
                if parameters[5].value and Record[15] != parameters[5].value:
                    Record[15] = parameters[5].value
                if parameters[6].value and Record[3] != parameters[6].value:
                    Record[3] = parameters[6].value
                if parameters[7].value and Record[4] != parameters[7].value:
                    Record[4] = parameters[7].value

                # this allows for None values...for name fields
                if Record[5] != parameters[8].value:
                    Record[5] = parameters[8].value
                if Record[6] != parameters[9].value:
                    Record[6] = parameters[9].value
                if Record[7] != parameters[10].value:
                    Record[7] = parameters[10].value
                if Record[8] != parameters[11].value:
                    Record[8] = parameters[11].value
                if Record[9] != parameters[12].value:
                    Record[9] = parameters[12].value
                if Record[10] != parameters[13].value:
                    Record[10] = parameters[13].value
                if Record[11] != parameters[14].value:
                    Record[11] = parameters[14].value

                if parameters[15].value and Record[12] != parameters[15].value:
                    Record[12] = parameters[15].value

                #if there is a value in Record, but no value in the field, take the Record value
                if not parameters[2].value and Record[2]:
                    parameters[2].value = Record[2]
                if not parameters[3].value and Record[13]:
                    parameters[3].value = Record[13]
                if not parameters[4].value and Record[14]:
                    parameters[4].value = Record[14]
                if not parameters[5].value and Record[15]:
                    parameters[5].value = Record[3]
                if not parameters[6].value and Record[3]:
                    parameters[6].value = Record[6]
                if not parameters[7].value and Record[4]:
                    parameters[7].value = Record[4]
                if not parameters[8].value and Record[5]:
                    parameters[8].value = Record[5]
                if not parameters[9].value and Record[6]:
                    parameters[9].value = Record[6]
                if not parameters[10].value and Record[7]:
                    parameters[10].value = Record[7]
                if not parameters[11].value and Record[8]:
                    parameters[11].value = Record[8]
                if not parameters[12].value and Record[9]:
                    parameters[12].value = Record[9]
                if not parameters[13].value and Record[10]:
                    parameters[13].value = Record[10]
                if not parameters[14].value and Record[11]:
                    parameters[14].value = Record[11]
                if not parameters[15].value and Record[12]:
                    parameters[15].value = Record[12]

                i = 0
                if Records:
                    for r in Records:
                        if parameters[1].value == r[0]:
                            Records[i] = Record
                        i += 1
                    parameters[0].values = Records

            if currentR != parameters[1].value:  #if the "Current Record" is refreshed, and doesnt match the last one...refresh the fields
                currentR = parameters[1].value
                for r in Records:
                    if parameters[1].value == r[0]:
                        Record = r
                if Record[2] == 'L':
                    parameters[2].value = 'L'
                    parameters[3].value = None
                    parameters[4].value = None
                    parameters[5].value = None
                if Record[2] == 'H':
                    parameters[2].value = 'H'
                    parameters[3].value = Record[13]
                    parameters[4].value = Record[14]
                    parameters[5].value = Record[15]
                parameters[6].value = Record[3]
                parameters[7].value = Record[4]
                parameters[8].value = Record[5]
                parameters[9].value = Record[6]
                parameters[10].value = Record[7]
                parameters[11].value = Record[8]
                parameters[12].value = Record[9]
                parameters[13].value = Record[10]
                parameters[14].value = Record[11]
                parameters[15].value = Record[12]


        if not currentR:  # the original field population...now we have currentR in memory
            if parameters[1].value and parameters[1].altered:
                currentR = parameters[1].value
                for r in Records:
                    if parameters[1].value == r[0]:
                        Record = r
                if Record[2] == 'L':
                    parameters[2].value = 'L'
                if Record[2] == 'H':
                    parameters[2].value = 'H'
                    parameters[3].value = Record[13]
                    parameters[4].value = Record[14]
                    parameters[5].value = Record[15]
                parameters[6].value = Record[3]
                parameters[7].value = Record[4]
                parameters[8].value = Record[5]
                parameters[9].value = Record[6]
                parameters[10].value = Record[7]
                parameters[11].value = Record[8]
                parameters[12].value = Record[9]
                parameters[13].value = Record[10]
                parameters[14].value = Record[11]
                parameters[15].value = Record[12]



        # ----------------------------------------------------------------------
        # GET THE SEGMENT THAT IS CURRENTLY SELECTED

        try:
            with arcpy.da.SearchCursor(segmentfc, ["SYMBOL_TYPE_ID"]) as cursor:  # insert a cursor to access fields, print names
                for row in cursor:
                    symtype = row[0]
            del cursor, row
            if int(symtype) == 100:
                parameters[3].filter.list = ["ACE", "ACB", "GSP", "PIP", "TPK"]
                parameters[5].enabled = False
        except:
            pass


        # ----------------------------------------------------------------------
        # BUILD THE NAME
        if parameters[11].value:
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()
        else:
            pass
            #parameters[7].value = Record[4]
        # SEG SHIELD PARAMS
        # check that NAME_TYPE_ID (seg name) parameter has a value, Enable the SEG_SHIELD Category

        if parameters[2].value == "H":
            parameters[3].enabled = True
            parameters[4].enabled = True
            parameters[5].enabled = True

        else:
            parameters[3].enabled = False
            parameters[4].enabled = False
            parameters[5].enabled = False


        emptyval = None
        if parameters[3].value == "ACE":
            parameters[8].value = emptyval;parameters[9].value = emptyval;parameters[10].value = emptyval;parameters[11].value = emptyval;parameters[12].value = emptyval;parameters[13].value = emptyval;parameters[14].value = emptyval
            parameters[11].value = "Atlantic City"
            parameters[12].value = "Expressway"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "ACB":
            parameters[8].value = emptyval;parameters[9].value = emptyval;parameters[10].value = emptyval;parameters[11].value = emptyval;parameters[12].value = emptyval;parameters[13].value = emptyval;parameters[14].value = emptyval
            parameters[11].value = "Atlantic City Brigantine"
            parameters[14].value = "Connector"
            parameters[4].value = "C"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "COR":
            parameters[9].value = "County Route"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "GSP":
            parameters[8].value = emptyval;parameters[9].value = emptyval;parameters[10].value = emptyval;parameters[11].value = emptyval;parameters[12].value = emptyval;parameters[13].value = emptyval;parameters[14].value = emptyval
            parameters[11].value = "Garden State"
            parameters[12].value = "Parkway"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "INT":
            parameters[9].value = "Interstate"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "PIP":
            parameters[8].value = emptyval;parameters[9].value = emptyval;parameters[10].value = emptyval;parameters[11].value = emptyval;parameters[12].value = emptyval;parameters[13].value = emptyval;parameters[14].value = emptyval
            parameters[11].value = "Palisades Interstate"
            parameters[12].value = "Parkway"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "STR":
            parameters[9].value = "State Highway"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "TPK":
            parameters[9].value = emptyval;parameters[10].value = emptyval;parameters[11].value = emptyval;parameters[12].value = emptyval;parameters[13].value = emptyval;parameters[14].value = emptyval;parameters[15].value = emptyval
            parameters[12].value = "New Jersey"
            parameters[13].value = "Turnpike"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        if parameters[3].value == "USR":
            parameters[9].value = "US Highway"
            fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()

        # Use SHIELD_SUBTYPE_ID to populate name fields
        if parameters[4].value:
            if parameters[4].value != "M":
                lssub = {"A": "A - Alternate Route", "B": "B - Business Route", "C": "C - Connector Route", "E": "E - Express Route", "M": "M - Main Route", "S": "S - Spur Route", "T": "T - Truck Route", "Y": "Y - Bypass Route"}
                substring = lssub[parameters[4].value]
                parameters[14].value = substring.split()[2]
                fnn = erebus.FullName(parameters[8].value, parameters[9].value, parameters[10].value, parameters[11].value, parameters[12].value, parameters[13].value, parameters[14].value)
            parameters[7].value = fnn.concatenate()


        # only enable the NAME_FULL if there is a value in it AND there are no values for any of the 7 parts
        if parameters[7].value and parameters[8].value == None and parameters[9].value  == None and parameters[10].value  == None and parameters[11].value == None and parameters[12].value == None and parameters[13].value == None and parameters[14].value == None:
            parameters[17].enabled = True
        else:
            parameters[17].enabled = False

        # If the user is allowed to click the checkbox, then parse the name when the box is checked.
        if parameters[17].value:
            try:
                try:
                    std_name = eval(pn.Standardize(parameters[7].value).getOutput(0))
                except:
                    std_name = tuple([''] * 7)
                fgdc_name = fgdc_parser.ParseName.ParseName(parameters[7].value).parse()
                if std_name.count('') > fgdc_name.count(''):
                    keep_name = fgdc_name
                else:
                    keep_name = std_name
                if keep_name[0]:
                    parameters[8].value = keep_name[0].capitalize()
                if keep_name[1]:
                    parameters[9].value = keep_name[1].capitalize()
                if keep_name[2]:
                    parameters[10].value = keep_name[2].capitalize()
                if keep_name[3]:
                    parameters[11].value = keep_name[3].capitalize()
                if keep_name[4]:
                    parameters[12].value = keep_name[4].capitalize()
                if keep_name[5]:
                    parameters[13].value = keep_name[5].capitalize()
                if keep_name[6]:
                    parameters[14].value = keep_name[6].capitalize()
                parameters[17].value = False
                parameters[17].enabled = False
            except:
                parameters[17].setErrorMessage("A problem occured while parsing NAME_FULL. Python error: {0}".format(traceback.format_exc()))
        else:
            pass
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        # ----------------------------------------------------------------------
        # GET THE SEGMENT THAT IS CURRENTLY SELECTED
        import re
        #pythonaddins.MessageBox('updateMessages RecordsCleared: {0}\nparameters[0].altered: {1}\nself.Records: {2}'.format(RecordsCleared,parameters[0].altered,self.Records), 'Globals', 0)

        if parameters[1].value:
            if parameters[2].value:
                parameters[2].clearMessage()
            elif parameters[2].value == None:
                parameters[2].setErrorMessage("Must be either 'L' or 'H'")
            else:
                parameters[2].setErrorMessage("Must be either 'L' or 'H'")
            if parameters[6].value or parameters[6].value == 0 or not parameters[6].value:
                if parameters[6].value in (1,2,3,4,5,6):
                    parameters[6].clearMessage()
                else:
                    parameters[6].setErrorMessage("Value must be an positive integer")

            if parameters[8].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[8].value):
                    parameters[8].clearMessage()
                else:
                    parameters[8].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[8].clearMessage()
            if parameters[9].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[9].value):
                    parameters[9].clearMessage()
                else:
                    parameters[9].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[9].clearMessage()
            if parameters[10].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[10].value):
                    parameters[10].clearMessage()
                else:
                    parameters[10].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[10].clearMessage()
            if parameters[11].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[11].value):
                    parameters[11].clearMessage()
                else:
                    parameters[11].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[11].setErrorMessage("NAME cannot be empty, please enter a name (text).")

            if parameters[12].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[12].value):
                    parameters[12].clearMessage()
                else:
                    parameters[12].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[12].clearMessage()
            if parameters[13].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[13].value):
                    parameters[13].clearMessage()
                else:
                    parameters[13].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[13].clearMessage()
            if parameters[14].value:
                if re.match("^[0-9A-Za-z\s]*$",parameters[14].value):
                    parameters[14].clearMessage()
                else:
                    parameters[14].setErrorMessage("Value can only contain characters and numbers, no special characters.")
            else:
                parameters[14].clearMessage()

            if parameters[15].value in (1,2,3,4,5,6,7):
                parameters[15].clearMessage()
            else:
                parameters[15].setErrorMessage("Value must be an integer (1-7)")

            # ----------------------------------------------------------------------

            # SEG_SHIELD Validation. If "Highway" make parameters required.
            if parameters[2].value == "H":
                if parameters[3].value not in ("ACE", "ACB", "COR", "GSP", "INT", "PIP", "STR","TPK","USR"):
                    parameters[3].setErrorMessage("SHIELD_TYPE_ID cannot be empty, please choose from the drop down")
##                elif parameters[3].value in ("ACE", "ACB", "GSP", "PIP", "TPK"):
##                     parameters[5].clearMessage()
                else:
                    parameters[3].clearMessage()
                if parameters[4].value not in ("A", "B", "C", "E", "M", "S", "T", "Y"):
                    parameters[4].setErrorMessage("SHIELD_SUBTYPE_ID cannot be empty, please choose from the drop down")
                else:
                    parameters[4].clearMessage()
                if parameters[3].value in ("ACE", "ACB", "GSP", "PIP", "TPK"):
                    parameters[5].clearMessage()
                elif parameters[5].value and parameters[3].value in ("COR", "INT", "STR", "USR"):
                    shname = parameters[5].valueAsText
                    # check to see if shield name is numeric, unless it begins with 'C' or 'S' or '9W' or '606A'
                    if parameters[5].value == '9W' or parameters[5].value == '606A' or shname[0].upper() == 'C' or shname[0].upper() == 'S':
                        parameters[5].clearMessage()
                    else:
                        try:
                            int(parameters[5].value)
                        except ValueError:
                            parameters[5].setErrorMessage("SHIELD_NAME must be numeric. Exceptions are; 'C' and 'S' for Bergen County, '9W', '606A', and Highway Authority Routes.")
                else:
                    parameters[5].setErrorMessage("SHIELD_NAME cannot be empty, please enter a name (text).")

        # ----------------------------------------------------------------------
        # Make sure the name type/ranks are valid
        L1H1 = [False]*2
        Els = ['L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8']
        if parameters[0].values:
            Rchecks = parameters[0].values
            ntr = []; err = False
            for Rcheck in Rchecks:
                ntr.append(Rcheck[2] + str(Rcheck[3]))
                if Rcheck[2] == 'L' and str(Rcheck[3]) == '1':
                    L1H1[0] = True
                if Rcheck[2] == 'H' and str(Rcheck[3]) == '1':
                    L1H1[1] = True

            if not L1H1[0] and not L1H1[1]:
                parameters[0].setErrorMessage("Missing L1 and/or H1 Name Record")

            if (not L1H1[0] and L1H1[1]) and len([x for x in ntr if x[0] == 'L' and int(x[1]) > 1 ]) > 0:
                parameters[0].setErrorMessage("Missing L1 and/or H1 Name Record")

            ntrsort = sorted(ntr, reverse=True)
            ntrsortlen = len(ntrsort)
            for i, v in enumerate(ntrsort):
                if i == ntrsortlen-1:
                    if v[1] != '1' if len(v) == 2 else False:
                        missing = v[0] + '1'
                        parameters[0].setErrorMessage("Rank Error: Missing {0} Record".format(missing))
                    break
                if v[0] == ntrsort[i+1][0]:
                    if (int(v[1]) - 1) != int(ntrsort[i+1][1]):
                        missing = v[0] + str(int(v[1]) - 1)
                        parameters[0].setErrorMessage("Rank Error: Missing {0} Record".format(missing))


            for i, v in enumerate(ntr):
                if ntr.count(v) > 1:
                    parameters[0].setErrorMessage("Duplicate {0} Records".format(v))
                    err = True
                    break
            curvals = [v[0] for v in parameters[0].values]
            for curv in curvals:
                if curv not in ('Record 1', 'Record 2', 'Record 3', 'Record 4', 'Record 5', 'Record 6', 'Record 7', 'Record 8', 'Record 9', 'Record 10', 'Record 11', 'Record 12'):
                    parameters[0].setErrorMessage('ID must be formatted like: Record 1, Record 2, etc.')
                    err = True
                    break
            # check for missing L1 or H1

            if not err:
                parameters[0].clearMessage()


        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        import os, sys, traceback
        import numpy as np
        global Records, Record, currentR, RecordsCleared


        editnamespath = arcpy.env.scratchWorkspace + "\\editnamesselection.p"
        if os.path.exists(editnamespath):
            with open(editnamespath,'rb') as editnamesopen:
                editnames_pickle = pickle.load(editnamesopen)
        updatecount = editnames_pickle['UPDATECOUNT']
        #arcpy.AddMessage('\nEXECUTE: updatecount: {0}'.format(updatecount))

        #arcpy.AddMessage('\nEXECUTE: editnames_pickle: {0}'.format(editnames_pickle))
        #arcpy.AddMessage('\nEXECUTE: parameters[0].values: {0}'.format(parameters[0].values))

        if arcpy.GetInstallInfo()['Version'] == '10.2.1':
            if updatecount <= 4:
                #arcpy.AddMessage('\n1')
                if editnames_pickle['segment'][0]:
                    #arcpy.AddMessage('\n2')
                    RecordsValues = editnames_pickle['segment'][1]
                else:
                    #arcpy.AddMessage('\n3')
                    RecordsValues = editnames_pickle['segment'][0]
            else:
                #arcpy.AddMessage('\n4')
                RecordsValues = parameters[0].values

        if arcpy.GetInstallInfo()['Version'] == '10.2.2' or arcpy.GetInstallInfo()['Version'] == '10.3'  or arcpy.GetInstallInfo()['Version'] == '10.3.1':
            if updatecount <= 3:
                #arcpy.AddMessage('\n5')
                if editnames_pickle['segment'][0]:
                    #arcpy.AddMessage('\n6')
                    RecordsValues = editnames_pickle['segment'][1]
                else:
                    #arcpy.AddMessage('\n7')
                    RecordsValues = editnames_pickle['segment'][0]
            else:
                #arcpy.AddMessage('\n8')
                RecordsValues = parameters[0].values

        #arcpy.AddMessage('\nEXECUTE:RecordsValues: {0}'.format(RecordsValues))
        #arcpy.AddMessage('\nEXECUTE:self.RecordsDict: {0}'.format(self.RecordsDict))

        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------

        # Delete or Update?
        for key,value in self.RecordsDict.iteritems():
            arcpy.AddMessage('\n____________________________________________________\nEvaluating {0}...'.format(key))
            present = False
            if RecordsValues:
                for i,rec in enumerate(RecordsValues):
                    if key == rec[0]:  #
                        present = True
                        presentInd = i
                        break
            if not present: #-------------------------Delete
                # delete the seg_name record
                seg_sql = erebus.sqlGUID("GLOBALID", value[0])
                try:
                    cursor =  arcpy.UpdateCursor(segnametab, seg_sql)
                    for row in cursor:
                        cursor.deleteRow(row)
                        arcpy.AddMessage('\nDeleted {0} SEG_NAME Record. {1}'.format(key, seg_sql))
                    del row, cursor
                    if value[1]: #if there is a shield records too...
                        seg_sql = erebus.sqlGUID("GLOBALID", value[1])
                        cursor =  arcpy.UpdateCursor(segshieldtab, seg_sql)
                        for row in cursor:
                            cursor.deleteRow(row)
                            arcpy.AddMessage('\nDeleted {0} SEG_SHIELD Record. {1}'.format(key ,seg_sql))
                        del row, cursor
                except:
                    Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                    try: row; del row
                    except: pass
                    try: cursor; del cursor
                    except: pass
                    trace = traceback.format_exc()
                    arcpy.AddMessage(trace)
                    sys.exit('block1')

            if present: #--------------------------Update
                try:
                    # compare RecordsValues to self.Records
                    changed= False
                    changeInds = []

                    for ij,rece in enumerate(self.Records):  #find the index in self.Roecords...because they wont necisarily be the same..
                        if key == rece[0]:  #
                            selfInd = ij
                            break

                    for j,field in enumerate(RecordsValues[presentInd]): # this is the record in RecordsValues that matches Dict
                        if field != self.Records[selfInd][j]:
                            if self.Records[selfInd][j] in ('', None, 'None') and field in ('', None, 'None'):
                                pass
                                #arcpy.AddMessage('\nFields are different, but no update: Original {0}, New {1}'.format(self.Records[selfInd][j], field))
                            else:
                                arcpy.AddMessage('\nFields are different: Original {0}, New {1}'.format(self.Records[selfInd][j], field))
                                changed = True  # there is a changed value...we need to update
                                changeInds.append(j)

                    if changed:
                        walkXsegname = {1: 'SEG_GUID', 2: 'NAME_TYPE_ID', 3: 'RANK', 4: 'NAME_FULL', 5: 'PRE_DIR', 6: 'PRE_TYPE', 7: 'PRE_MOD', 8: 'NAME', 9: 'SUF_TYPE', 10: 'SUF_DIR', 11: 'SUF_MOD', 12: 'DATA_SRC_TYPE_ID', 13: 'SHIELD_TYPE_ID', 14: 'SHIELD_SUBTYPE_ID', 15: 'SHIELD_NAME'}
                        seg_sql = erebus.sqlGUID("GLOBALID", value[0])
                        cursor = arcpy.UpdateCursor(segnametab, seg_sql)
                        for row in cursor:
                            for cc in changeInds:
                                if cc <= 12:
                                    row.setValue(walkXsegname[cc], RecordsValues[presentInd][cc])
                                    arcpy.AddMessage('\nUpdated {0} in SEG_NAME. {1}, \nUpdated {2} from {3} to {4}'.format(key ,seg_sql, walkXsegname[cc], self.Records[ij][cc], RecordsValues[i][cc]))
                                cursor.updateRow(row)
                        del row, cursor
                        if value[1]:
                            seg_sql = erebus.sqlGUID("GLOBALID", value[1])
                            cursor = arcpy.UpdateCursor(segshieldtab, seg_sql)
                            for row in cursor:
                                for cc in changeInds:
                                    if cc >= 12:
                                        row.setValue(walkXsegname[cc], RecordsValues[presentInd][cc])
                                        row.setValue('RANK', RecordsValues[presentInd][3])
                                        row.setValue('DATA_SRC_TYPE_ID', RecordsValues[presentInd][12])
                                        arcpy.AddMessage('\nUpdated {0} in SEG_SHIELD. {1}, \nUpdated {2} from {3} to {4}'.format(key ,seg_sql, walkXsegname[cc], self.Records[ij][cc], RecordsValues[i][cc]))
                                    cursor.updateRow(row)
                            del row, cursor

                except:
                    Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                    trace = traceback.format_exc()
                    try: row; del row
                    except: pass
                    try: cursor; del cursor
                    except: pass
                    arcpy.AddMessage(trace)
                    arcpy.AddMessage('\nchangeinds: {0}, cc {1}, RecordsValues {2}'.format(changeInds, cc ,RecordsValues[presentInd][cc]))
                    #arcpy.AddMessage('\nGlobals {0}'.format(globals()))
                    sys.exit('Error: Delete and Update Block')

        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------
        #-----------------------------------------------------------------------

        # Insert and there are existing records
        if RecordsValues:
            for y,rec in enumerate(RecordsValues):
                match = False
                for key,value in self.RecordsDict.iteritems():
                    if rec[0] == key:
                        match = True
                if not match: # no matching records, do an insert
                    arcpy.AddMessage('\n____________________________________________________\nEvaluating {0}...'.format(rec[0]))
                    if rec[1] and rec[2] and rec[3] and rec[4] and rec[8] and rec[12]:
                        try:
                            cursor = arcpy.InsertCursor(segnametab)
                            row = cursor.newRow()
                            row.setValue("SEG_GUID", rec[1])
                            row.setValue("NAME_TYPE_ID", rec[2])
                            row.setValue("RANK", rec[3])
                            row.setValue("NAME_FULL", rec[4])
                            row.setValue("NAME", rec[8])
                            row.setValue("DATA_SRC_TYPE_ID", rec[12])
                            if rec[5]:
                                row.setValue("PRE_DIR", rec[5])
                            if rec[6]:
                                row.setValue("PRE_TYPE", rec[6])
                            if rec[7]:
                                row.setValue("PRE_MOD", rec[7])
                            if rec[9]:
                                row.setValue("SUF_TYPE", rec[9])
                            if rec[10]:
                                row.setValue("SUF_DIR", rec[10])
                            if rec[11]:
                                row.setValue("SUF_MOD", rec[11])
                            cursor.insertRow(row)
                            arcpy.AddMessage('Inserted {0} into SEG_NAME, values are {1}'.format(rec[0], rec[1:12]))
                            del cursor, row
    #[u'Record 1', u'{2423FF3C-1708-11E3-B5F2-0062151309FF}', u'H', 1, u'County Route 619', u'', u'County Route', u'', u'619', u'ff', u'ffff', u'', 2, u'COR', u'M', u'619']
                            if rec[2] == 'H' and rec[13] and rec[14]:
                                cursor22 = arcpy.InsertCursor(segshieldtab)
                                row22 = cursor22.newRow()
                                row22.setValue("SEG_GUID", rec[1])
                                row22.setValue("RANK", rec[3])
                                row22.setValue("DATA_SRC_TYPE_ID", rec[12])
                                row22.setValue("SHIELD_TYPE_ID", rec[13])
                                row22.setValue("SHIELD_SUBTYPE_ID", rec[14])
                                if rec[15]:
                                    row22.setValue("SHIELD_NAME", rec[15])
                                cursor22.insertRow(row22)
                                arcpy.AddMessage('Inserted {0} into SEG_SHIELD, values are {1}'.format(rec[0], rec[12:15]))
                                del cursor22, row22
                            if rec[2] == 'H' and not rec[13] and not rec[14]:
                                Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                                arcpy.AddError('Missing Required Fields for SEG_SHIELD Insert. Required fields are; SHIELD_TYPE_ID, SHIELD_SUBTYPE_ID.')
                        except:
                            Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                            trace = traceback.format_exc()
                            try: row; del row
                            except: pass
                            try: cursor; del cursor
                            except: pass
                            try: row22; del row22
                            except: pass
                            try: cursor22; del cursor22
                            except: pass
                            arcpy.AddMessage(trace)
                            sys.exit('Error: Insert 2')
                    else:
                        arcpy.AddError('Missing Required Fields. Required fields are; SEG_GUID, NAME_TYPE_ID, RANK, NAME_FULL, NAME, and DATA_SRC_TYPE_ID.')

        #-----------------------------------------------------------------------
        # PRIME_NAME

        if parameters[16].value:

            try:
                ################################################################################
                ## Get current records in SEG_NAME
                seg_sql2 = erebus.sqlGUID("SEG_GUID", self.segguid)
                segname_current = [] # this is the list collector of tuples for each entry
                with arcpy.da.SearchCursor(segnametab, "*", seg_sql2) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        segname_current.append(row)
                if segname_current == []: # no records in segname. PRIME_NAME should be removed if there is one.
                    Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                    arcpy.AddWarning("PRIME NAME: There are no current records in SEG_NAME for this segment. If there is a record in SEGMENT.PRIME_NAME, it will be deleted.")

                    ## Update the record in SEGMENT
                    cursor = arcpy.UpdateCursor(segmentfc, seg_sql2)
                    for row in cursor:
                        if row.getValue("PRIME_NAME"):
                            currv = row.getValue("PRIME_NAME")
                            row.setValue("PRIME_NAME", None)
                            cursor.updateRow(row)
                            arcpy.AddWarning("\nPRIME_NAME successfully updated from {0} to {1}".format(currv ,'<null>'))
                        else:
                            arcpy.AddWarning('\nPRIME_NAME was not updated because it is already <null>. No need to update.')
                    del row, cursor

                else: # there is a name record

                    ################################################################################
                    ## Evaluate the available SEG_NAMES, then make a decision about what to insert into SEGMENT PRIME_NAME
                    ij = 0
                    ranktoken = np.zeros((len(segname_current),13), dtype=np.int)
                    for record in segname_current:
                        if record[3] == 'L' and record[4] == 1:
                            ranktoken[ij][0] = 1
                        elif record[3] == 'L' and record[4] == 2:
                            ranktoken[ij][1] = 1
                        elif record[3] == 'L' and record[4] == 3:
                            ranktoken[ij][2] = 1
                        elif record[3] == 'L' and record[4] == 4:
                            ranktoken[ij][3] = 1
                        elif record[3] == 'L' and record[4] == 5:
                            ranktoken[ij][4] = 1
                        elif record[3] == 'L' and record[4] == 6:
                            ranktoken[ij][5] = 1
                        elif record[3] == 'H' and record[4] == 1:
                            ranktoken[ij][6] = 1
                        elif record[3] == 'H' and record[4] == 2:
                            ranktoken[ij][7] = 1
                        elif record[3] == 'H' and record[4] == 3:
                            ranktoken[ij][8] = 1
                        elif record[3] == 'H' and record[4] == 4:
                            ranktoken[ij][9] = 1
                        elif record[3] == 'H' and record[4] == 5:
                            ranktoken[ij][10] = 1
                        elif record[3] == 'H' and record[4] == 6:
                            ranktoken[ij][11] = 1
                        else:
                            ranktoken[ij][12] = 1
                        ij += 1

                    ##########################################
                    ## 3.2) Find l1 or H1, if none throw error
                    # iterate through column zero to find if there are any L1
                    chosenone = None
                    if sum(ranktoken[:,0]) == 1:
                        bb = 0
                        for rr in ranktoken[:,0]:
                            if rr == 1:
                                chosenone = bb
                            bb += 1
                    else:
                        if sum(ranktoken[:,6]) == 1:
                            bb = 0
                            for rr in ranktoken[:,6]:
                                if rr == 1:
                                    chosenone = bb
                                bb += 1

                    if chosenone == None:
                        # build a dictionary to hold errors for the anlysis of current names
                        nameerr = {0: '\nBUILD NAMES ERROR: There is one or more Local/Rank 2 records, with no Local/Rank 1 record in SEG_NAME',
                        1: '\nBUILD NAMES ERROR: There is one or more Highway/Rank 2 records, with no Highway/Rank 1 record in SEG_NAME',
                        2: '\nBUILD NAMES ERROR: There is one or more Highway/Rank 3 records, with no Highway/Rank 2 record in SEG_NAME',
                        3: '\nBUILD NAMES ERROR: There is one or more Highway/Rank 3 records, with no Highway/Rank 1 record in SEG_NAME',
                        4: '\nBUILD NAMES ERROR: There is more than 1 Local/Rank 1 record in SEG_NAME',
                        5: '\nBUILD NAMES ERROR: There is more than 1 Highway/Rank 1 record in SEG_NAME',
                        6: '\nBUILD NAMES ERROR: In 1 or more records, there is a value other than L/1, L/2, H/1, H/2, H/3'}
                        errcollector = []
                        if sum(ranktoken[:,1]) >= 1 and sum(ranktoken[:,0]) == 0: # there is one or more L2, with no L1
                            errcollector.append(0)
                        if sum(ranktoken[:,3]) >= 1 and sum(ranktoken[:,2]) == 0: # there is one or more H2, with no H1
                            errcollector.append(1)
                        if sum(ranktoken[:,4]) >= 1 and sum(ranktoken[:,3]) == 0: # there is one or more H3, with no H2
                            errcollector.append(2)
                        if sum(ranktoken[:,4]) >= 1 and sum(ranktoken[:,2]) == 0: # there is one or more H3, with no H1
                            errcollector.append(3)
                        if sum(ranktoken[:,0]) > 0: # there is more than 1 L1
                            errcollector.append(4)
                        if sum(ranktoken[:,2]) > 0: # there is more than 1 H1
                            errcollector.append(5)
                        if sum(ranktoken[:,5]) > 0: # some other value in than L1, l2, h1, h2, h3 in one of the records
                            errcollector.append(6)
                        arcpy.AddMessage("BUILD NAMES: errcollector print out: {0}, ranktoken: {1}".format(errcollector,ranktoken))
                        if len(errcollector) > 0:
                            for erc in range(0,(len(errcollector))):
                                if erc == 0:
                                    mess = nameerr[errcollector[erc]]
                                if erc > 0:
                                    mess = mess + nameerr[errcollector[erc]]
                        Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                        arcpy.AddError("BUILD NAMES ERROR: No valid L1 or H1 in SEG_NAME, and..." + mess)

                    ##########################################
                    ## Construct the PRIME NAME entry
                    namelist = segname_current[chosenone][6:13]
                    #arcpy.AddMessage("ADD NAME: The chosen one is index {0}, and the attribs are {1}".format(chosenone,namelist))
                    primecatclass = erebus.FullName(namelist[0],namelist[1],namelist[2],namelist[3],namelist[4],namelist[5],namelist[6])
                    primename = primecatclass.concatenate()

                    try:
                        arcpy.AddMessage("\nPrime Name construction resulted in: {0}".format(primename))
                    except:
                        Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                        arcpy.AddError("\nPrime Name construction failed")

                    ##########################################
                    ## 3.4) Update the record in SEGMENT
                    cursor = arcpy.UpdateCursor(segmentfc, seg_sql2)
                    for row in cursor:
                        if row.getValue("PRIME_NAME") != primename:
                            currv = row.getValue("PRIME_NAME")
                            row.setValue("PRIME_NAME", primename)
                            cursor.updateRow(row)
                            arcpy.AddMessage("\nPRIME_NAME successfully updated from {0} to {1}".format(currv ,primename))
                        else:
                            arcpy.AddWarning('\nPRIME_NAME was not updated because it is already the same as NAME_FULL. No need to update.')
                    del row, cursor

            except:
                Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)
                trace = traceback.format_exc()
                try: row; del row
                except: pass
                try: cursor; del cursor
                except: pass
                arcpy.AddMessage(trace)
                sys.exit('Error: PRIME_NAME block failed')

        else:
            arcpy.AddWarning('PRIME_NAME will not be built')



        Records = []; Record = []; currentR = ""; RecordsCleared['status'] = ('',False)



## [u'L1', u'SEG_GUID',    u'name type id', 0,  u'namefull', u'predir', u'pretype', u'premod', u'name', u'suftype', u'sufdir', u'sufmod', u'datasrctupe', u'shieldtyp', u'sheid subtype', u'shieldname']
##[[u'L1', u'segguid', u'nametypeid', rank, u'namefull', u'predir', u'pretype', u'premod', u'name', u'suftype', u'sufdir', u'sufmod', u'datasrctypeid', u'shield type id', u'shield sub id', u'shield name'],
## [u'L1', u'1',          u'2',       3,   u'4',       u'5',       u'6',        u'7',     u'8',     u'9',     u'10',       u'11',       u'12',             u'13',            u'14',          u'15']]


##selfRecords values [['Record 1', u'{2423FF3C-1708-11E3-B5F2-0062151309FF}', u'H', 1, u'County Route 619', None, u'County Route', None, u'619', None, None, None, 2, u'COR', u'M', u'619'], ['Record 2', u'{2423FF3C-1708-11E3-B5F2-0062151309FF}', u'L', 1, u'Pinewald Keswick Road', u'aaa', u'dd', u'fff', u'Pinewald Keswick', u'Road', None, None, 2, '', '', '']]
##
##RecordsDict values {'Record 2': [u'{F96C1940-D941-48F9-A437-6CCC40AAFE51}', ''], 'Record 1': [u'{9B44F367-D65F-4A83-8731-BF0D24168E40}', u'{430B3C9C-2B52-4656-8F46-C26E4C61828D}']}
##
##RecordsValues values [[u'Record 1', u'{2423FF3C-1708-11E3-B5F2-0062151309FF}', u'H', 1, u'County Route 619', u'', u'County Route', u'', u'619', u'ff', u'ffff', u'', 2, u'COR', u'M', u'619'], [u'Record 2', u'{2423FF3C-1708-11E3-B5F2-0062151309FF}', u'L', 1, u'Pinewald Keswick Road', u'aaa', u'dd', u'fff', u'Pinewald Keswick', u'Road', u'', u'', 2, u'', u'', u'']]




# END EditNames
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
# ||||||||||||||||||||||||||||||||||\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\