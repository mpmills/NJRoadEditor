#-------------------------------------------------------------------------------
# Name:         SLD_Manager.pyt
# Purpose:      Python toolbox file.
#
# Authors:       NJ Office of GIS / Michael Baker International
# Contact:      gis-admin@oit.state.nj.us / michael.mills@mbakerintl.com
#
# Created:      1/19/2016
# Updated:      4/14/2016 Michael Baker International
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

import arcpy
import os
import sys
import erebus
import re
import pythonaddins
import math
import traceback
import decimal
import json

from arcpy import env

segmentfc = ""; segmentchangetab = ""; transtab = ""; segnametab = ""; segshieldtab = ""; segcommtab = ""; linreftab = ""; sldroutetab = "";

os.sys.path.append(os.path.dirname(__file__))

# This function determines your database and how the name should be formatted
def getlongnames(workspace, names):
    # workspace_type = 'sde'
    workspace_type = arcpy.env.workspace.split(".")[-1]
    if workspace_type == 'sde':
        try:
            import re
            desc = arcpy.Describe(workspace)
            conn = desc.connectionProperties

            inst = conn.instance
            ss = re.search('sql', inst, re.I)
            ora = re.search('oracle', inst, re.I)
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
    arcpy.AddMessage("There was an error identifing a table.")
    # pass


class Toolbox(object):

    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SLD_Manager"
        self.alias = "sld_manager"

        # List of tool classes associated with this toolbox
        self.tools = [ChangeSRI, RemilepostRoute]


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
                        where_clause="SRI='" + parameters[0].value + "'"
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

        os.sys.path.append(os.path.dirname(__file__))

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
        
        arcpy.AddMessage('\nUpdating SRI value globally.\n Original SRI: ' + parameters[0].value +
                         '\n New SRI: ' + parameters[1].value +
                         '\n Route Type: ' + parameters[2].value +
                         '\n RCF ID: ' + str(parameters[3].value))

        # sldroutetab    - sld route table
        # linreftab - linear ref table
      
        # ##
        # ##     SRI Updates to the SLD_ROUTE table
        # ##

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
        
        #
        #     SRI Updates to the LINEAR_REF table
        #

        # retain all messages for the linear_ref updates
        messages_linref = []

        try:

            field_names_linref = [ 'SRI', 'SEG_ID', 'GLOBALID' ]
            
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


class RemilepostRoute(object):

    print "Remilepost Route Tool"

    def __init__(self):
        """
        Remilepost Route:
        This tool will update the LINEAR_REF tables MILEPOST_FR, MILEPOST_TO, and RCF fields
        The associate segment geometries will also be updated (M Values)

        """
        self.label = "RemilepostRoute"
        self.description = "Update the route mile post values in LINEAR_REF Table and Segment feature class geometries"
        # self.canRunInBackground = False

        # global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldroutetab

    def getParameterInfo(self):
        """Define parameter definitions"""

        param_route_sri = arcpy.Parameter(
            displayName="SRI",
            name="route_sri",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        param_route_mp_from_current = arcpy.Parameter(
            displayName="Milepost From",
            name="route_mp_from_current",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        param_route_mp_from_current.filter.type = "ValueList"
        param_route_mp_from_current.filter.list = []
        param_route_mp_from_current.enabled = False

        param_route_mp_to_current = arcpy.Parameter(
            displayName="Milepost To",
            name="route_mp_to_current",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        param_route_mp_to_current.filter.type = "ValueList"
        param_route_mp_to_current.filter.list = []
        param_route_mp_to_current.enabled = False

        param_route_mp_from_new = arcpy.Parameter(
            displayName="New Milepost FROM",
            name="route_mp_from_new",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        param_route_mp_from_new.enabled = False

        param_route_mp_to_new = arcpy.Parameter(
            displayName="New Milepost TO",
            name="route_mp_from_to",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )
        param_route_mp_to_new.enabled = False

        param_route_mp_from_parent = arcpy.Parameter(
            displayName="Parent Milepost FROM",
            name="route_mp_from_parent",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param_route_mp_from_parent.enabled = False

        param_route_mp_to_parent = arcpy.Parameter(
            displayName="Parent Milepost TO",
            name="route_mp_to_parent",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input"
        )
        param_route_mp_to_parent.enabled = False

        param_route_change_form_id = arcpy.Parameter(
            displayName="Route Change Form ID",
            name="route_change_form_id",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        param_route_change_form_id.enabled = False

        params_RemilepostRoute = [
            param_route_sri,

            param_route_mp_from_current,
            param_route_mp_to_current,

            param_route_mp_from_new,
            param_route_mp_to_new,

            param_route_mp_from_parent,
            param_route_mp_to_parent,

            param_route_change_form_id
        ]

        return params_RemilepostRoute

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # when the sri has been updated, populate the milepost from and milepost to parameter inputs
        # the milepost_from and/or milepost_to parameters will be updated by the user but are included for reference

        if (not parameters[0].hasBeenValidated) or parameters[0].altered:

            p_route_sri = parameters[0].value

            mp_dropdown_data = arcpy.da.TableToNumPyArray(
                in_table=linreftab,
                field_names=[ "MILEPOST_FR", "MILEPOST_TO", "SEG_TYPE_ID" ],
                where_clause="SRI='" + p_route_sri + "' AND LRS_TYPE_ID IN (1)",
            )

            secondary = "S" in mp_dropdown_data[0][2]

            # get a sorted set of From mileposts for dropdown
            ary_from_current = [ round( f[ 0 ], 3 ) for f in mp_dropdown_data ]
            set_from_current = sorted( set( ary_from_current ) )

            # get a sorted set of To milesposts for dropdown
            ary_to_current = [ round( f[ 1 ], 3 ) for f in mp_dropdown_data ]
            set_to_current = sorted( set( ary_to_current ) )

            with arcpy.da.SearchCursor(
                in_table=linreftab,
                field_names=[ "SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF" ],
                where_clause="LRS_TYPE_ID=1 and SRI='" + p_route_sri + "'",
                sql_clause=(None, "ORDER BY MILEPOST_FR")

            ) as linrefCursor:

                count_linref = 0

                for linrefRow in linrefCursor:

                    if count_linref == 0:

                        distance_mp_from = float(linrefRow[2])
                    else:

                        distance_mp_to = float(linrefRow[3])

                    count_linref += 1

            parameters[ 1 ].enabled = True
            parameters[ 1 ].filter.list = set_from_current
            parameters[ 1 ].value = set_from_current[ 0 ]

            # enable it after the first dropdown is selected
            # parameters[2].enabled = True
            parameters[ 2 ].filter.list = set_to_current
            parameters[ 2 ].value = set_to_current[ len( set_to_current ) - 1 ]

            parameters[ 3 ].enabled = True
            parameters[ 4 ].enabled = True

            if secondary:

                parameters[ 5 ].enabled = True
                parameters[ 6 ].enabled = True

                parameters[ 5 ].parameterType = "Required"
                parameters[ 6 ].parameterType = "Required"

            parameters[7].enabled = True

        if (not parameters[ 1 ].hasBeenValidated) or parameters[ 1 ].altered:

            mp_from_selected = parameters[ 1 ].value

            # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
            # todo: filter to_milepost for values > from milepost selection

            parameters[ 2 ].enabled = True

        if (not parameters[ 2 ].hasBeenValidated) or parameters[ 2 ].altered:

            mp_from_selected = parameters[ 2 ].value

            arcpy.AddMessage( mp_from_selected )
            # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
            # todo: for val in parameters[2].filter.list:

        if (not parameters[ 3 ].hasBeenValidated) or parameters[ 3 ].altered:

            arcpy.AddMessage( mp_from_selected )

            # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
            # todo: for val in parameters[2].filter.list:

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        import traceback

        if parameters[0].value:

            param_route_sri = parameters[0].value

            if not arcpy.Exists(sldroutetab):

                parameters[0].setErrorMessage("Can not access the SLD ROUTE sde table.")

            else:

                # is user provided SRI in the list
                try:

                    with arcpy.da.SearchCursor(
                        in_table=sldroutetab,
                        field_names=["SRI"],
                        where_clause="SRI='" + param_route_sri + "'"
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

                            for x in range(1, 4):
                                parameters[x].enabled = False

                except Exception as ex:

                    parameters[0].setErrorMessage("Error with Parameter Value 0: " + param_route_sri + " \n " + ex.message + " - " + traceback.format_exc())

        try:

            # verify new mile post start value
            if parameters[1].value:

                param_route_mp_from_new = parameters[1].value

                if re.match("([0-9]+.?[0-9]{0,3})", str(param_route_mp_from_new)):

                    parameters[1].clearMessage()

                else:
                    parameters[1].setErrorMessage("Milepost FROM value must only contain two decimal places.")
        except Exception as ex:

            parameters[0].setErrorMessage("Error with Parameter Value 1: " + parameters[1].value + " \n " + ex.message + " - " + traceback.format_exc())

        # verify new mile post end value
        if parameters[2].value:

            param_route_mp_to_new = parameters[2].value

            if re.match("([0-9]+.?[0-9]{0,3})", str(param_route_mp_to_new)):

                parameters[2].clearMessage()
            else:
                parameters[2].setErrorMessage("Milepost TO value must only contain two decimal places.")

        # verify Route Change Form ID
        if parameters[7].value:

            param_route_change_form_id = parameters[7].value

            if re.match("[0-9]+", str(param_route_change_form_id)):

                parameters[7].clearMessage()
            else:
                parameters[7].setErrorMessage("RCF ID must be a numerical value.")

        # todo: saved value will be appended to existing RCF ID for auditing purposes


        return

    def execute(self, parameters, messages):

        global segmentfc

        """The source code of the tool."""

        # import arcpy
        # import os
        # import traceback

        os.sys.path.append(os.path.dirname(__file__))

        p_route_sri = parameters[ 0 ].value
        p_route_mp_from_current = parameters[ 1 ].value
        p_route_mp_to_current = parameters[ 2 ].value

        p_route_mp_from_new = parameters[ 3 ].value
        p_route_mp_to_new = parameters[ 4 ].value

        p_route_mp_from_parent = parameters[ 5 ]
        p_route_mp_to_parent = parameters[ 6 ]

        p_route_change_form_id = parameters[ 7 ].value

        #array position for easier reference
        pos_sid = 0
        pos_guid = 1
        pos_mpfrom = 2
        pos_mpto = 3
        pos_rcf = 4

        distance_mp_total = abs(float(p_route_mp_to_new) - float(p_route_mp_from_new))

        distance_total_mp = 0
        distance_total_gis = 0

        list_segment_guids = []
        list_segment_ids = []

        print "Route SRI: " + p_route_sri
        arcpy.AddMessage("Route SRI: " + p_route_sri)

        linRef_reference = {}

        # calculate current gis distance
        try:

            option1 = False
            option2 = True

            distances = []
            total_calculated_distance = 0

            where_clause_linRef = " LRS_TYPE_ID=1 " \
                                  " AND SRI='" + p_route_sri + "' " \
                                  " AND MILEPOST_FR >= " + str( p_route_mp_from_current ) + \
                                  " AND MILEPOST_TO <= " + str(p_route_mp_to_current )

            if option1:

                # option 1 collects all segment GUIDs from the lin ref table and then does one secondary search query
                # using search cursor vs tabletonumpyarray to support sorting by milepost

                arcpy.AddMessage( where_clause_linRef )

                with arcpy.da.SearchCursor(
                    in_table=linreftab,
                    field_names=[ "SEG_ID", "SEG_GUID" ],
                    where_clause=where_clause_linRef,
                    sql_clause=(None, "ORDER BY MILEPOST_FR")

                ) as distanceLinRefCursor:

                    for distanceLinRefRow in distanceLinRefCursor:

                        distances.append(distanceLinRefRow[1])

                arcpy.AddMessage(distances)

                where_clause_segments = " SEG_GUID IN ('" + "','".join([str(d) for d in distances]) + "')"

                arcpy.AddMessage(where_clause_segments)

                with arcpy.da.SearchCursor(
                    in_table=segmentfc,
                    field_names=["SHAPE@LENGTH"],
                    where_clause=where_clause_segments

                ) as distanceCursor:

                    for distanceRow in distanceCursor:

                        total_calculated_distance += distanceRow[0]

            elif option2 == True:

                # option 2 uses an inline cursor, where each segment feature is selected within the lin ref lookup
                # an SRI may have so many segments that the secondary where clause on the segment fc is too long.
                # this ensures that will never happen. but it will be slower.. we should
                # have some logic that determines which scenario it will use

                with arcpy.da.SearchCursor(
                    in_table=linreftab,
                    field_names=["SEG_ID", "SEG_GUID"],
                    where_clause=where_clause_linRef,
                    sql_clause=(None, "ORDER BY MILEPOST_FR")

                ) as distanceLinRefCursor:

                    for distanceLinRefRow in distanceLinRefCursor:

                        with arcpy.da.SearchCursor(
                            in_table=segmentfc,
                            field_names=["SHAPE@LENGTH"],
                            where_clause="SEG_GUID = '" + distanceLinRefRow[1] + "'"
                        ) as distanceCursor:

                            for distanceRow in distanceCursor:

                                total_calculated_distance += distanceRow[0]

            # todo: determine the scenario for updating

            arcpy.AddMessage("Total Calculated Distance from MP Start to MP End: " + str(total_calculated_distance))

            # calculate the scaling factor
            distance_conversion_factor =  distance_mp_total / ( total_calculated_distance / 5280)
            arcpy.AddMessage( "distance_mp_total:" + str( distance_mp_total ) )
            arcpy.AddMessage( "Distance Conversion Factor:" + str( distance_conversion_factor ) )

            # generate a collection of segments that will be updated, sorting by milepost_from
            # (not sure what happens when MILEPOST_FR field has an error)
            with arcpy.da.SearchCursor(
                in_table=linreftab,
                field_names=["SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF"],
                # where_clause="LRS_TYPE_ID=1 and SRI='" + p_route_sri + "'",
                where_clause=where_clause_linRef,
                sql_clause=(None, "ORDER BY MILEPOST_FR")

            ) as linrefCursor:

                count_linref = 0

                for linrefRow in linrefCursor:

                    # linRef_record = {}
                    # linRef_record["guid"] = linrefRow[pos_guid]
                    # linRef_record["mp_from"] = linrefRow[pos_mpfrom]
                    # linRef_record["mp_to"] = linrefRow[pos_mpto]
                    # linRef_record["distance"] = None
                    # linRef_record["order"] = count_linref

                    list_segment_guids.append(linrefRow[pos_guid])
                    list_segment_ids.append(linrefRow[pos_sid])

                    count_segment = 0

                    distance_segment_begin = distance_total_gis

                    arcpy.AddMessage("linrefRow")
                    arcpy.AddMessage(linrefRow)

                    ref_guid = linrefRow[pos_guid]

                    # create a segment cursor to update geometry M values
                    segmentCursor = arcpy.UpdateCursor(
                        segmentfc,
                        "SEG_GUID = '" + ref_guid + "'",
                        ["SHAPE@", "PRIME_NAME"]
                    )

                    # calculate updates for linref table values

                    for segmentRow in segmentCursor:

                        vertex_previous_geometry = {}
                        segVertexDistance = 0

                        # get the segment geometry and then vertices collections
                        segVerticesGeom = segmentRow.getValue( "SHAPE" )

                        # get json representation and look for true curves
                        j_seg = json.loads( segVerticesGeom.JSON )

                        segVertices = []

                        arcpy.AddMessage( j_seg )

                        # test for true curve
                        if "curvePaths" in j_seg:

                            # curves exist, so we'll need to get the well known text of the curve, which we will derive an x,y list from
                            seg_wkt = segVerticesGeom.WKT

                            arcpy.AddMessage( "seg_wkt" )
                            arcpy.AddMessage( seg_wkt )

                            # grab only the stuff within the parens
                            wkt_points = seg_wkt[ seg_wkt.find( "((" ) + 2:seg_wkt.find( "))" ) ]

                            points = wkt_points.split( ", " )

                            arcpy.AddMessage( "points" )
                            arcpy.AddMessage( points )

                            for point in points:
                                segVertices.append(point.strip( ).split( " " ))

                            newSegmentGeom = arcpy.Array( )
                            newSegmentPart = arcpy.Array( )

                            arcpy.AddMessage( "segVertices" )
                            arcpy.AddMessage( segVertices )

                            for i in range( len( segVertices ) ):

                                # grab the current segment vertex
                                segVertex = segVertices[ i ]

                                arcpy.AddMessage( "segVertex" )
                                arcpy.AddMessage( segVertex )

                                # create a new point object, essentially copying the existing one
                                vertex_point = arcpy.Point( segVertex[0], segVertex[1], None, segVertex[2] )

                                # create a point geometry from the point object.. necessary for distance measurement
                                vertex_geom = arcpy.PointGeometry( vertex_point )

                                # measure distance from previous vertex to current vertex. first vertex is at aggregate distance
                                if i > 0:
                                    segVertexDistance += (vertex_previous_geometry.distanceTo( vertex_geom ))

                                # set the current geometry as previous for next iteration
                                vertex_previous_geometry = vertex_geom

                                # set the point M value
                                # account for an aggregate of total route distance, convert to miles, round 3 decimal places
                                segVertex[2] = round( ((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor, 3 )

                                # create a new point for the updated vertex (could just recycle vertex_point..)
                                newSegmentVertex = arcpy.Point( segVertex[0], segVertex[1], None, segVertex[2] )

                                # add the segment vertex to the segment parts array
                                newSegmentPart.add( newSegmentVertex )

                            # add the segment part to the point collection
                            newSegmentGeom.add( newSegmentPart )

                            # add the total segment distance to aggregate distance (at beginning of new segment)
                            distance_total_gis += float( segVerticesGeom.length )

                            arcpy.AddMessage( "Vertex M: " + str( distance_total_gis + (segVertexDistance / 5280) ) )
                            arcpy.AddMessage( "Distance: " + str( segVertexDistance ) + "(" + str( segVertexDistance / 5280 ) + ")" )

                            # create the new polyline object, ensure SR. Z and M must be set to be able to update M
                            newSegment = arcpy.Polyline( newSegmentGeom, arcpy.SpatialReference( 3424 ), False, True )

                            # update the row geometry with the new polyline
                            segmentRow.setValue( "SHAPE", newSegment )

                            # update the row
                            segmentCursor.updateRow( segmentRow )

                            count_segment += 1

                        else:

                            segVertices = segVerticesGeom.getPart( 0 )

                            newSegmentGeom = arcpy.Array( )
                            newSegmentPart = arcpy.Array( )

                            arcpy.AddMessage( "segVertices" )
                            arcpy.AddMessage( segVertices )

                            for i in range( len( segVertices ) ):

                                # grab the current segment vertex
                                segVertex = segVertices[ i ]

                                arcpy.AddMessage( "segVertex" )
                                arcpy.AddMessage( segVertex )

                                # create a new point object, essentially copying the existing one
                                vertex_point = arcpy.Point( segVertex.X, segVertex.Y, None, segVertex.M )

                                # create a point geometry from the point object.. necessary for distance measurement
                                vertex_geom = arcpy.PointGeometry( vertex_point )

                                # measure distance from previous vertex to current vertex. first vertex is at aggregate distance
                                if i > 0:
                                    segVertexDistance += (vertex_previous_geometry.distanceTo( vertex_geom ))

                                # set the current geometry as previous for next iteration
                                vertex_previous_geometry = vertex_geom

                                # set the point M value
                                # account for an aggregate of total route distance, convert to miles, round 3 decimal places
                                segVertex.M = round( ((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor, 3 )

                                # create a new point for the updated vertex (could just recycle vertex_point..)
                                newSegmentVertex = arcpy.Point( segVertex.X, segVertex.Y, None, segVertex.M )

                                # add the segment vertex to the segment parts array
                                newSegmentPart.add( newSegmentVertex )

                            # add the segment part to the point collection
                            newSegmentGeom.add( newSegmentPart )

                            # add the total segment distance to aggregate distance (at beginning of new segment)
                            distance_total_gis += float( segVerticesGeom.length )

                            arcpy.AddMessage( "Vertex M: " + str( distance_total_gis + (segVertexDistance / 5280) ) )
                            arcpy.AddMessage( "Distance: " + str( segVertexDistance ) + "(" + str( segVertexDistance / 5280 ) + ")" )

                            # create the new polyline object, ensure SR. Z and M must be set to be able to update M
                            newSegment = arcpy.Polyline( newSegmentGeom, arcpy.SpatialReference( 3424 ), False, True )

                            # update the row geometry with the new polyline
                            segmentRow.setValue( "SHAPE", newSegment )

                            # update the row
                            segmentCursor.updateRow( segmentRow )

                            count_segment += 1

                    # todo: create of collection of 'update objects'
                    # which will then be paseed to a function specificially designed to update the linRef table

                    # update the MILEPOST_FROM value in the linref table
                    linRefUpdate_mp_from = round(distance_segment_begin / 5280, 3)
                    linRefUpdate_mp_to = round(distance_total_gis / 5280, 3)
                    linRefUpdate_rfc_id = (str(linrefRow[pos_rcf] or '') + " " + str(p_route_change_form_id)).strip()

                    lrUpdateFields = [ "SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF", "LRS_TYPE_ID", "SEG_TYPE_ID" ]

                    # used for lookups when reference related types.. Parent Mileposts, for example
                    npa = arcpy.da.TableToNumPyArray(
                        in_table='NJOIT_CENTERLINE.DBO.LINEAR_REF',
                        field_names=lrUpdateFields,
                        where_clause="SEG_GUID='" + ref_guid + "' AND LRS_TYPE_ID IN (1,2,3)"
                    )

                    with arcpy.da.UpdateCursor(
                            in_table=linreftab,
                            field_names=lrUpdateFields,
                            where_clause="SEG_GUID='" + ref_guid + "' AND LRS_TYPE_ID IN (1,2,3)"
                    ) as linrefUpdateCursor:

                        for linrefUpdateRecord in linrefUpdateCursor:

                            typeLRS = linrefUpdateRecord[5]
                            typeSeg = linrefUpdateRecord[6]

                            # PRIMARY SEGMENT
                            if typeSeg == "P":

                                if typeLRS in [1,3]:
                                    # scaled M values
                                    linrefUpdateRecord[ 2 ] = linRefUpdate_mp_from
                                    linrefUpdateRecord[ 3 ] = linRefUpdate_mp_to

                                elif typeLRS == 2:
                                    # flipped scaled m-values
                                    linrefUpdateRecord[ 2 ] = linRefUpdate_mp_to
                                    linrefUpdateRecord[ 3 ] = linRefUpdate_mp_from

                            # SECONDARY SEGMENT
                            elif typeSeg == "S":
                                pass

                            elif typeSeg == "E":
                                pass

                            elif typeSeg == "ES":
                                pass

                            elif typeSeg == "AD":
                                pass






                    # update the row
                    # linrefCursor.updateRow(linrefRow)

                    del segmentRow
                    del segmentCursor

            # del linrefCursor, linrefRow

        except arcpy.ExecuteError:

            arcpy.AddError(arcpy.GetMessages(2))

        except Exception as ex:

            arcpy.AddError(traceback.format_exc())

            e = sys.exc_info()[1]
            arcpy.AddMessage("Exception updating segment geometry: " + ex.message + "  ------- \n " + e.args[0])

        arcpy.AddMessage("Aggregate Distance by Geometry: " + str(distance_total_gis) + " feet.  " + str(distance_total_gis / 5280) + " miles.")
        arcpy.AddMessage("Milepost Distance: " + str(distance_total_mp) + " miles.")

        return


