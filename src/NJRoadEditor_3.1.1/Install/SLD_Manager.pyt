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

        # if (not parameters[0].hasBeenValidated) or parameters[0].altered:
        if parameters[0].value:

            if not parameters[0].hasBeenValidated:

                p_route_sri = parameters[0].value

                mp_dropdown_data = arcpy.da.TableToNumPyArray(
                    in_table=linreftab,
                    field_names=[ "MILEPOST_FR", "MILEPOST_TO", "SEG_TYPE_ID" ],
                    where_clause="SRI='" + p_route_sri + "' AND LRS_TYPE_ID IN (1)",
                )

                secondary = "S" in mp_dropdown_data[0][2]

                # get a sorted set of From mileposts for dropdown
                # ary_from_current = [ round( f[ 0 ], 3 ) for f in mp_dropdown_data ]
                set_from_current = sorted( set( [ round( f[ 0 ], 3 ) for f in mp_dropdown_data ] ) )

                # get a sorted set of To mileposts for dropdown
                # ary_to_current = [ round( t[ 1 ], 3 ) for t in mp_dropdown_data ]
                set_to_current = sorted( set( [ round( t[ 1 ], 3 ) for t in mp_dropdown_data ] ) )

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

            if parameters[ 1 ].value:

                if not parameters[ 1 ].hasBeenValidated:

                    mp_from_selected = parameters[ 1 ].value

                    # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
                    if mp_from_selected > parameters[ 2 ].value:
                        parameters[ 2 ].setErrorMessage("From Mile Post is > To Mile Post")
                    else:
                        parameters[ 2 ].clearMessage()
                    # todo: filter to_milepost for values > from milepost selection

                        parameters[ 2 ].enabled = True

                    # if (not parameters[ 2 ].hasBeenValidated) or parameters[ 2 ].altered:
                    if parameters[ 2 ].value:

                        if not parameters[ 2 ].hasBeenValidated:

                            mp_from_selected = parameters[ 2 ].value

                            arcpy.AddMessage( mp_from_selected )
                            # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
                            # todo: for val in parameters[2].filter.list:

                            # if (not parameters[ 3 ].hasBeenValidated) or parameters[ 3 ].altered:
                            if parameters[ 3 ].value:

                                if not parameters[ 3 ].hasBeenValidated:

                                    arcpy.AddMessage( mp_from_selected )

                                    # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
                                    # todo: for val in parameters[2].filter.list:

        return parameters

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        import traceback

        if parameters[0].value:

            if not parameters[0].hasBeenValidated:

                param_route_sri = parameters[0].value

                if not arcpy.Exists(sldroutetab):

                    parameters[0].setErrorMessage("Can not access the SLD ROUTE sde table.")

                else:

                    # is user provided SRI in the list
                    try:

                        with arcpy.da.SearchCursor(
                            in_table=sldroutetab,
                            field_names=[ "SRI" ],
                            where_clause="SRI='" + param_route_sri + "'"
                        ) as c_segment:

                            sri_is_valid = False

                            for r_segment in c_segment:

                                if r_segment[ 0 ] != '':
                                    sri_is_valid = True

                            if sri_is_valid:

                                parameters[ 0 ].clearMessage( )
                                parameters[ 1 ].enabled = True

                            else:

                                parameters[ 0 ].setErrorMessage( parameters[ 0 ].value + ' is not a valid SRI' )

                                for x in range( 1, 4 ):
                                    parameters[ x ].enabled = False

                    except Exception as ex:

                        parameters[0].setErrorMessage("Error with Parameter Value 0: " + param_route_sri + " \n " + ex.message + " - " + traceback.format_exc())

        try:

            # verify new mile post start value
            if parameters[1].value:

                clear_messages = False

                param_route_mp_from_new = parameters[1].value

                if re.match( "([0-9]+.?[0-9]{0,3})", str( param_route_mp_from_new ) ):
                    clear_messages = True
                else:
                    parameters[ 1 ].setErrorMessage( "Milepost FROM value must only contain two decimal places." )

        except Exception as ex:
            parameters[0].setErrorMessage("Error with Parameter Value 1: " + parameters[1].value + " \n " + ex.message + " - " + traceback.format_exc())

        # verify new mile post end value
        if parameters[2].value:

            param_route_mp_to_new = parameters[2].value

            if re.match( "([0-9]+.?[0-9]{0,3})", str( param_route_mp_to_new ) ):

                parameters[ 2 ].clearMessage( )
            else:
                parameters[ 2 ].setErrorMessage( "Milepost TO value must only contain two decimal places." )

        # verify Route Change Form ID
        if parameters[7].value:

            param_route_change_form_id = parameters[7].value

            if re.match( "[0-9]+", str( param_route_change_form_id ) ):

                parameters[7].clearMessage()
            else:
                parameters[ 7 ].setErrorMessage( "RCF ID must be a numerical value." )

        # todo: saved value will be appended to existing RCF ID for auditing purposes

        return

    def execute(self, parameters, messages):

        def getSegmentUpdateObject( seg_guid, type_seg, mp_from, mp_to, mp_from_parent, mp_to_parent, length, rcf_id ):

            update_object = { }

            if type_seg in [ "P", "E" ]:

                isPrimary = True

                #todo: primary parent is also flipped!

                update_object[ seg_guid ] = {
                    'isPrimary' : isPrimary,
                    'length' : 0,
                    'rcf_id': rcf_id,
                    'lrs_1': {
                        'from': mp_from,
                        'to': mp_to
                    },
                    'lrs_2': {
                        'from': mp_to,
                        'to': mp_from
                    },
                    'lrs_3': {
                        'from': mp_from,
                        'to': mp_to
                    }
                }

            else:

                isPrimary = False

                update_object[ seg_guid ] = {
                    'isPrimary': isPrimary,
                    'length': 1,
                    'rcf_id': rcf_id,
                    'lrs_1': {
                        'from': mp_from,
                        'to': mp_to
                    },
                    'lrs_2': {
                        'from': mp_to_parent,
                        'to': mp_from_parent
                    },
                    'lrs_3': {
                        'from': mp_from_parent,
                        'to': mp_to_parent
                    }
                }

            return update_object

        global segmentfc

        """The source code of the tool."""

        # import arcpy
        # import os
        # import traceback

        os.sys.path.append( os.path.dirname( __file__ ) )

        p_route_sri = parameters[ 0 ].value

        p_route_mp_from_current = parameters[ 1 ].value
        p_route_mp_to_current = parameters[ 2 ].value

        p_route_mp_from_new = parameters[ 3 ].value
        p_route_mp_to_new = parameters[ 4 ].value

        p_route_mp_from_parent = parameters[ 5 ].value or 0
        p_route_mp_to_parent = parameters[ 6 ].value or 0

        p_route_change_form_id = parameters[ 7 ].value

        #array position for easier reference
        pos_sid = 0
        pos_guid = 1
        pos_mpfrom = 2
        pos_mpto = 3
        pos_rcf = 4
        pos_lrsid = 5
        pos_seg_typeid = 6

        if not len(p_route_sri) == 10:
            arcpy.AddError("Only routes are currently supported.")

        distance_total_mp = 0
        # distance_total_gis = 0

        # set the starting total MP value.. New MP in feet
        distance_total_gis = 0

        print "Route SRI: " + p_route_sri
        arcpy.AddMessage( "Route SRI: " + p_route_sri )

        where_clause_linRef = ""

        # calculate current gis distance
        try:

            total_calculated_distance = 0

            where_clause_linRef = " SRI = '" + p_route_sri + "' AND LRS_TYPE_ID IN ( 1 ) " \
                                  " AND MILEPOST_FR >= " + str( p_route_mp_from_current ) + \
                                  " AND MILEPOST_TO <= " + str( p_route_mp_to_current )
            count_type = 0
            segment_type = ""

            with arcpy.da.SearchCursor(
                    in_table=linreftab,
                    field_names=["SEG_ID", "SEG_GUID", "SEG_TYPE_ID"],
                    where_clause=where_clause_linRef,
                    sql_clause=(None, "ORDER BY MILEPOST_FR")

            ) as distanceLinRefCursor:

                for distanceLinRefRow in distanceLinRefCursor:

                    if count_type == 0:
                        segment_type = distanceLinRefRow[2]
                        count_type += 1

                    with arcpy.da.SearchCursor(
                            in_table=segmentfc,
                            field_names=["SHAPE@LENGTH"],
                            where_clause="SEG_GUID = '" + distanceLinRefRow[1] + "'"
                    ) as distanceCursor:

                        for distanceRow in distanceCursor:

                            total_calculated_distance += distanceRow[0]

            arcpy.AddMessage( "Segment Type: " + str(segment_type) )

        except arcpy.ExecuteError:

            arcpy.AddError( arcpy.GetMessages( 2 ) )

        except Exception as ex:

            arcpy.AddError( traceback.format_exc( ) )
            e = sys.exc_info( )[ 1 ]
            arcpy.AddMessage( "Exception calculating total route distance: " + ex.message + "  ------- \n " + e.args[ 0 ] )

        try:

            # for primary routes, we will take the New Milepost From/To
            # for secondary routes, we'll take the Parent Milepost From/To

            if segment_type in [ "P", "E" ]:
                distance_mp_total = abs( float( p_route_mp_to_new ) - float( p_route_mp_from_new ) )
                distance_mp_total_parent = abs( float( p_route_mp_to_new ) - float( p_route_mp_from_new ) )
            else:
                distance_mp_total = abs( float( p_route_mp_to_new ) - float( p_route_mp_from_new ) )
                distance_mp_total_parent = abs( float( p_route_mp_to_parent ) - float( p_route_mp_from_parent ) )

            arcpy.AddMessage( "Total Calculated Distance from MP Start to MP End: " + str( total_calculated_distance ) )

            # calculate the scaling factor
            distance_conversion_factor =  distance_mp_total / ( total_calculated_distance / 5280)
            distance_conversion_factor_parent = distance_mp_total_parent / ( total_calculated_distance / 5280)

            arcpy.AddMessage( "distance_mp_total:" + str( distance_mp_total ) )
            arcpy.AddMessage( "Distance Conversion Factor:" + str( distance_conversion_factor ) )

        except arcpy.ExecuteError:

            arcpy.AddError( arcpy.GetMessages( 2 ) )

        except Exception as ex:

            arcpy.AddError( traceback.format_exc( ) )
            e = sys.exc_info( )[ 1 ]
            arcpy.AddMessage( "Exception calculating distance conversion factor: " + ex.message + "  ------- \n " + e.args[ 0 ] )

        try:

            # generate a collection of segments that will be updated, sorting by milepost_from
            # todo: what if MILEPOST_FR or MILEPOST_TO has a data error

            count_linref = 0
            mp_segment_begin = float( p_route_mp_from_new )
            mp_segment_begin_parent = float( p_route_mp_from_parent)

            linref_updates = []

            with arcpy.da.SearchCursor(
                in_table=linreftab,
                field_names=[ "SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF", "LRS_TYPE_ID", "SEG_TYPE_ID" ],
                # where_clause="LRS_TYPE_ID=1 and SRI='" + p_route_sri + "'",
                where_clause=where_clause_linRef,
                sql_clause=( None, "ORDER BY MILEPOST_FR" )

            ) as linrefCursor:

                for linrefRow in linrefCursor:

                    count_segment = 0

                    count_linref += 1
                    current_vertex_m = 0
                    current_vertex_m_parent = 0

                    arcpy.AddMessage( "MP at start of segment" )
                    arcpy.AddMessage( "    Segment:" + str( round( mp_segment_begin, 3 ) ) )
                    arcpy.AddMessage( "    Parent:" + str( round( mp_segment_begin_parent, 3 ) ) )

                    arcpy.AddMessage( "linrefRow" )
                    arcpy.AddMessage( linrefRow )

                    ref_guid = linrefRow[pos_guid]

                    # create a segment cursor to update geometry M values
                    segmentCursor = arcpy.UpdateCursor(
                        segmentfc,
                        "SEG_GUID = '" + ref_guid + "'",
                        ["SHAPE@", "PRIME_NAME"]
                    )

                    # calculate updates for linref table values
                    if count_linref == 1:
                        pass
                        # set from as user input

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

                            # curves exist, so we'll use the well known text of the geometry, which converts true curves to polylines with many segments
                            # we will derive an x,y,m list from the wkt and add M values to all of the newly created segment parts
                            seg_wkt = segVerticesGeom.WKT

                            arcpy.AddMessage( "seg_wkt" )
                            arcpy.AddMessage( seg_wkt )

                            # collect all the points
                            wkt_points = seg_wkt[ seg_wkt.find( "((" ) + 2:seg_wkt.find( "))" ) ]

                            segment_vertex_points = wkt_points.split( ", " )

                            arcpy.AddMessage( "segment_vertex_points" )
                            arcpy.AddMessage( segment_vertex_points )

                            for point in segment_vertex_points:
                                segVertices.append(point.strip( ).split( " " ))

                            # create arrays to hold the full segment geometry and the individual parts
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
                                # we have to use index based access for segment parts
                                vertex_point = arcpy.Point( segVertex[ 0 ], segVertex[ 1 ], None, segVertex[ 2 ] )

                                # create a point geometry from the point object.. necessary for distance measurement
                                vertex_geom = arcpy.PointGeometry( vertex_point )

                                # measure distance from previous vertex to current vertex. first vertex is at aggregate distance
                                if i > 0:
                                    segVertexDistance += (vertex_previous_geometry.distanceTo( vertex_geom ))

                                # set the current geometry as previous for next iteration
                                vertex_previous_geometry = vertex_geom

                                # set the point M value
                                # account for an aggregate of route distance, convert to miles, round 3 decimal places
                                # set the point M value
                                current_vertex_m = round( (((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor) + p_route_mp_from_new, 3 )
                                current_vertex_m_parent = round( p_route_mp_from_parent - (((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor_parent), 3 )

                                # segVertex[ 2 ] = round( ((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor, 3 )
                                segVertex[ 2 ] = current_vertex_m

                                # create a new point for the updated vertex
                                newSegmentVertex = arcpy.Point( segVertex[ 0 ], segVertex[ 1 ], None, segVertex[ 2 ] )

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

                            mp_segment_end = current_vertex_m
                            mp_segment_end_parent = current_vertex_m_parent

                            # update the row
                            segmentCursor.updateRow( segmentRow )

                            count_segment += 1

                        else:
                            # pull the geometry from the shape representation
                            segVertices = segVerticesGeom.getPart( 0 )

                            # create arrays to hold the full segment geometry and the individual parts
                            newSegmentGeom = arcpy.Array( )
                            newSegmentPart = arcpy.Array( )

                            arcpy.AddMessage( "segVertices" )
                            arcpy.AddMessage( segVertices )

                            for i in range( len( segVertices ) ):

                                # grab the current segment vertex
                                segVertex = segVertices[ i ]

                                # create a new point object, essentially copying the existing one
                                vertex_point = arcpy.Point( segVertex.X, segVertex.Y, None, segVertex.M )

                                # create a point geometry from the point object.. necessary for distance measurement
                                vertex_geom = arcpy.PointGeometry( vertex_point )

                                # measure distance from previous vertex to current vertex. first vertex is at aggregate distance
                                if i > 0:
                                    segVertexDistance += (vertex_previous_geometry.distanceTo( vertex_geom ))

                                # arcpy.AddMessage( "distance_total_gis: " + str( distance_total_gis ))
                                # arcpy.AddMessage( "p_route_mp_from_new: " + str( p_route_mp_from_new ))
                                # arcpy.AddMessage( "segVertexDistance: " + str( segVertexDistance ) + " ")
                                # arcpy.AddMessage( "distance_conversion_factor: " + str( distance_conversion_factor ))
                                arcpy.AddMessage( "segVertex.M: " + str(round( ( (( distance_total_gis + segVertexDistance ) / 5280 ) * distance_conversion_factor) + p_route_mp_from_new, 3 ) ))

                                # set the current geometry as previous for next iteration
                                vertex_previous_geometry = vertex_geom

                                # set the point M value
                                current_vertex_m = round( (( ( distance_total_gis + segVertexDistance ) / 5280 ) * distance_conversion_factor) + p_route_mp_from_new, 3 )
                                current_vertex_m_parent = round( p_route_mp_from_parent - (((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor_parent), 3 )

                                # account for an aggregate of total route distance, convert to miles, round 3 decimal places
                                segVertex.M = current_vertex_m

                                # create a new point for the updated vertex
                                newSegmentVertex = arcpy.Point( segVertex.X, segVertex.Y, None, segVertex.M )

                                # add the segment vertex to the segment parts array
                                newSegmentPart.add( newSegmentVertex )

                            # add the segment part to the point collection
                            newSegmentGeom.add( newSegmentPart )

                            # add the total segment distance to aggregate distance (at beginning of new segment)
                            distance_total_gis += float( segVerticesGeom.length )

                            arcpy.AddMessage( "Segment Total Distance: " + str( segVertexDistance ) + " (" + str( round( segVertexDistance / 5280, 3 ) ) + ")" )

                            # create the new polyline object, ensure SR. Z and M must be set to be able to update M
                            newSegment = arcpy.Polyline( newSegmentGeom, arcpy.SpatialReference( 3424 ), False, True )

                            arcpy.AddMessage( "Current Vertex M value: " + str( current_vertex_m ) )
                            arcpy.AddMessage( "Current Vertex M value parent: " + str( current_vertex_m_parent ) )

                            mp_segment_end = current_vertex_m
                            mp_segment_end_parent = current_vertex_m_parent

                            # update the row geometry with the new polyline
                            segmentRow.setValue( "SHAPE", newSegment )

                            # update the row
                            # only update row when lrs type is 1.. for now, we are recalculating the geometries until we move this into a seconary cursor update
                            segmentCursor.updateRow( segmentRow )

                            count_segment += 1

                    del segmentRow
                    del segmentCursor

                    #### LINEAR_REF Updates, values stored in dictionary and updated after geometry calculations and updates

                    linRefUpdate_rcf_id = (str( linrefRow[ pos_rcf ] or '' ) + " " + str( p_route_change_form_id )).strip( )

                    # set the MILEPOST_FROM value for the update object
                    # linRefUpdate_mp_to = linRefUpdate_mp_from + round( (distance_total_gis / 5280) * distance_conversion_factor, 3)

                    linRefUpdate_mp_from = mp_segment_begin
                    linRefUpdate_mp_to = mp_segment_end

                    linRefUpdate_mp_from_parent = mp_segment_begin_parent
                    linRefUpdate_mp_to_parent = mp_segment_end_parent

                    typeSeg = linrefRow[ pos_seg_typeid ]
                    if typeSeg not in ["P", "S", "E", "ES"]:
                        raise Exception( 'Segment type was not properly identified.' )

                    arcpy.AddMessage("linRefUpdate_mp_from: " + str(linRefUpdate_mp_from))
                    arcpy.AddMessage("linRefUpdate_mp_to: " + str(linRefUpdate_mp_to ))

                    arcpy.AddMessage( "linRefUpdate_mp_from_parent: " + str( linRefUpdate_mp_from_parent ) )
                    arcpy.AddMessage( "linRefUpdate_mp_to_parent: " + str( linRefUpdate_mp_to_parent ) )

                    update_rec = getSegmentUpdateObject(
                        seg_guid = ref_guid,
                        type_seg = typeSeg,
                        mp_from = linRefUpdate_mp_from,
                        mp_to = linRefUpdate_mp_to,
                        mp_from_parent = linRefUpdate_mp_from_parent,
                        mp_to_parent = linRefUpdate_mp_to_parent,
                        length = None,
                        rcf_id = linRefUpdate_rcf_id
                    )

                    arcpy.AddMessage("Linear Reference Table Update Object")
                    arcpy.AddMessage( update_rec )

                    # set the next segment from milepost as the current segment end mile post
                    mp_segment_begin = mp_segment_end
                    mp_segment_begin_parent = mp_segment_end_parent

                    linref_updates.append( update_rec )

        except arcpy.ExecuteError:

            arcpy.AddError(arcpy.GetMessages(2))

        except Exception as ex:

            arcpy.AddError(traceback.format_exc())

            e = sys.exc_info()[1]
            arcpy.AddMessage("Exception updating segment geometry: " + ex.message + "  ------- \n " + e.args[0])

        arcpy.AddMessage("Aggregate Distance by Geometry: " + str(distance_total_gis) + " feet.  " + str(distance_total_gis / 5280) + " miles.")
        arcpy.AddMessage("Milepost Distance: " + str(distance_mp_total) + " miles.")

        # now cycle through lin ref update objects and update corresponding table records
        try:

            arcpy.AddMessage( "linref_updates" )
            arcpy.AddMessage( linref_updates )

            for linref_update in linref_updates:

                seg_guid = linref_update.keys()[0]
                linref_rec = linref_update[ seg_guid ]

                with arcpy.da.UpdateCursor(
                    in_table=linreftab,
                    field_names=["SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF", "LRS_TYPE_ID", "SEG_TYPE_ID", "SRI"],
                    where_clause="SEG_GUID = '" + seg_guid + "' AND LRS_TYPE_ID IN ( 1, 2, 3)"
                ) as uc:

                    for ur in uc:

                        # sri is primary
                        # if ur[6] in ["E","ES"]:

                        lrs_type_id = ur[5]

                        arcpy.AddMessage( "update lrs_type_id" + str( lrs_type_id ) )
                        # update from
                        ur[ 2 ] = linref_rec[ "lrs_" + str( lrs_type_id ) ][ 'from' ]

                        # update to
                        ur[ 3 ] = linref_rec[ "lrs_" + str( lrs_type_id ) ][ 'to' ]

                        # update route change form ID
                        ur[ 4 ] = linref_rec[ 'rcf_id' ]

                        arcpy.AddMessage( 'updated linear reference table' )
                        arcpy.AddMessage( ur )

                        uc.updateRow( ur )

        except arcpy.ExecuteError:

            arcpy.AddError( arcpy.GetMessages( 2 ) )

        except Exception as ex:

            arcpy.AddError( traceback.format_exc( ) )

            e = sys.exc_info( )[ 1 ]
            arcpy.AddMessage( "Exception updating segment geometry: " + ex.message + "  ------- \n " + e.args[ 0 ] )

        return


# class RemilepostRamp(object):
#
#     print "Remilepost Route Tool"
#
#     def __init__(self):
#         """
#         Remilepost Route:
#         This tool will update the LINEAR_REF tables MILEPOST_FR, MILEPOST_TO, and RCF fields
#         The associate segment geometries will also be updated (M Values)
#
#         """
#         self.label = "RemilepostRoute"
#         self.description = "Update the route mile post values in LINEAR_REF Table and Segment feature class geometries"
#         # self.canRunInBackground = False
#
#         # global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldroutetab
#
#     def getParameterInfo(self):
#         """Define parameter definitions"""
#
#         param_route_sri = arcpy.Parameter(
#             displayName="SRI",
#             name="route_sri",
#             datatype="GPString",
#             parameterType="Required",
#             direction="Input"
#         )
#
#         param_route_mp_from_current = arcpy.Parameter(
#             displayName="Milepost From",
#             name="route_mp_from_current",
#             datatype="GPDouble",
#             parameterType="Required",
#             direction="Input"
#         )
#
#         param_route_mp_from_current.filter.type = "ValueList"
#         param_route_mp_from_current.filter.list = []
#         param_route_mp_from_current.enabled = False
#
#         param_route_mp_to_current = arcpy.Parameter(
#             displayName="Milepost To",
#             name="route_mp_to_current",
#             datatype="GPDouble",
#             parameterType="Required",
#             direction="Input"
#         )
#
#         param_route_mp_to_current.filter.type = "ValueList"
#         param_route_mp_to_current.filter.list = []
#         param_route_mp_to_current.enabled = False
#
#         param_route_mp_from_new = arcpy.Parameter(
#             displayName="New Milepost FROM",
#             name="route_mp_from_new",
#             datatype="GPDouble",
#             parameterType="Required",
#             direction="Input"
#         )
#         param_route_mp_from_new.enabled = False
#
#         param_route_mp_to_new = arcpy.Parameter(
#             displayName="New Milepost TO",
#             name="route_mp_from_to",
#             datatype="GPDouble",
#             parameterType="Required",
#             direction="Input"
#         )
#         param_route_mp_to_new.enabled = False
#
#         param_route_mp_from_parent = arcpy.Parameter(
#             displayName="Parent Milepost FROM",
#             name="route_mp_from_parent",
#             datatype="GPDouble",
#             parameterType="Optional",
#             direction="Input"
#         )
#         param_route_mp_from_parent.enabled = False
#
#         param_route_mp_to_parent = arcpy.Parameter(
#             displayName="Parent Milepost TO",
#             name="route_mp_to_parent",
#             datatype="GPDouble",
#             parameterType="Optional",
#             direction="Input"
#         )
#         param_route_mp_to_parent.enabled = False
#
#         param_route_change_form_id = arcpy.Parameter(
#             displayName="Route Change Form ID",
#             name="route_change_form_id",
#             datatype="GPString",
#             parameterType="Optional",
#             direction="Input"
#         )
#         param_route_change_form_id.enabled = False
#
#         params_RemilepostRoute = [
#             param_route_sri,
#
#             param_route_mp_from_current,
#             param_route_mp_to_current,
#
#             param_route_mp_from_new,
#             param_route_mp_to_new,
#
#             param_route_mp_from_parent,
#             param_route_mp_to_parent,
#
#             param_route_change_form_id
#         ]
#
#         return params_RemilepostRoute
#
#     def isLicensed(self):
#         """Set whether tool is licensed to execute."""
#         return True
#
#     def updateParameters(self, parameters):
#         """Modify the values and properties of parameters before internal
#         validation is performed.  This method is called whenever a parameter
#         has been changed."""
#
#         # when the sri has been updated, populate the milepost from and milepost to parameter inputs
#         # the milepost_from and/or milepost_to parameters will be updated by the user but are included for reference
#
#         if (not parameters[0].hasBeenValidated) or parameters[0].altered:
#
#             p_route_sri = parameters[0].value
#
#             mp_dropdown_data = arcpy.da.TableToNumPyArray(
#                 in_table=linreftab,
#                 field_names=[ "MILEPOST_FR", "MILEPOST_TO", "SEG_TYPE_ID" ],
#                 where_clause="SRI='" + p_route_sri + "' AND LRS_TYPE_ID IN (1)",
#             )
#
#             secondary = "S" in mp_dropdown_data[0][2]
#
#             # get a sorted set of From mileposts for dropdown
#             ary_from_current = [ round( f[ 0 ], 3 ) for f in mp_dropdown_data ]
#             set_from_current = sorted( set( ary_from_current ) )
#
#             # get a sorted set of To milesposts for dropdown
#             ary_to_current = [ round( f[ 1 ], 3 ) for f in mp_dropdown_data ]
#             set_to_current = sorted( set( ary_to_current ) )
#
#             with arcpy.da.SearchCursor(
#                 in_table=linreftab,
#                 field_names=[ "SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF" ],
#                 where_clause="LRS_TYPE_ID=1 and SRI='" + p_route_sri + "'",
#                 sql_clause=(None, "ORDER BY MILEPOST_FR")
#
#             ) as linrefCursor:
#
#                 count_linref = 0
#
#                 for linrefRow in linrefCursor:
#
#                     if count_linref == 0:
#
#                         distance_mp_from = float(linrefRow[2])
#                     else:
#
#                         distance_mp_to = float(linrefRow[3])
#
#                     count_linref += 1
#
#             parameters[ 1 ].enabled = True
#             parameters[ 1 ].filter.list = set_from_current
#             parameters[ 1 ].value = set_from_current[ 0 ]
#
#             # enable it after the first dropdown is selected
#             # parameters[2].enabled = True
#             parameters[ 2 ].filter.list = set_to_current
#             parameters[ 2 ].value = set_to_current[ len( set_to_current ) - 1 ]
#
#             parameters[ 3 ].enabled = True
#             parameters[ 4 ].enabled = True
#
#             if secondary:
#
#                 parameters[ 5 ].enabled = True
#                 parameters[ 6 ].enabled = True
#
#                 parameters[ 5 ].parameterType = "Required"
#                 parameters[ 6 ].parameterType = "Required"
#
#             parameters[7].enabled = True
#
#         if (not parameters[ 1 ].hasBeenValidated) or parameters[ 1 ].altered:
#
#             mp_from_selected = parameters[ 1 ].value
#
#             # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
#             # todo: filter to_milepost for values > from milepost selection
#
#             parameters[ 2 ].enabled = True
#
#         if (not parameters[ 2 ].hasBeenValidated) or parameters[ 2 ].altered:
#
#             mp_from_selected = parameters[ 2 ].value
#
#             arcpy.AddMessage( mp_from_selected )
#             # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
#             # todo: for val in parameters[2].filter.list:
#
#         if (not parameters[ 3 ].hasBeenValidated) or parameters[ 3 ].altered:
#
#             arcpy.AddMessage( mp_from_selected )
#
#             # update parameters 2 filter list to not allow selection of mileposts before or equal to FROM selection
#             # todo: for val in parameters[2].filter.list:
#
#         return
#
#     def updateMessages(self, parameters):
#         """Modify the messages created by internal validation for each tool
#         parameter.  This method is called after internal validation."""
#
#         import traceback
#
#         if parameters[0].value:
#
#             param_route_sri = parameters[0].value
#
#             if not arcpy.Exists(sldroutetab):
#
#                 parameters[0].setErrorMessage("Can not access the SLD ROUTE sde table.")
#
#             else:
#
#                 # is user provided SRI in the list
#                 try:
#
#                     with arcpy.da.SearchCursor(
#                         in_table=sldroutetab,
#                         field_names=["SRI"],
#                         where_clause="SRI='" + param_route_sri + "'"
#                     ) as c_segment:
#
#                         sri_is_valid = False
#
#                         for r_segment in c_segment:
#
#                             if r_segment[0] != '':
#                                 sri_is_valid = True
#
#                         if sri_is_valid:
#
#                             parameters[0].clearMessage()
#                             parameters[1].enabled = True
#
#                         else:
#
#                             parameters[0].setErrorMessage(parameters[0].value + ' is not a valid SRI')
#
#                             for x in range(1, 4):
#                                 parameters[x].enabled = False
#
#                 except Exception as ex:
#
#                     parameters[0].setErrorMessage("Error with Parameter Value 0: " + param_route_sri + " \n " + ex.message + " - " + traceback.format_exc())
#
#         try:
#
#             # verify new mile post start value
#             if parameters[1].value:
#
#                 param_route_mp_from_new = parameters[1].value
#
#                 if re.match("([0-9]+.?[0-9]{0,3})", str(param_route_mp_from_new)):
#
#                     parameters[1].clearMessage()
#
#                 else:
#                     parameters[1].setErrorMessage("Milepost FROM value must only contain two decimal places.")
#         except Exception as ex:
#
#             parameters[0].setErrorMessage("Error with Parameter Value 1: " + parameters[1].value + " \n " + ex.message + " - " + traceback.format_exc())
#
#         # verify new mile post end value
#         if parameters[2].value:
#
#             param_route_mp_to_new = parameters[2].value
#
#             if re.match("([0-9]+.?[0-9]{0,3})", str(param_route_mp_to_new)):
#
#                 parameters[2].clearMessage()
#             else:
#                 parameters[2].setErrorMessage("Milepost TO value must only contain two decimal places.")
#
#         # verify Route Change Form ID
#         if parameters[7].value:
#
#             param_route_change_form_id = parameters[7].value
#
#             if re.match("[0-9]+", str(param_route_change_form_id)):
#
#                 parameters[7].clearMessage()
#             else:
#                 parameters[7].setErrorMessage("RCF ID must be a numerical value.")
#
#         # todo: saved value will be appended to existing RCF ID for auditing purposes
#
#         return
#
#     def execute(self, parameters, messages):
#
#         global segmentfc
#
#         """The source code of the tool."""
#
#         # import arcpy
#         # import os
#         # import traceback
#
#         os.sys.path.append(os.path.dirname(__file__))
#
#         p_route_sri = parameters[ 0 ].value
#
#         p_route_mp_from_current = parameters[ 1 ].value
#         p_route_mp_to_current = parameters[ 2 ].value
#
#         p_route_mp_from_new = parameters[ 3 ].value
#         p_route_mp_to_new = parameters[ 4 ].value
#
#         p_route_mp_from_parent = parameters[ 5 ]
#         p_route_mp_to_parent = parameters[ 6 ]
#
#         p_route_change_form_id = parameters[ 7 ].value
#
#         #array position for easier reference
#         pos_sid = 0
#         pos_guid = 1
#         pos_mpfrom = 2
#         pos_mpto = 3
#         pos_rcf = 4
#
#         isRoute = False
#         isRamp = False
#
#         if len(p_route_sri) == 10:
#             isRoute = True
#         else:
#             isRamp = True
#
#         distance_total_mp = 0
#         distance_total_gis = 0
#
#         # for primary routes, we will take the New Milepost From/To
#         # for secondary routes, we'll take the Parent Milepost From/To
#         if primary_sri:
#             distance_mp_total = abs( float( p_route_mp_to_new ) - float( p_route_mp_from_new ) )
#             distance_mp_total_parent = abs( float( p_route_mp_to_new ) - float( p_route_mp_from_new ) )
#         else:
#             distance_mp_total = abs( float( p_route_mp_to_new ) - float( p_route_mp_to_new ) )
#             distance_mp_total_parent = abs( float( p_route_mp_to_parent ) - float( p_route_mp_from_parent ) )
#
#         # todo: add scaling factor for parent milepost from /to when necessary
#
#         list_segment_guids = []
#         list_segment_ids = []
#
#         print "Route SRI: " + p_route_sri
#         arcpy.AddMessage("Route SRI: " + p_route_sri)
#
#         # calculate current gis distance
#         try:
#
#             option1 = False
#             option2 = True
#
#             distances = []
#             total_calculated_distance = 0
#
#             where_clause_linRef = " LRS_TYPE_ID=1 " \
#                                   " AND SRI='" + p_route_sri + "' " \
#                                   " AND MILEPOST_FR >= " + str( p_route_mp_from_current ) + \
#                                   " AND MILEPOST_TO <= " + str(p_route_mp_to_current )
#
#             count_type = 0
#             segment_type = ""
#
#             if isRoute:
#
#                 with arcpy.da.SearchCursor(
#                     in_table=linreftab,
#                     field_names=["SEG_ID", "SEG_GUID", "SEG_TYPE_ID"],
#                     where_clause=where_clause_linRef,
#                     sql_clause=(None, "ORDER BY MILEPOST_FR")
#
#                 ) as distanceLinRefCursor:
#
#                     for distanceLinRefRow in distanceLinRefCursor:
#
#                         if count_type == 0:
#                             count_type += 1
#                             segment_type = distanceLinRefRow[2]
#
#                         with arcpy.da.SearchCursor(
#                             in_table=segmentfc,
#                             field_names=["SHAPE@LENGTH"],
#                             where_clause="SEG_GUID = '" + distanceLinRefRow[1] + "'"
#                         ) as distanceCursor:
#
#                             for distanceRow in distanceCursor:
#
#                                 total_calculated_distance += distanceRow[0]
#
#             elif isRamp:
#
#                 # this distance cursor based calculation is different when dealing with ramps.. gore to gore identified using L_Segment_Type
#                 # we will only measure where the L_SEGMENT_TYPE is Primary..
#                 # negative distances for acceleration and positive distances for deceleration will also have to be calculated
#
#                 ramp_where_clause = where_clause_linRef + ' AND SEG_TYPE_ID = "P" '
#
#                 count_primary_segments = 0
#
#                 with arcpy.da.SearchCursor(
#                         in_table=linreftab,
#                         field_names=[ "SEG_ID", "SEG_GUID" ],
#                         where_clause=ramp_where_clause,
#                         sql_clause=(None, "ORDER BY MILEPOST_FR")
#                 ) as distanceLinRefCursor:
#
#                     for distanceLinRefRow in distanceLinRefCursor:
#
#                         count_primary_segments += 1
#
#                         with arcpy.da.SearchCursor(
#                                 in_table=segmentfc,
#                                 field_names=[ "SHAPE@LENGTH" ],
#                                 where_clause=" SEG_GUID = '" + distanceLinRefRow[ 1 ] + "' "
#                         ) as distanceCursor:
#
#                             for distanceRow in distanceCursor:
#                                 total_calculated_distance += distanceRow[ 0 ]
#
#                 if count_primary_segments == 0:
#                     arcpy.AddError("This ramp does not contain a primary segment and should be corrected. \nAll pending updates have been canceled.")
#
#             arcpy.AddMessage("Total Calculated Distance from MP Start to MP End: " + str(total_calculated_distance))
#
#             # calculate the scaling factor
#             distance_conversion_factor =  distance_mp_total / ( total_calculated_distance / 5280)
#             distance_conversion_factor_parent = distance_mp_total_parent / ( total_calculated_distance / 5280)
#
#             arcpy.AddMessage( "distance_mp_total:" + str( distance_mp_total ) )
#             arcpy.AddMessage( "Distance Conversion Factor:" + str( distance_conversion_factor ) )
#
#             # generate a collection of segments that will be updated, sorting by milepost_from
#             # todo: what if MILEPOST_FR or MILEPOST_TO has a data error
#
#             with arcpy.da.SearchCursor(
#                 in_table=linreftab,
#                 field_names=["SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF"],
#                 # where_clause="LRS_TYPE_ID=1 and SRI='" + p_route_sri + "'",
#                 where_clause=where_clause_linRef,
#                 sql_clause=(None, "ORDER BY MILEPOST_FR")
#
#             ) as linrefCursor:
#
#                 count_linref = 0
#
#                 for linrefRow in linrefCursor:
#
#                     # list_segment_guids.append(linrefRow[pos_guid])
#                     # list_segment_ids.append(linrefRow[pos_sid])
#
#                     count_linref += 1
#                     count_segment = 0
#
#                     mp_segment_begin = distance_total_gis
#
#                     arcpy.AddMessage("linrefRow")
#                     arcpy.AddMessage(linrefRow)
#
#                     ref_guid = linrefRow[pos_guid]
#
#                     # create a segment cursor to update geometry M values
#                     segmentCursor = arcpy.UpdateCursor(
#                         segmentfc,
#                         "SEG_GUID = '" + ref_guid + "'",
#                         ["SHAPE@", "PRIME_NAME"]
#                     )
#
#                     # calculate updates for linref table values
#                     if count_linref == 1:
#                         pass
#                         # set from as user input
#
#                     for segmentRow in segmentCursor:
#
#                         vertex_previous_geometry = {}
#                         segVertexDistance = 0
#
#                         # get the segment geometry and then vertices collections
#                         segVerticesGeom = segmentRow.getValue( "SHAPE" )
#
#                         # get json representation and look for true curves
#                         j_seg = json.loads( segVerticesGeom.JSON )
#
#                         segVertices = []
#
#                         arcpy.AddMessage( j_seg )
#
#                         # test for true curve
#                         if "curvePaths" in j_seg:
#
#                             # curves exist, so we'll use the well known text of the geometry, which converts true curves to polylines with many segments
#                             # we will derive an x,y,m list from the wkt and add M values to all of the newly created segment parts
#                             seg_wkt = segVerticesGeom.WKT
#
#                             arcpy.AddMessage( "seg_wkt" )
#                             arcpy.AddMessage( seg_wkt )
#
#                             # grab only the stuff within
#                             wkt_points = seg_wkt[ seg_wkt.find( "((" ) + 2:seg_wkt.find( "))" ) ]
#
#                             segment_vertex_points = wkt_points.split( ", " )
#
#                             arcpy.AddMessage( "segment_vertex_points" )
#                             arcpy.AddMessage( segment_vertex_points )
#
#                             for point in segment_vertex_points:
#                                 segVertices.append(point.strip( ).split( " " ))
#
#                             # create arrays to hold the full segment geometry and the individual parts
#                             newSegmentGeom = arcpy.Array( )
#                             newSegmentPart = arcpy.Array( )
#
#                             arcpy.AddMessage( "segVertices" )
#                             arcpy.AddMessage( segVertices )
#
#                             for i in range( len( segVertices ) ):
#
#                                 # grab the current segment vertex
#                                 segVertex = segVertices[ i ]
#
#                                 arcpy.AddMessage( "segVertex" )
#                                 arcpy.AddMessage( segVertex )
#
#                                 # create a new point object, essentially copying the existing one
#                                 # we have to use index based access for segment parts
#                                 vertex_point = arcpy.Point( segVertex[0], segVertex[1], None, segVertex[2] )
#
#                                 # create a point geometry from the point object.. necessary for distance measurement
#                                 vertex_geom = arcpy.PointGeometry( vertex_point )
#
#                                 # measure distance from previous vertex to current vertex. first vertex is at aggregate distance
#                                 if i > 0:
#                                     segVertexDistance += (vertex_previous_geometry.distanceTo( vertex_geom ))
#
#                                 # set the current geometry as previous for next iteration
#                                 vertex_previous_geometry = vertex_geom
#
#                                 # set the point M value
#                                 # account for an aggregate of total route distance, convert to miles, round 3 decimal places
#                                 segVertex[2] = round( ((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor, 3 )
#
#                                 # create a new point for the updated vertex (could just recycle vertex_point..)
#                                 newSegmentVertex = arcpy.Point( segVertex[0], segVertex[1], None, segVertex[2] )
#
#                                 # add the segment vertex to the segment parts array
#                                 newSegmentPart.add( newSegmentVertex )
#
#                             # add the segment part to the point collection
#                             newSegmentGeom.add( newSegmentPart )
#
#                             # add the total segment distance to aggregate distance (at beginning of new segment)
#                             distance_total_gis += float( segVerticesGeom.length )
#
#                             arcpy.AddMessage( "Vertex M: " + str( distance_total_gis + (segVertexDistance / 5280) ) )
#                             arcpy.AddMessage( "Distance: " + str( segVertexDistance ) + "(" + str( segVertexDistance / 5280 ) + ")" )
#
#                             # create the new polyline object, ensure SR. Z and M must be set to be able to update M
#                             newSegment = arcpy.Polyline( newSegmentGeom, arcpy.SpatialReference( 3424 ), False, True )
#
#                             # update the row geometry with the new polyline
#                             segmentRow.setValue( "SHAPE", newSegment )
#
#                             # update the row
#                             segmentCursor.updateRow( segmentRow )
#
#                             count_segment += 1
#
#                         else:
#                             # pull the geometry from the shape representation
#                             segVertices = segVerticesGeom.getPart( 0 )
#
#                             # create arrays to hold the full segment geometry and the individual parts
#                             newSegmentGeom = arcpy.Array( )
#                             newSegmentPart = arcpy.Array( )
#
#                             arcpy.AddMessage( "segVertices" )
#                             arcpy.AddMessage( segVertices )
#
#                             for i in range( len( segVertices ) ):
#
#                                 # grab the current segment vertex
#                                 segVertex = segVertices[ i ]
#
#                                 arcpy.AddMessage( "segVertex" )
#                                 arcpy.AddMessage( segVertex )
#
#                                 # create a new point object, essentially copying the existing one
#                                 vertex_point = arcpy.Point( segVertex.X, segVertex.Y, None, segVertex.M )
#
#                                 # create a point geometry from the point object.. necessary for distance measurement
#                                 vertex_geom = arcpy.PointGeometry( vertex_point )
#
#                                 # measure distance from previous vertex to current vertex. first vertex is at aggregate distance
#                                 if i > 0:
#                                     segVertexDistance += (vertex_previous_geometry.distanceTo( vertex_geom ))
#
#                                 # set the current geometry as previous for next iteration
#                                 vertex_previous_geometry = vertex_geom
#
#                                 # set the point M value
#                                 # account for an aggregate of total route distance, convert to miles, round 3 decimal places
#                                 segVertex.M = round( ((distance_total_gis + segVertexDistance) / 5280) * distance_conversion_factor, 3 )
#
#                                 # create a new point for the updated vertex (could just recycle vertex_point..)
#                                 newSegmentVertex = arcpy.Point( segVertex.X, segVertex.Y, None, segVertex.M )
#
#                                 # add the segment vertex to the segment parts array
#                                 newSegmentPart.add( newSegmentVertex )
#
#                             # add the segment part to the point collection
#                             newSegmentGeom.add( newSegmentPart )
#
#                             # add the total segment distance to aggregate distance (at beginning of new segment)
#                             distance_total_gis += float( segVerticesGeom.length )
#
#                             arcpy.AddMessage( "Vertex M: " + str( distance_total_gis + (segVertexDistance / 5280) ) )
#                             arcpy.AddMessage( "Distance: " + str( segVertexDistance ) + "(" + str( segVertexDistance / 5280 ) + ")" )
#
#                             # create the new polyline object, ensure SR. Z and M must be set to be able to update M
#                             newSegment = arcpy.Polyline( newSegmentGeom, arcpy.SpatialReference( 3424 ), False, True )
#
#                             # update the row geometry with the new polyline
#                             segmentRow.setValue( "SHAPE", newSegment )
#
#                             # update the row
#                             segmentCursor.updateRow( segmentRow )
#
#                             count_segment += 1
#                     #
#                     # LINEAR_REF Table Updates, segment by segment.
#                     #
#
#                     #segment milepost FROM new
#                     #segment milepost TO NEW
#
#                     # update the MILEPOST_FROM value in the linref table
#                     linRefUpdate_mp_from = round(mp_segment_begin / 5280, 3)
#                     linRefUpdate_mp_to = round(distance_total_gis / 5280, 3)
#                     linRefUpdate_rfc_id = (str(linrefRow[pos_rcf] or '') + " " + str(p_route_change_form_id)).strip()
#
#                     lrUpdateFields = [ "SEG_ID", "SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "RCF", "LRS_TYPE_ID", "SEG_TYPE_ID" ]
#
#                     # used for lookups when reference related types.. Parent Mileposts, for example
#                     # npa = arcpy.da.TableToNumPyArray(
#                     #     in_table='NJOIT_CENTERLINE.DBO.LINEAR_REF',
#                     #     field_names=lrUpdateFields,
#                     #     where_clause="SEG_GUID='" + ref_guid + "' AND LRS_TYPE_ID IN (1,2,3)"
#                     # )
#
#                     with arcpy.da.UpdateCursor(
#                             in_table=linreftab,
#                             field_names=lrUpdateFields,
#                             where_clause="SEG_GUID='" + ref_guid + "' AND LRS_TYPE_ID IN (1,2,3)"
#                     ) as linrefUpdateCursor:
#
#                         for linrefUpdateRecord in linrefUpdateCursor:
#
#                             # what type of lin ref record are we updated.. we'll use LRS_TYPE_ID to differentiate
#
#                             typeLRS = linrefUpdateRecord[ 5 ]
#                             typeSeg = linrefUpdateRecord[ 6 ]
#
#                             # PRIMARY SEGMENT
#                             if typeSeg in [ "P", "E" ]:
#
#                                 if typeLRS in [ 1, 3 ]:
#                                     # scaled M values
#                                     linrefUpdateRecord[ 2 ] = linRefUpdate_mp_from
#                                     linrefUpdateRecord[ 3 ] = linRefUpdate_mp_to
#
#                                 elif typeLRS == 2:
#                                     # flipped scaled m-values
#                                     linrefUpdateRecord[ 2 ] = linRefUpdate_mp_to
#                                     linrefUpdateRecord[ 3 ] = linRefUpdate_mp_from
#
#                             # SECONDARY SEGMENT
#                             elif typeSeg in [ "S", "ES" ]:
#
#                                 if typeLRS in [ 1, 3 ]:
#                                     # scaled M values
#                                     linrefUpdateRecord[ 2 ] = linRefUpdate_mp_from
#                                     linrefUpdateRecord[ 3 ] = linRefUpdate_mp_to
#
#                                 elif typeLRS == 2:
#                                     # flipped scaled m-values
#                                     linrefUpdateRecord[ 2 ] = linRefUpdate_parent_mp_from
#                                     linrefUpdateRecord[ 3 ] = linRefUpdate_parent_mp_to
#
#                             elif typeSeg == "AD":
#
#                                 # additional logic is needed for AD since we'll be calculating
#                                 # a negative distance for each geometry for acceleration segments and a positive distance for deceleration
#                                 # gore to gore will likely be an entirely new geometric calculation and lin ref updates.
#
#                                 pass
#
#                     # update the row
#                     # linrefCursor.updateRow(linrefRow)
#
#                     del segmentRow
#                     del segmentCursor
#
#             # del linrefCursor, linrefRow
#
#         except arcpy.ExecuteError:
#
#             arcpy.AddError(arcpy.GetMessages(2))
#
#         except Exception as ex:
#
#             arcpy.AddError(traceback.format_exc())
#
#             e = sys.exc_info()[1]
#             arcpy.AddMessage("Exception updating segment geometry: " + ex.message + "  ------- \n " + e.args[0])
#
#         arcpy.AddMessage("Aggregate Distance by Geometry: " + str(distance_total_gis) + " feet.  " + str(distance_total_gis / 5280) + " miles.")
#         arcpy.AddMessage("Milepost Distance: " + str(distance_mp_total) + " miles.")
#
#         return

