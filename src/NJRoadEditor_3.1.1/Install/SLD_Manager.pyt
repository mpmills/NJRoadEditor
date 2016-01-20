#-------------------------------------------------------------------------------
# Name:         SLD_Manager.pyt
# Purpose:      Python toolbox file.
#
# Author:       NJ Office of GIS, Michael Baker International
# Contact:      gis-admin@oit.state.nj.us, michael.mills@mbakerintl.com
#
# Created:      1/19/2016
# Copyright:    (c) NJ Office of GIS 2014
# Licence:      GPLv3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#-------------------------------------------------------------------------------

import arcpy, pythonaddins
import os, sys, erebus, re
from arcpy import env

segmentfc = ""; segmentchangetab = ""; transtab = ""; segnametab = ""; segshieldtab = ""; segcommtab = ""; linreftab = ""; sldroutetab = "";

os.sys.path.append(os.path.dirname(__file__))

# This function determines your database and how the name should be formatted
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
# Below is the naming scheme for the layers and tables in the geodatabase. This is a requirement.
try:
    segmentfc = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT"], "Layer")
    segmentchangetab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_CHANGE"], "Layer")
    transtab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_TRANS"], "Table")
    segnametab = erebus.getlongname(arcpy.env.workspace, longnames["SEG_NAME"], "Table")
    segshieldtab = erebus.getlongname(arcpy.env.workspace, longnames["SEG_SHIELD"], "Table")
    segcommtab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_COMMENTS"], "Table")
    linreftab = erebus.getlongname(arcpy.env.workspace, longnames["LINEAR_REF"], "Table")
    sldroutetab = erebus.getlongname(arcpy.env.workspace, longnames["SLD_ROUTE"], "Table")
except:
    arcpy.MessageAdd("There was an error identifing a table.")
    # pass

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SLD_Manager"
        self.alias = "SLD_Manager"

        # List of tool classes associated with this toolbox
        self.tools = [ChangeSRI]


class ChangeSRI(object):

    print "Change SRI"

    def __init__(self):
        """
        Global Change SRI:
        This tool with update the SLD_Route and LINEAR_REF tables
        The SRI value in both fields will be updated with the new SRI which is provided by the user.
        """
        self.label = "ChangeSRI"
        self.description = "Update the SRI in the SLD_ROUTE and LINEAR_REF Tables"
        # self.canRunInBackground = False
        
        # global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldroutetab

    def getParameterInfo(self):
        """Define parameter definitions"""
        list_route_type = [d for d in arcpy.da.ListDomains(arcpy.env.workspace) if d.name == 'ROUTE_TYPE'][0].codedValues.values()
        
        param_sri = arcpy.Parameter(
            displayName="Route SRI",
            name="route_sri",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        param_sri_new = arcpy.Parameter(
            displayName="New Route SRI",
            name="route_sri_new",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        param_sri_new.enabled = False
        
        param_route_type = arcpy.Parameter(
            displayName="Route Type",
            name="route_type_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param_route_type.filter.type = "ValueList"
        param_route_type.filter.list = list_route_type
        param_route_type.enabled = False
            
        param_rcf_ID = arcpy.Parameter(
            displayName="RCF ID",
            name="rcf_ID",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input")
        param_rcf_ID.enabled = False
        
        params = [param_sri, param_sri_new, param_route_type, param_rcf_ID]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        
        if parameters[0].value:
            parameters[1].enabled = True
            
            if parameters[1].value:
                parameters[2].enabled = True

                if parameters[2].value:
                    parameters[3].enabled = True
                    
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        import traceback
        
        if parameters[0].value:
            
            list_route_sri = []
            
            if not arcpy.Exists(sldroutetab):

                parameters[0].setErrorMessage("Can not access the SLD ROUTE sde table.")
            else:
                
                # is user provided SRI in the list
                try:
                
                    with arcpy.da.SearchCursor(
                        in_table=sldroutetab,
                        field_names=["SRI"],
                        where_clause="SRI='"+ parameters[0].value +"'"
                    ) as c_segment:

                        sri_is_valid = False
                        for r_segment in c_segment:

                            if r_segment[0] != '':
                                sri_is_valid = True

                        if sri_is_valid:

                            parameters[0].clearMessage()
                            parameters[1].enabled = True
                        else:

                            parameters[0].setErrorMessage(parameters[0].value + ' is not a valid SRI')
                            for x in range(1,4):
                                parameters[x].enabled = False
                except Exception as ex:
                    parameters[0].setErrorMessage(ex.message + " - "  + traceback.format_exc())
        
        if parameters[1].value:
            
            p_sri = parameters[1].value
        
            if len(p_sri) not in [10, 17]:

                parameters[1].setErrorMessage("Value must conform to the 10 or 17 digit SRI naming convention.")
            else:

                if len(p_sri) == 10:

                    if re.match("[0-9a-zA-Z_]{10}", p_sri):
                        parameters[1].clearMessage()
                    else:
                        parameters[1].setErrorMessage("Value must conform to the SRI standard naming convention. 00000001__).")
                else:

                    if re.match("([0-9a-zA-Z_]{10})([ABCXYZ]?[1-9]?[0-9]{5}?)", p_sri):
                        parameters[1].clearMessage()
                    else:
                        parameters[1].setErrorMessage("Value must conform to the SRI standard naming convention. 00000001__A100123).")

        if parameters[3].value:

            if re.match("[0-9]+", str(parameters[3].value)):

                parameters[3].clearMessage()
            else:

                parameters[3].setErrorMessage("RCF ID must be a numerical value.")
        return

    def execute(self, parameters, messages):

        """The source code of the tool."""

        import arcpy, os, sys
        import traceback
        os.sys.path.append(os.path.dirname(__file__))
        import erebus

        # load Route Type Domain Values
        route_domain_values = [d for d in arcpy.da.ListDomains(arcpy.env.workspace) if d.name == 'ROUTE_TYPE'][0].codedValues
        
        p_sri = parameters[0].value
        p_sri_new = parameters[1].value
        p_route_type = parameters[2].value
        p_rcf_id = parameters[3].value

        try:

            route_type_id = int([k for k, v in route_domain_values.items() if v == p_route_type][0])

            # arcpy.AddMessage("Route type for " + str(p_route_type) + " identified. (" + str(route_type_id) + ")")

        except Exception as ex:

            arcpy.AddError('Type of ' + str(p_route_type) + ' was not found in the domain.')

        # test that you can get access to what is currently selected in the SEGMENT
        # count = int(arcpy.GetCount_management(sldroutetab).getOutput(0))
        
        arcpy.AddMessage('\nUpdating SRI value globally.\n Original SRI: ' + parameters[0].value + '\n New SRI: ' + parameters[1].value + '\n Route Type: ' + parameters[2].value + '\n RCF ID: ' + str(parameters[3].value))

        # sldroutetab    - sld route table
        # linreftab - linear ref table
      
        ###
        ###     SRI Updates to the SLD_ROUTE table
        ###

        # retain all messages for the sld_route updates
        messages_sldroute = []

        try:

            field_names_segment = ['SRI', 'ROUTE_TYPE_ID', 'SLD_NAME', 'GLOBALID']
           
            count_sldroute_update = 0

            where_clause = "SRI = '" + p_sri + "'"
            
            c_segment = arcpy.UpdateCursor(
                sldroutetab,
                where_clause,
                field_names_segment
            )
        
            for r_segment in c_segment:

                try:
                    r_segment.setValue("SRI", p_sri_new)
                    r_segment.setValue("ROUTE_TYPE_ID", route_type_id)

                    c_segment.updateRow(r_segment)

                except Exception as seg_ex:

                    arcpy.AddError('Error updating SRI in the SLD_ROUTE record: \n' + traceback.format_exc())

                finally:

                    count_sldroute_update += 1

                    messages_sldroute.append('  - globalid: ' + str(r_segment.getValue("GLOBALID")))

            # delete objects to remove locks
            if r_segment is not None:

                del r_segment
                del c_segment

        except Exception as ex:

            arcpy.AddError('Error occurred when updating the SLD_ROUTE table.\n' + traceback.format_exc())

        finally:

            # add summary message for SLD_ROUTE table updates.
            arcpy.AddMessage("\nSRI updated for " + str(count_sldroute_update) + " record" + ("s" if count_sldroute_update > 1 else "") + " in SLD_ROUTE.\n" + "\n".join(messages_sldroute))
        
        ###
        ###     SRI Updates to the LINEAR_REF table
        ###

        # retain all messages for the linear_ref updates
        messages_linref = []

        try:

            field_names_linref = ['SRI', 'SEG_ID', 'GLOBALID']
            
            where_clause = "SRI = '" + p_sri + "'"

            # initialize the update cursor
            c_segment = arcpy.UpdateCursor(
                linreftab,
                where_clause,
                field_names_linref
            )

            count_linref_update = 0

            for r_segment in c_segment:

                try:

                    r_segment.setValue("SRI", p_sri_new)
                    c_segment.updateRow(r_segment)

                except Exception as linref_ex:

                    arcpy.AddMessage('Error updating SRI in the LINEAR_REF record: \n' + traceback.format_exc())

                finally:

                    count_linref_update += 1
                    messages_linref.append('  - globalid: ' + str(r_segment.getValue('GLOBALID')))

            if r_segment is not None:

                del r_segment
                del c_segment

        except Exception as ex:

            arcpy.AddError('Error occurred while updating LINEAR_REF table.\n' + traceback.format_exc())
 
        finally:
            arcpy.AddMessage("\nSRI updated for " + str(count_linref_update) + " record" + ("s" if count_sldroute_update > 1 else "") + " in LINEAR_REF. \n" + "\n".join(messages_linref))

        return

