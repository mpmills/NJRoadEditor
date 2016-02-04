#-------------------------------------------------------------------------------
# Name:         erebus
# Purpose:      module for NJRoadEditor python add-in
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

def calcGUID():
    """Create a GUID."""
    import uuid
    return '{' + str(uuid.uuid4()).upper() + '}'

def timestamp():
    """Get a timestamp"""
    import datetime
    return datetime.datetime.now()

def sqlGUID(field, guid):
    """Create a SQL query for a GUID for entry into a arcpy cursor."""
    sqlquery = "%s = '%s'" % (field, guid)
    return sqlquery

def sqlcursor(field, value):
    """Create a SQL query for a field for an arcpy cursor."""
    sqlquery = "%s = '%s'" % (field, value)
    return sqlquery

class FullName(object):
    """Build a full name from seven parts with no abbreviations."""
    #predir=None, pretype=None, premod=None, name, suftype=None, sufdir=None, sufmod=None
    #self, predir, pretype, premod, name, suftype, sufdir, sufmod
    def __init__(self, predir=None, pretype=None, premod=None, name=None, suftype=None, sufdir=None, sufmod=None):
        self.predir = predir
        self.pretype = pretype
        self.premod = premod
        self.name = name
        self.suftype = suftype
        self.sufdir = sufdir
        self.sufmod = sufmod
        self.namelist = [predir, pretype, premod, name, suftype, sufdir, sufmod]
        # {'name': 'sufmod': 'premod': 'pretype': 'suftype': 'sufdir': 'predir':}
    def concatenate(self):
        #print self.namelist #['predir', None, None, 'hey you', None, None, None]
        import re
        # break it into pieces (this handles fields with mulitple names)
        namelist2 = []
        for nm in self.namelist:
            if nm:
                n1 = nm.split()
                for n in n1:
                    namelist2.append(n)

        catind = 0
        for name in namelist2:
            if name:
                if catind == 0:
                    #nc = name.capitalize()
                    #nc = re.sub(name[0],name[0].upper(),name)
                    for bb in ['~','!','@','#','$','%','^','&','*','(',')','+','=','[',']','{','}',':',';','"','<','>',',','.','/','?','`']:
                        name = name.replace(bb,"")
                    name = name.strip(" ")
                    name = name.replace("'", "")
                    nc3 = name.replace("-", " ")
                    #nc2 = name.strip(' ""~!@#$%^&*()_+=-[{]},;:<>?/ ')
                    #nc2 = name.strip(" ").replace()
                    #nc3 = nc2.replace("'", "")
                    namecat = nc3
                    catind += 1
                else:
                    for bb in ['~','!','@','#','$','%','^','&','*','(',')','+','=','[',']','{','}',':',';','"','<','>',',','.','/','?','`']:
                        name = name.replace(bb,"")
                    name = name.strip(" ")
                    name = name.replace("'", "")
                    nc3 = name.replace("-", " ")
                    #nc2 = name.strip(' ""~!@#$%^&*()_+=-[{]},;:<>?/ ')
                    #nc3 = nc2.replace("'", "")
                    namecat = namecat + " " + nc3
                    catind += 1

        try:
            return namecat
        except:
            return None

class FullNameNumpy(object):
    """Build a full name from seven parts with no abbreviations."""
    #predir=None, pretype=None, premod=None, name, suftype=None, sufdir=None, sufmod=None
    #self, predir, pretype, premod, name, suftype, sufdir, sufmod
    def __init__(self, predir=None, pretype=None, premod=None, name=None, suftype=None, sufdir=None, sufmod=None):
        self.predir = predir
        self.pretype = pretype
        self.premod = premod
        self.name = name
        self.suftype = suftype
        self.sufdir = sufdir
        self.sufmod = sufmod
        self.namelist = [predir, pretype, premod, name, suftype, sufdir, sufmod]
        # {'name': 'sufmod': 'premod': 'pretype': 'suftype': 'sufdir': 'predir':}
    def concatenate(self):
        #print self.namelist #['predir', None, None, 'hey you', None, None, None]

        # break it into pieces (this handles fields with mulitple names)
        namelist2 = []
        for nm in self.namelist:
            if nm != 'None':
                n1 = nm.split()
                for n in n1:
                    namelist2.append(n)

        catind = 0
        for name in namelist2:
            if name != 'None':
                if catind == 0:
                    nc = name.capitalize()
                    nc2 = nc.strip(' ""~!@#$%^&*()_+=-[{]},;:<>?/ ')
                    nc3 = nc2.replace("'", "")
                    namecat = nc3
                    catind += 1
                else:
                    nc = name.capitalize()
                    nc2 = nc.strip(' ""~!@#$%^&*()_+=-[{]},;:<>?/ ')
                    nc3 = nc2.replace("'", "")
                    namecat = namecat + " " + nc3
                    catind += 1

        return namecat



def getlongname(workspace, featureclass, gettype):
     ## 1 Get the current names, format and make a pretty message box
    import arcpy, os
    #import socket
    #ip = socket.gethostbyname(socket.gethostname())

    workspace_type = workspace.split(".")[-1]

    if workspace_type == "sde":

        if featureclass.split(".")[-1] == "SEGMENT":
            if len(featureclass.split(".")) == 3:
                fulls = [os.path.join(workspace, '.'.join(featureclass.split(".")[0:2]) + ".Centerline", featureclass)]  #"\\" + featureclass.split(".")[0] + ".Centerline" + "\\" + featureclass
            if len(featureclass.split(".")) == 2:
                fulls = [os.path.join(workspace, featureclass.split(".")[0] + ".Centerline", featureclass)]
        else:
            fulls = [os.path.join(workspace, featureclass)]

        try:
            mxd = arcpy.mapping.MapDocument("CURRENT")

            if gettype == "Layer":
                lyrs = arcpy.mapping.ListLayers(mxd)
                for lyr in lyrs:
                    if lyr.isFeatureLayer:
                        for full in fulls:
                            if lyr.dataSource == full:  # lyr.dataSource would equal "Database Connections\ROAD@gis7t@1525.sde\ROAD.Centerline\ROAD.SEGMENT"
                                longname = lyr.longName # this would be "ROAD.SEGMENT"

            if gettype == "Table":
                tbls = arcpy.mapping.ListTableViews(mxd)
                for tbl in tbls:
                    for full in fulls:
                        if tbl.dataSource == full:
                            longname = tbl.name

            print 'DataSources to edit: {0}'.format(fulls)
            return longname

        except Exception, e:
            print e
            return None

    if workspace_type == 'gdb':
        if featureclass.split(".")[-1] == "SEGMENT":
            fulls = [os.path.join(workspace, "Centerline", featureclass)]
        else:
            fulls = [os.path.join(workspace, featureclass)]

        try:
            mxd = arcpy.mapping.MapDocument("CURRENT")

            if gettype == "Layer":
                lyrs = arcpy.mapping.ListLayers(mxd)
                for lyr in lyrs:
                    if lyr.isFeatureLayer:
                        for full in fulls:
                            if lyr.dataSource == full:  # lyr.dataSource would equal "Database Connections\ROAD@gis7t@1525.sde\ROAD.Centerline\ROAD.SEGMENT"
                                longname = lyr.longName # this would be "ROAD.SEGMENT"

            if gettype == "Table":
                tbls = arcpy.mapping.ListTableViews(mxd)
                for tbl in tbls:
                    for full in fulls:
                        if tbl.dataSource == full:
                            longname = tbl.name

            print 'DataSources to edit: {0}'.format(fulls)
            return longname

        except Exception, e:
            print e
            return None


def delete(seg_guid, table, globalid = False):
    """"Delete row(s) is a table in the NJ Road Centerline Database"""
    import arcpy, traceback
    try:
        delete_result = {'result': 'na', 'SEG_GUID': seg_guid, 'table': table}
        if globalid:
            sqlquery = sqlGUID("GLOBALID", seg_guid)
        else:
            sqlquery = sqlGUID("SEG_GUID", seg_guid)
        sci = False

        counter = 0
        cursor = arcpy.UpdateCursor(table, sqlquery)
        for row in cursor:
            sci = True
            cursor.deleteRow(row)
            counter += 1

        if sci == True:
            delete_result['result'] = 'success'
            delete_result['deletes'] = counter
            return delete_result

        else:
            delete_result['result'] = 'no matches'
            delete_result['sql'] = sqlquery
            return delete_result
    except:
        trace = traceback.format_exc()
        try: row; del row
        except: pass
        try: cursor; del cursor
        except: pass
        delete_result['result'] = 'fail'
        delete_result['trace'] = trace
        return delete_result

def segment_trans(oldguid, newguid, table, seg_id_arch):
    import arcpy
    import traceback
    try:
        segname_result = {'result': 'na', 'SEG_GUID0': oldguid, 'SEG_GUIDnew': newguid}
        cursor = arcpy.InsertCursor(table)
        row = cursor.newRow()
        row.setValue('SEG_GUID_ARCH', oldguid)
        row.setValue('SEG_GUID_NEW', newguid)
        row.setValue('SEG_ID_ARCH', seg_id_arch)
        cursor.insertRow(row)
        del cursor, row
        segname_result['result'] = 'success'
        return segname_result
    except:
        trace = traceback.format_exc()
        try: row; del row
        except: pass
        try: cursor; del cursor
        except: pass
        segname_result['result'] = 'fail'
        segname_result['trace'] = trace
        return segname_result


class SegmentChange(object):
    def __init__(self, seg_guid_arch, table):
        self.seg_guid_arch = seg_guid_arch
        self.table = table
    def insert(self, segmentgeo, change_type_id = 'R', comments = None, seg_id_arch = None):
        """"Insert a new record into SEGMENT_CHANGE. This copies/appends from SEGMENT, the updates the record based on user input"""
        try:
            #print 'segmentgeo.WKT {0}'.format(segmentgeo.WKT)
            import arcpy, traceback
            segname_result = {'result': 'na', 'SEG_GUID_ARCH': self.seg_guid_arch}
            segname_result['method'] = 'None'
            breaker = False
            try:
                cursor =  arcpy.da.InsertCursor(self.table, ["SEG_ID_ARCH", "SEG_GUID_ARCH", "CHANGE_TYPE_ID", "COMMENTS", "SHAPE@"])
                row = [seg_id_arch, self.seg_guid_arch, change_type_id, comments, segmentgeo]
                cursor.insertRow(row)
                del cursor, row
                segname_result['result'] = 'success'
                segname_result['method'] = 'SHAPE@'
                return segname_result
                breaker = True
            except:
                pass
            if not breaker:
                try:
                    cursor =  arcpy.da.InsertCursor(self.table, ["SEG_ID_ARCH", "SEG_GUID_ARCH", "CHANGE_TYPE_ID", "COMMENTS", "SHAPE@WKT"])
                    row = [seg_id_arch, self.seg_guid_arch, change_type_id, comments, segmentgeo.WKT]
                    cursor.insertRow(row)
                    del cursor, row
                    segname_result['result'] = 'success'
                    segname_result['method'] = '@WKT'
                    return segname_result
                    breaker = True
                except:
                    pass
            if not breaker:
                try:
                    cursor =  arcpy.da.InsertCursor(self.table, ["SEG_ID_ARCH", "SEG_GUID_ARCH", "CHANGE_TYPE_ID", "COMMENTS", "SHAPE@JSON"])
                    row = [seg_id_arch, self.seg_guid_arch, change_type_id, comments, segmentgeo]
                    cursor.insertRow(row)
                    del cursor, row
                    segname_result['result'] = 'success'
                    segname_result['method'] = '@JSON'
                    return segname_result
                    breaker = True
                except:
                    pass

        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segname_result['result'] = 'fail'
            segname_result['trace'] = trace
            return segname_result

class UpdateCopy(object):
    def __init__(self, original_guid, guid1, guid2):
        self.original_guid = original_guid
        self.guid1 = guid1
        self.guid2 = guid2
    def segname(self, table):
        """"Update and Copy records in SEG_NAME"""
        try:
            import arcpy, traceback

            # Build the response dictionary
            segname_result = {'result': 'na', 'SEG_GUID0': self.original_guid, 'SEG_GUID1': self.guid1, 'SEG_GUID2': self.guid2}

            sqlquery = sqlGUID("SEG_GUID", self.original_guid)

            # get what is there and make a tuple
            rowsexist = False
            orginalrows = []
            with arcpy.da.SearchCursor(table, "*", sqlquery) as cursor:
                for row in cursor:
                    rowsexist = True
                    orginalrows.append(row)

            if rowsexist:

                # update existing rows
                cursor = arcpy.UpdateCursor(table, sqlquery)
                for row in cursor:
                    row.setValue('SEG_GUID', self.guid1)
                    cursor.updateRow(row)
                del row, cursor
##                with arcpy.da.UpdateCursor(table, ["SEG_GUID"], sqlquery) as cursor:
##                    for row in cursor:
##                        row[0] = self.guid1
##                        cursor.updateRow(row)

                # make some new rows, this will be a list of lists
                newrows = []
                for r in orginalrows:
                    nr = list(r)
                    nr[2]  = self.guid2
                    newrows.append(nr)

                #insert

                cursor = arcpy.InsertCursor(table)
                for rr in newrows:
                    row = cursor.newRow()
                    row.setValue('SEG_ID', rr[1])
                    row.setValue('SEG_GUID', rr[2])
                    row.setValue('NAME_TYPE_ID', rr[3])
                    row.setValue('RANK', rr[4])
                    row.setValue('NAME_FULL', rr[5])
                    row.setValue('PRE_DIR', rr[6])
                    row.setValue('PRE_TYPE', rr[7])
                    row.setValue('PRE_MOD', rr[8])
                    row.setValue('NAME', rr[9])
                    row.setValue('SUF_TYPE', rr[10])
                    row.setValue('SUF_DIR', rr[11])
                    row.setValue('SUF_MOD', rr[12])
                    row.setValue('DATA_SRC_TYPE_ID', rr[13])
                    cursor.insertRow(row)
                del row
                del cursor

##                cursor =  arcpy.da.InsertCursor(table, ["SEG_ID", "SEG_GUID", "NAME_TYPE_ID", "RANK", "NAME_FULL", "PRE_DIR", "PRE_TYPE", "PRE_MOD", "NAME", "SUF_TYPE", "SUF_DIR", "SUF_MOD", "DATA_SRC_TYPE_ID"])
##                for rr in newrows:
##                    row = [rr[1], rr[2], rr[3], rr[4], rr[5], rr[6], rr[7], rr[8], rr[9], rr[10], rr[11], rr[12], rr[13]]
##                    cursor.insertRow(row)
##                del cursor, row

                segname_result['result'] = 'success'
                segname_result['updates'] = len(orginalrows)
                segname_result['copies'] = len(newrows)
                return segname_result

            else:
                segname_result['result'] = 'no matching records'
                return segname_result
        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segname_result['result'] = 'fail'
            segname_result['trace'] = trace
            return segname_result

    def segshield(self, table):
        """"Update and Copy records in SEG_SHIELD"""
        try:
            import arcpy, traceback
            segname_result = {'result': 'na', 'SEG_GUID0': self.original_guid, 'SEG_GUID1': self.guid1, 'SEG_GUID2': self.guid2}

            sqlquery = sqlGUID("SEG_GUID", self.original_guid)

            # get what is there and make a tuple
            rowsexist = False
            orginalrows = []
            with arcpy.da.SearchCursor(table, "*", sqlquery) as cursor:
                for row in cursor:
                    rowsexist = True
                    orginalrows.append(row)

            if rowsexist:
                # update existing rows

                cursor = arcpy.UpdateCursor(table, sqlquery)
                for row in cursor:
                    row.setValue('SEG_GUID', self.guid1)
                    cursor.updateRow(row)
                del row, cursor


                # make some new rows, this will be a list of lists
                newrows = []
                for r in orginalrows:
                    nr = list(r)
                    nr[2]  = self.guid2
                    newrows.append(nr)

                cursor = arcpy.InsertCursor(table)
                for rr in newrows:
                    row = cursor.newRow()
                    row.setValue('SEG_ID', rr[1])
                    row.setValue('SEG_GUID', rr[2])
                    row.setValue('RANK', rr[3])
                    row.setValue('SHIELD_TYPE_ID', rr[4])
                    row.setValue('SHIELD_SUBTYPE_ID', rr[5])
                    row.setValue('SHIELD_NAME', rr[6])
                    row.setValue('DATA_SRC_TYPE_ID', rr[7])
                    cursor.insertRow(row)
                del row
                del cursor



                #insert
##                cursor =  arcpy.da.InsertCursor(table, ["SEG_ID", "SEG_GUID", "RANK", "SHIELD_TYPE_ID", "SHIELD_SUBTYPE_ID", "SHIELD_NAME", "DATA_SRC_TYPE_ID"])
##                for rr in newrows:
##                    row = [rr[1], rr[2], rr[3], rr[4], rr[5], rr[6], rr[7]]
##                    cursor.insertRow(row)
##                del cursor, row
                segname_result['result'] = 'success'
                segname_result['updates'] = len(orginalrows)
                segname_result['copies'] = len(newrows)
                return segname_result
            else:
                segname_result['result'] = 'no matching records'
                return segname_result

        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segname_result['result'] = 'fail'
            segname_result['trace'] = trace
            return segname_result

    def linearref(self, table, ge1, ge2, interp = True):
        """"Update and Copy records in LINEAR_REF (if records exist)
        table - the layer name for the LINEAR_REF table
        ge1 - geometry of the first of the newly split features (JSON)
        ge2 - geometry of the second of the newly split features (JSON)
        iterp - whether or not to interpolate the addresses."""
        try:
            import arcpy, traceback
            segname_result = {'result': 'na', 'SEG_GUID0': self.original_guid, 'SEG_GUID1': self.guid1, 'SEG_GUID2': self.guid2, 'sri': ''}
            sqlquery = sqlGUID("SEG_GUID", self.original_guid)

            #check for true curves in the JSON
            if 'curvePaths' in ge1.keys():
                # format for true curves
                xym1 = []
                for i in ge1['curvePaths'][0]:
                    if type(i) is list:
                        xym1.append(i)
                    elif type(i) is dict:
                        xym1.append(i['c'][0])
            elif 'paths' in ge1.keys():
                #format for no true curves
                # find the matching vertices
                xym1 = ge1['paths'][0] # list of lists. each list has [x,y,m]

            if 'curvePaths' in ge2.keys():
                # format for true curves
                xym2 = []
                for i in ge2['curvePaths'][0]:
                    if type(i) is list:
                        xym2.append(i)
                    elif type(i) is dict:
                        xym2.append(i['c'][0])
            elif 'paths' in ge2.keys():
                #format for no true curves
                # find the matching vertices
                xym2 = ge2['paths'][0]


            # get what is there and make a tuple
            rowsexist = False
            orginalrows = []
            with arcpy.da.SearchCursor(table, "*", sqlquery) as cursor:
                for row in cursor:
                    rowsexist = True
                    orginalrows.append(row)

            if rowsexist:
                # update existing rows
                if interp == True: # if interpolation of Milepost values is true

                    keeptrack=[[],[],[],[]]

                    cursor = arcpy.UpdateCursor(table, sqlquery)
                    for row in cursor:
                        row.setValue('SEG_GUID',self.guid1)

                        # choose the right LRS values to change
                        lastge1vert = len(xym1) - 1
                        startv = round(xym1[0][2], 8)
                        endv = round(xym1[lastge1vert][2], 8)
                        mp_from = round(row.getValue('MILEPOST_FR'), 8)
                        mp_to = round(row.getValue('MILEPOST_TO'), 8)

                        # if FROM == first or last
                        if mp_from == startv:
                            # dont update from
                            if mp_to != startv and mp_to != endv:
                                # it must be endv
                                row.setValue('MILEPOST_TO', endv)
                        elif mp_from  == endv:
                            # dont update from
                            if mp_to != startv and mp_to != endv:
                                # it must be start
                                row.setValue('MILEPOST_TO', startv)
                        elif mp_to == startv:
                            # dont update to
                            if mp_from != startv and mp_from != endv:
                                # it must be endv
                                row.setValue('MILEPOST_FR', endv)
                        elif mp_to  == endv:
                            # dont update to
                            if mp_from != startv and mp_from != endv:
                                # it must be start
                                row.setValue('MILEPOST_FR', startv)

                        cursor.updateRow(row)
                        keeptrack[0].append(startv); keeptrack[1].append(endv); keeptrack[2].append(mp_from); keeptrack[3].append(mp_to)
                    segname_result['keeptrack1'] = keeptrack
                    try: del row
                    except: pass
                    try: del cursor
                    except: pass

                if interp == False:

                    cursor = arcpy.UpdateCursor(table, sqlquery)
                    for row in cursor:
                        row.setValue('SEG_GUID',self.guid1)
                        cursor.updateRow(row)

                    try: del row
                    except: pass
                    try: del cursor
                    except: pass

                # make some new rows, this will be a list of lists
                newrows = []
                for r in orginalrows:
                    nr = list(r)
                    nr[2] = self.guid2
                    newrows.append(nr)

                #insert
                if interp == True:

                    keeptrack=[[],[],[],[]]

                    cursor =  arcpy.InsertCursor(table)
                    for rr in newrows:
                        row = cursor.newRow()
                        # choose the right LRS values to change
                        lastge1vert = len(xym2) - 1
                        startv = round(xym2[0][2], 8)
                        endv = round(xym2[lastge1vert][2], 8)
                        mp_from = round(rr[6], 8)
                        mp_to = round(rr[7], 8)

                        row.setValue('SEG_ID', rr[1])
                        row.setValue('SEG_GUID', rr[2])
                        row.setValue('SRI', rr[3])
                        row.setValue('LRS_TYPE_ID', rr[4])
                        row.setValue('SEG_TYPE_ID', rr[5])

                        # set them up, 1 will be changed !!!
                        row.setValue('MILEPOST_FR', rr[6])
                        row.setValue('MILEPOST_TO', rr[7])

                        row.setValue('RCF', rr[8])
                        # if FROM == first or last
                        if mp_from == startv:
                            # dont update from
                            if mp_to != startv and mp_to != endv:
                                # it must be endv
                                row.setValue('MILEPOST_TO', endv)
                        elif mp_from  == endv:
                            # dont update from
                            if mp_to != startv and mp_to != endv:
                                # it must be start
                                row.setValue('MILEPOST_TO', startv)
                        elif mp_to == startv:
                            # dont update to
                            if mp_from != startv and mp_from != endv:
                                # it must be endv
                                row.setValue('MILEPOST_FR', endv)
                        elif mp_to  == endv:
                            # dont update to
                            if mp_from != startv and mp_from != endv:
                                # it must be start
                                row.setValue('MILEPOST_FR', startv)
                        cursor.insertRow(row)
                        keeptrack[0].append(startv); keeptrack[1].append(endv); keeptrack[2].append(mp_from); keeptrack[3].append(mp_to)
                    segname_result['keeptrack2'] = keeptrack
                    del cursor, row

                if interp == False:

                    cursor =  arcpy.InsertCursor(table)
                    for rr in newrows:
                        row = cursor.newRow()
                        row.setValue('SEG_ID', rr[1])
                        row.setValue('SEG_GUID', rr[2])
                        row.setValue('SRI', rr[3])
                        row.setValue('LRS_TYPE_ID', rr[4])
                        row.setValue('SEG_TYPE_ID', rr[5])
                        row.setValue('MILEPOST_FR', rr[6])
                        row.setValue('MILEPOST_TO', rr[7])
                        row.setValue('RCF', rr[8])
                        cursor.insertRow(row)
                    del cursor, row

                segname_result['result'] = 'success'
                segname_result['updates'] = len(orginalrows)
                segname_result['copies'] = len(newrows)

                # Check for an SRI
                if orginalrows[0][3]:
                    segname_result['sri'] = orginalrows[0][3]
                return segname_result
            else:
                segname_result['result'] = 'no matching records'
                return segname_result

        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segname_result['result'] = 'fail'
            segname_result['trace'] = trace
            return segname_result

class Geocode(object):
    def __init__(self, url):
        self.url = url
    def reverse_geocode(self, x, y, f = 'pjson', distance = 10):
        r_geo_result = {'result': 'na'}
        try:
            import json, urllib2, urllib

            URL = self.url + '/reverseGeocode'
            loc = str(x) + ',' + str(y)

            #jsonrequest = {'location': loc, 'distance': distance, 'f': f}
            jsonrequest = {'location': loc, 'f': f}
            data_encoded = urllib.urlencode(jsonrequest)

            opener = urllib2.build_opener()

            result = opener.open(URL, data_encoded)
            loads2 = result.read()
            loads = json.loads(loads2) # this is the dictionary
            r_geo_result['json'] = loads
            if loads['location']:
                r_geo_result['json'] = loads
                r_geo_result['address'] = loads['address']
                r_geo_result['location'] = loads['location']
                street = loads['address']['Street']
                r_geo_result['address number'] = street.split()[0]
                r_geo_result['result'] = 'success'
                return r_geo_result
            if loads['error']:
                r_geo_result['json'] = loads
                r_geo_result['result'] = 'fail'
                return r_geo_result

        except:
            r_geo_result['result'] = 'fail'
            trace = traceback.format_exc()
            segname_result['trace'] = trace
            return r_geo_result
        finally:
            return r_geo_result

class UpdateGuid(object):
    def __init__(self, seg_guid, new_seg_guid):
        self.seg_guid = seg_guid
        self.new_seg_guid = new_seg_guid
    def segname(self, table):
        """"Update records in SEG_NAME"""
        try:
            import arcpy, traceback

            # Build the response dictionary
            segname_result = {'result': 'na', 'SEG_GUID1': self.seg_guid, 'SEG_GUID2': self.new_seg_guid}

            sqlquery = sqlGUID("SEG_GUID", self.seg_guid)

            # get what is there and make a tuple
            rowsexist = False
            orginalrows = []
            with arcpy.da.SearchCursor(table, "*", sqlquery) as cursor:
                for row in cursor:
                    rowsexist = True
                    orginalrows.append(row)

            if rowsexist:
                # update existing rows
                cursor = arcpy.UpdateCursor(table, sqlquery)
                for row in cursor:
                    row.setValue('SEG_GUID', self.new_seg_guid)
                    cursor.updateRow(row)

                try: del row
                except: pass
                try: del cursor
                except: pass

                segname_result['result'] = 'success'
                segname_result['updates'] = len(orginalrows)
                return segname_result
            else:
                segname_result['result'] = 'no matching records'
                return segname_result

        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segname_result['result'] = 'fail'
            segname_result['trace'] = trace
            return segname_result

    def segshield(self, table):
        """"Update records in SEG_SHIELD"""
        try:
            import arcpy, traceback
            segshield_result = {'result': 'na', 'SEG_GUID1': self.seg_guid, 'SEG_GUID2': self.new_seg_guid}

            sqlquery = sqlGUID("SEG_GUID", self.seg_guid)

            # get what is there and make a tuple
            rowsexist = False
            orginalrows = []
            with arcpy.da.SearchCursor(table, "*", sqlquery) as cursor:
                for row in cursor:
                    rowsexist = True
                    orginalrows.append(row)

            if rowsexist:
                # update existing rows
                cursor = arcpy.UpdateCursor(table, sqlquery)
                for row in cursor:
                    row.setValue('SEG_GUID', self.new_seg_guid)
                    cursor.updateRow(row)

                try: del row
                except: pass
                try: del cursor
                except: pass

                segshield_result['result'] = 'success'
                segshield_result['updates'] = len(orginalrows)

                return segshield_result
            else:
                segshield_result['result'] = 'no matching records'
                return segshield_result

        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segshield_result['result'] = 'fail'
            segshield_result['trace'] = trace
            return segshield_result

    def linearref(self, table, geojson, interp = True):
        """"Update records in LINEAR_REF (if records exist)"""
        try:
            import arcpy, traceback
            segname_result = {'result': 'na', 'SEG_GUID1': self.seg_guid, 'SEG_GUID2': self.new_seg_guid}
            sqlquery = sqlGUID("SEG_GUID", self.seg_guid)
            segname_result['sqlquery'] = sqlquery
            # get what is there and make a tuple
            rowsexist = False
            orginalrows = []
            with arcpy.da.SearchCursor(table, "*", sqlquery) as cursor:
                for row in cursor:
                    rowsexist = True
                    orginalrows.append(row)




            segname_result['orginalrows'] = orginalrows

            if rowsexist:
                segname_result['rowsexist'] = rowsexist
                # update existing rows
                if interp == True: # if interpolation of Milepost values is true
                    segname_result['interp'] = interp
                    keeptrack=[[],[],[],[]]

                    i = 0
                    #with arcpy.da.UpdateCursor(table, ["SEG_GUID", "MILEPOST_FR", "MILEPOST_TO", "LRS_TYPE_ID"], sqlquery) as cursor:
                    cursor = arcpy.UpdateCursor(table, sqlquery)
                    for row in cursor:
                        segname_result['cursor'] = i
                        row.setValue('SEG_GUID', self.new_seg_guid)

                        lrstype = row.getValue('LRS_TYPE_ID')
                        MP_FR = row.getValue('MILEPOST_FR')
                        MP_TO = row.getValue('MILEPOST_TO')

                        if 'curvePaths' in geojson.keys():
                            # format for true curves
                            xym1 = []
                            for i in ge1['curvePaths'][0]:
                                if type(i) is list:
                                    xym1.append(i)
                                elif type(i) is dict:
                                    xym1.append(i['c'][0])
                        elif 'paths' in geojson.keys():
                            #format for no true curves
                            xym1 = geojson['paths'][0] # list of lists. each list has [x,y,m]



                        if lrstype in (1, 2, 3):  # only change records that are LRS 1, 2, or 3
                            # choose the right LRS values to change
                            lastge1vert = len(xym1) - 1
                            startv = round(xym1[0][2], 8)            # new start
                            endv = round(xym1[lastge1vert][2], 8)    # new end
                            mp_from = round(MP_FR, 8)                              # current start
                            mp_to = round(MP_TO, 8)                                # current end

                            segname_result['LRS'] = [lastge1vert,startv,endv,mp_from,mp_to]

                            # if FROM == first or last
                            if mp_from == startv:
                                # dont update from
                                if mp_to != startv and mp_to != endv:
                                    # it must be endv
                                    row.setValue('MILEPOST_TO', endv)
                            elif mp_from  == endv:
                                # dont update from
                                if mp_to != startv and mp_to != endv:
                                    # it must be start
                                    row.setValue('MILEPOST_TO', startv)
                            elif mp_to == startv:
                                # dont update to
                                if mp_from != startv and mp_from != endv:
                                    # it must be endv
                                    row.setValue('MILEPOST_FR', endv)
                            elif mp_to  == endv:
                                # dont update to
                                if mp_from != startv and mp_from != endv:
                                    # it must be start
                                    row.setValue('MILEPOST_FR', startv)
                            keeptrack[0].append(startv); keeptrack[1].append(endv); keeptrack[2].append(mp_from); keeptrack[3].append(mp_to)

                        cursor.updateRow(row)

                        i += 1

                    try: del row
                    except: pass
                    try: del cursor
                    except: pass

                    segname_result['keeptrack1'] = keeptrack

                if interp == False:
                    cursor = arcpy.UpdateCursor(table, sqlquery)
                    for row in cursor:
                        row.setValue('SEG_GUID',self.new_seg_guid)
                        cursor.updateRow(row)

                    try: del row
                    except: pass
                    try: del cursor
                    except: pass

                segname_result['result'] = 'success'
                segname_result['updates'] = len(orginalrows)

                # Check for an SRI
                if orginalrows[0][3]:
                    segname_result['sri'] = orginalrows[0][3]

                return segname_result
            else:
                segname_result['result'] = 'no matching records'
                return segname_result

        except:
            trace = traceback.format_exc()
            try: row; del row
            except: pass
            try: cursor; del cursor
            except: pass
            segname_result['result'] = 'fail'
            segname_result['trace'] = trace
            return segname_result






def bisect_points(ge1, ge2, droplength = 10, plot = False):
    """
        This function is used for address range interpolation when a line is split
        ge1 - geometry (esri JSON)
    """


    b_result = {'result': 'na'}
    import json, arcpy, math, traceback
    try:

        if 'curvePaths' in ge1.keys():
            # format for true curves
            xym1 = []
            for i in ge1['curvePaths'][0]:
                if type(i) is list:
                    xym1.append(i)
                elif type(i) is dict:
                    xym1.append(i['c'][0])
        elif 'paths' in ge1.keys():
            #format for no true curves
            xym1 = ge1['paths'][0] # list of lists. each list has [x,y,m]

        if 'curvePaths' in ge2.keys():
            # format for true curves
            xym2 = []
            for i in ge2['curvePaths'][0]:
                if type(i) is list:
                    xym2.append(i)
                elif type(i) is dict:
                    xym2.append(i['c'][0])
        elif 'paths' in ge2.keys():
            #format for no true curves
            xym2 = ge2['paths'][0]

        l1 = len(xym1) - 1; l2 = len(xym2) - 1
        if xym1[0][0:2] == xym2[0][0:2]:
            zero = xym1[0][0:2]
            end1 = xym1[l1][0:2]; end2 = xym2[l2][0:2]
            b_result['splitstartend 1'] = 'start'; b_result['splitstartend 2'] = 'start'  # start of guid1, start of guid2
        elif xym1[0][0:2] == xym2[l2][0:2]:
            zero = xym1[0][0:2]
            end1 = xym1[l1][0:2]; end2 = xym2[0][0:2]
            b_result['splitstartend 1'] = 'start'; b_result['splitstartend 2'] = 'end' # start of guid1, end of guid2
        elif xym1[l1][0:2] == xym2[0][0:2]:
            zero = xym1[l1][0:2]
            end1 = xym1[0][0:2]; end2 = xym2[l2][0:2]
            b_result['splitstartend 1'] = 'end'; b_result['splitstartend 2'] = 'start' # end of guid1, start of guid2
        elif xym1[l1][0:2] == xym2[l2][0:2]:
            zero = xym1[l1][0:2]
            end1 = xym1[0][0:2]; end2 = xym2[0][0:2]
            b_result['splitstartend 1'] = 'end'; b_result['splitstartend 2'] = 'end'

        b_result['match'] = zero

    except:
        b_result['result'] = 'fail'
        trace = traceback.format_exc()
        #NJRE_logger.exception(trace)
        b_result['trace'] = trace
        return b_result

    try:
        x1 = end1[0] - zero[0]
        y1 = end1[1] - zero[1]
        x2 = end2[0] - zero[0]
        y2 = end2[1] - zero[1]
        x2 += 0.000001
        y2 += 0.000001

        b_result['x1y1'] = str(x1)+','+str(y1); b_result['x2y2'] = str(x2)+','+str(y2)

        angle1 = round(math.atan2(y1,x1) % (math.pi/2) * (180/math.pi), 1)
        angle2 = round(math.atan2(y2,x2) % (math.pi/2) * (180/math.pi), 1)
        #print angle1, angle2
        if angle1 == angle2:
            print 'equal'

        # find the magnitude of the two vectors that are on either side of the vertex
        splitnode1mag = math.sqrt(x1**2 + y1**2)
        splitnode2mag = math.sqrt(x2**2 + y2**2)

        # scale the vectors to unit vectors (i.e. magnitude =1)
        x1scaled = x1/splitnode1mag
        y1scaled = y1/splitnode1mag
        x2scaled = x2/splitnode2mag
        y2scaled = y2/splitnode2mag

        # find the midpoint (i.e. bisector) of the line between the endpoints
        # add 10 to each coordinate. This will make the length (i.e. magnitude) about 10 feet.
        midx = ((x1scaled + x2scaled) / 2)
        midy = ((y1scaled + y2scaled) / 2)

        # solve for the factor that will be multiplied to x and y to get the magnitude to equal the droplength
        factori = droplength/(math.sqrt(midx**2 + midy**2))
        midx2 = midx*(factori)
        midy2 = midy*(factori)

        #print 'factori is: {0}'.format(factori)

        midx3 = midx2 * -1
        midy3 = midy2 * -1

        b_result['bisect_x1'] = midx2 + zero[0]
        b_result['bisect_y1'] = midy2 + zero[1]

        b_result['bisect_x2'] = midx3 + zero[0]
        b_result['bisect_y2'] = midy3 + zero[1]

        b_result['result'] = 'success'

    except:
        b_result['result'] = 'fail'
        trace = traceback.format_exc()
        #NJRE_logger.exception(trace)
        b_result['trace'] = trace
        return b_result

    if plot == False:
        return b_result

    if plot == True:
        try:
            import matplotlib.pyplot as plt
            plt.plot([0,x1],[0,y1], '-')
            plt.plot([0,x2],[0,y2], 'r-')

            plt.plot([0,x1scaled],[0,y1scaled], 'k')
            plt.plot([0,x2scaled],[0,y2scaled], 'k')

            plt.plot([x1,x2],[y1,y2], '--')
            plt.plot([x1scaled,x2scaled],[y1scaled,y2scaled], '--')

            plt.plot([midx],[midy], 'rD')
            plt.plot([midx2],[midy2], 'rD')
            plt.plot([midx3],[midy3], 'gD')

            plt.plot([0,midx],[0,midy], '--')
            plt.plot([0,midx2],[0,midy2], '--')
            plt.plot([0,midx3],[0,midy3], '--')
            plt.axis('equal')
            plt.show()

        except:
            b_result['result'] = 'math success, plot fail'
            trace = traceback.format_exc()
            b_result['trace'] = trace
            #NJRE_logger.exception(trace)
            return b_result
        finally:
            return b_result


class InterpolateAddress:
    def __init__(self, Footprint):
        self.Footprint = Footprint
    def interpolate(self, ge1, ge2, geocodeURL, segmentID):
        import traceback
        try:
            if not self.Footprint['SEGMENT'][0]['PRIME_NAME']:
                return None, None
            else:

                def is_even(num):
                    return num % 2 == 0

                addintmess = {'even': None, 'odd': None, 'result': 'na', 'message': 'na', 'primename': False, 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}
                addintmess['primename'] = True

                # Create a dictionary to hold the interpolated values.

                #InterpolatedValues = {'ADDR_L_FR': LF, 'ADDR_L_TO': LT, 'ADDR_R_FR': RF, 'ADDR_R_TO': RT}
                InterpolatedValues = {'ADDR_L_FR': None, 'ADDR_L_TO': None, 'ADDR_R_FR': None, 'ADDR_R_TO': None}

                # define some parameters to avoid blowing up the code
                LF = self.Footprint['SEGMENT'][0]['ADDR_L_FR']
                LT = self.Footprint['SEGMENT'][0]['ADDR_L_TO']
                RF = self.Footprint['SEGMENT'][0]['ADDR_R_FR']
                RT = self.Footprint['SEGMENT'][0]['ADDR_R_TO']


                if (LF and LT): # if there are values on the left side
                    if is_even(LF) and is_even(LT):
                        addintmess['even'] = 'left'
                    elif not is_even(LF) and not is_even(LT):
                        addintmess['odd'] = 'left'

                if (RF and RT):   # if there are values on the right side
                    if is_even(RF) and is_even(RT):
                        addintmess['even'] = 'right'
                    elif not is_even(RF) and not is_even(RT):
                        addintmess['odd'] = 'right'


                if addintmess['even'] and (addintmess['even'] == addintmess['odd']): # if theres a value in one and they are equal
                    addintmess['result'] = 'fail'
                    addintmess['message'] = 'addresses on either side are both odd or both even'

                if (addintmess['odd'] or addintmess['even']) and addintmess['result'] == 'na': # we have a left and a right and they arent both odd or even

                    # now we have both geometries. Get the bisector points on either side of the split
                    bisector = bisect_points(ge1, ge2, droplength = 10, plot = False)
                    gc = Geocode(geocodeURL)   #'http://geodata.state.nj.us/arcgis/rest/services/Tasks/Addr_NJ_road/GeocodeServer'
                    # reverse geocode the first side of the road
                    rgcside1 = gc.reverse_geocode(bisector['bisect_x1'], bisector['bisect_y1'], f = 'pjson', distance = 10)
                    rgcside2 = gc.reverse_geocode(bisector['bisect_x2'], bisector['bisect_y2'], f = 'pjson', distance = 10)

                    # which segment are we working on?
                    if segmentID == 1:
                        bis_start_end = bisector['splitstartend 1']
                    if segmentID == 2:
                        bis_start_end = bisector['splitstartend 2']

                    # First Geocode
                    if rgcside1['result'] == 'success':
                        if is_even(int(rgcside1['address number'])): # drop point 1 is even
                            if addintmess['even'] == 'left':
                                if int(rgcside1['address number']) <= max(LF, LT) and int(rgcside1['address number']) >= min(LF, LT): # if the geocoded address is within the range of the left side of the road
                                    # now the geocoded address should match the FR or the TO
                                    if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                        InterpolatedValues['ADDR_L_FR'] = (int(rgcside1['address number']), True)
                                        InterpolatedValues['ADDR_L_TO'] = (LT, True)
                                        addintmess['addrlfr'] = True
                                    if bis_start_end == 'end': # if this is the end of guid1, the reassign left TO
                                        # descending or ascending?
                                        if LF - int(rgcside1['address number']) < 0: # ascending
                                            InterpolatedValues['ADDR_L_TO'] = (int(rgcside1['address number']) -2, True)
                                        elif LF - int(rgcside1['address number']) > 0: # descending
                                            InterpolatedValues['ADDR_L_TO'] = (int(rgcside1['address number']) + 2, True)
                                        else:
                                            InterpolatedValues['ADDR_L_TO'] = (int(rgcside1['address number']), True)
                                        InterpolatedValues['ADDR_L_FR'] = (LF, True)
                                        addintmess['addrlto'] = True

                            if addintmess['even'] == 'right':
                                if int(rgcside1['address number']) <= max(RF, RT) and int(rgcside1['address number']) >= min(RF, RT): # if the geocoded address is within the range of the left side of the road
                                    if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                        InterpolatedValues['ADDR_R_FR'] = (int(rgcside1['address number']), True)
                                        InterpolatedValues['ADDR_R_TO'] = (RT, True)
                                        addintmess['addrrfr'] = True
                                    if bis_start_end == 'end': # if this is the end of guid1, the reassign left TO
                                         # descending or ascending?
                                        if RF - int(rgcside1['address number']) < 0: # ascending
                                            InterpolatedValues['ADDR_R_TO'] = (int(rgcside1['address number']) - 2, True)
                                        elif RF - int(rgcside1['address number']) > 0: # descending
                                            InterpolatedValues['ADDR_R_TO'] = (int(rgcside1['address number']) + 2, True)
                                        else:
                                            InterpolatedValues['ADDR_R_TO'] = (int(rgcside1['address number']), True)
                                        InterpolatedValues['ADDR_R_FR'] = (RF, True)
                                        addintmess['addrrto'] = True

                    # Second Geocode
                    if rgcside2['result'] == 'success':
                        if is_even(int(rgcside2['address number'])) == False: # drop point 2 is odd
                            if addintmess['odd'] == 'left':
                                if int(rgcside2['address number']) <= max(LF, LT) and int(rgcside2['address number']) >= min(LF, LT): # if the geocoded address is within the range of the left side of the road
                                    # now the geocoded address should match the FR or the TO
                                    if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                        InterpolatedValues['ADDR_L_FR'] = (int(rgcside2['address number']), True)
                                        InterpolatedValues['ADDR_L_TO'] = (LT, True)
                                        addintmess['addrlfr'] = True
                                    if bis_start_end == 'end': # if this is the start of guid1, the reassign left TO
                                        # descending or ascending?
                                        if LF - int(rgcside2['address number']) < 0: # ascending
                                            InterpolatedValues['ADDR_L_TO'] = (int(rgcside2['address number']) -2, True)
                                        elif LF - int(rgcside1['address number']) > 0: # descending
                                            InterpolatedValues['ADDR_L_TO'] = (int(rgcside2['address number']) + 2, True)
                                        else:
                                            InterpolatedValues['ADDR_L_TO'] = (int(rgcside2['address number']), True)
                                        InterpolatedValues['ADDR_L_FR'] = (LF, True)
                                        addintmess['addrlto'] = True

                            if addintmess['odd'] == 'right':
                                if int(rgcside2['address number']) <= max(RF, RT) and int(rgcside2['address number']) >= min(RF, RT): # if the geocoded address is within the range of the left side of the road
                                    if bis_start_end == 'start': # if this is the start of guid1, the reassign left FR
                                        InterpolatedValues['ADDR_R_FR'] = (int(rgcside2['address number']), True)
                                        InterpolatedValues['ADDR_R_TO'] = (RT, True)
                                        addintmess['addrrfr'] = True
                                    if bis_start_end == 'end': # if this is the start of guid1, the reassign left TO
                                         # descending or ascending?
                                        if RF - int(rgcside2['address number']) < 0: # ascending
                                            InterpolatedValues['ADDR_R_TO'] = (int(rgcside2['address number']) - 2, True)
                                        elif RF - int(rgcside2['address number']) > 0: # descending
                                            InterpolatedValues['ADDR_R_TO'] = (int(rgcside2['address number']) + 2, True)
                                        else:
                                            InterpolatedValues['ADDR_R_TO'] = (int(rgcside2['address number']), True)
                                        InterpolatedValues['ADDR_R_FR'] = (RF, True)
                                        addintmess['addrrto'] = True

                if not InterpolatedValues['ADDR_L_FR'] and LF:
                    InterpolatedValues['ADDR_L_FR'] = (LF, False)
                if not InterpolatedValues['ADDR_L_TO'] and LT:
                    InterpolatedValues['ADDR_L_TO'] = (LT, False)
                if not InterpolatedValues['ADDR_R_FR'] and RF:
                    InterpolatedValues['ADDR_R_FR'] = (RF, False)
                if not InterpolatedValues['ADDR_R_TO'] and RT:
                    InterpolatedValues['ADDR_R_TO'] = (RT, False)

                return InterpolatedValues, addintmess

        except:
            return None, None
            #NJRE_logger.exception(traceback.format_exc())



def wkt_to_esrijson(geometry):
    """Convert ESRI geometry object from WKT to JSON
    geometry - ESRI Geometry object (SHAPE@)
    returns dictionary with 2 keys; 'result' and 'esrijson'

    esrijson - the esriJSON object
    result - 'success' or 'fail'
    """
    import arcpy, traceback

    wkt_dict = {'result': 'na'}

    try:
        wkt = geometry.WKT
        # grab only the stuff within the parens
        wktpaths = wkt[wkt.find("((")+2:wkt.find("))")]
        wktpaths2 = wktpaths.split(", ")

        # split by spaces to get the coordinates in their own list
        wktpaths3 = []
        for xy in wktpaths2:
            wktpaths3.append(xy.split(" "))

        # make it a cictionary and encapsulate in a list, so it mimicks the json
        ge1 = {'paths': [wktpaths3]}

        # convert to floating point from unicode
        for i,v in enumerate(ge1['paths'][0]):
            for ii,vv in enumerate(v):
                ge1['paths'][0][i][ii] = float(vv)

        wkt_dict['result'] = 'success'
        wkt_dict['esrijson'] = ge1
        return wkt_dict
    except:
        wkt_dict['result'] = 'fail'
        trace = traceback.format_exc()
        wkt_dict['trace'] = trace
        return wkt_dict

def esrijson_to_wkt(esrijson):
    """"Change the 'paths' key values to WKT
    esrijson - The JSON 'paths' key pair"""
    import itertools, traceback
    wkt_dict = {'result': 'na'}
    try:
        count = 0
        for i in itertools.chain(esrijson['paths'][0]):
            ii = str(i)
            ii = ii.replace("[","")
            ii = ii.replace("]","")
            ii = ii.replace(","," ")
            if count == 0:
                wkt = 'MULTILINESTRING M  ((' + ii
            elif (len(esrijson['paths'][0])-1) == count:
                wkt = wkt + ', '+ ii + '))'
            elif count > 0:
                wkt = wkt + ', '+ ii
            count += 1
        wkt_dict['WKT'] = wkt
        wkt_dict['result'] = 'success'
        return wkt_dict
    except:
        wkt_dict['result'] = 'fail'
        trace = traceback.format_exc()
        wkt_dict['trace'] = trace
        return wkt_dict


class Footprint(object):
    footprint = None
    def __init__(self, GUID, qmode = 'SEG_GUID'):
        self.GUID = GUID
        self.qmode = qmode
    def getfootprint(self, tables):
        """tables - must be a list of table alias names (long names) in the order (['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']"""

        import traceback, arcpy

        try:
            segmentfc = tables[0]
            segnametab = tables[1]
            segshieldtab = tables[2]
            linreftab = tables[3]
            sldtab = tables[4]
            segcommtab = tables[5]
            transtab = tables[6]
            segmentchangetab = tables[7]

            seg_sql = ''

            # GEt the SEG_GUID of the selected feature
        # GEt the SEG_GUID of the selected feature
            if not self.GUID:
                print '2'
                if self.qmode == 'SEG_GUID':
                    with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            self.GUID = row[0]
                    seg_sql = sqlGUID("SEG_GUID", self.GUID)
                    seg_sql_segment = sqlGUID("SEG_GUID", self.GUID)
                if self.qmode == 'GLOBALID':
                    with arcpy.da.SearchCursor(segmentfc, ["GLOBALID"]) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            self.GUID = row[0]
                    seg_sql_segment = sqlGUID("GLOBALID", self.GUID)
            else:
                #print '1'
                if self.qmode == 'SEG_GUID':
                    seg_sql = sqlGUID("SEG_GUID", self.GUID)
                    seg_sql_segment = sqlGUID("SEG_GUID", self.GUID)
                if self.qmode == 'GLOBALID':
                    seg_sql_segment = sqlGUID("GLOBALID", self.GUID)
                    #print 'seg_sql', seg_sql_segment


            if len(seg_sql_segment) > 0:
                #print 'you'
                ####################################################################

                segment_current = []  # this will be a list of tuples with current records
                with arcpy.da.SearchCursor(segmentfc, "*", seg_sql_segment) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        #print 'innnnn'
                        dictiter = {}
                        for i,field in enumerate(cursor.fields):
                            dictiter[field] = row[i]
                        segment_current.append(dictiter)
                        del dictiter
                        #print 'segment curr', segment_current

                seg_sql = sqlGUID("SEG_GUID", segment_current[0]['SEG_GUID'])

                segname_current = [] # this will be a list of tuples with current records
                with arcpy.da.SearchCursor(segnametab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        dictiter = {}
                        for i,field in enumerate(cursor.fields):
                            dictiter[field] = row[i]
                        segname_current.append(dictiter)
                        del dictiter

                segshield_current = [] # this will be a list of tuples with current records
                with arcpy.da.SearchCursor(segshieldtab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        dictiter = {}
                        for i,field in enumerate(cursor.fields):
                            dictiter[field] = row[i]
                        segshield_current.append(dictiter)
                        del dictiter


                lr_current = []  # this will be a list of tuples with current records
                sris = []
                with arcpy.da.SearchCursor(linreftab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        dictiter = {}
                        for i,field in enumerate(cursor.fields):
                            dictiter[field] = row[i]
                        lr_current.append(dictiter)
                        if dictiter["SRI"]:
                            if len(sris) == 0:
                                sris.append(dictiter["SRI"])
                            if len(sris) > 0:
                                if dictiter["SRI"] not in sris:
                                    sris.append(dictiter["SRI"])
                        del dictiter

                sld_current = [] # this will be a list of tuples with current records
                for sri in sris:
                    sri_sql = sqlGUID("SRI", sri)
                    with arcpy.da.SearchCursor(sldtab, "*", sri_sql) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            dictiter = {}
                            for i,field in enumerate(cursor.fields):
                                dictiter[field] = row[i]
                            sld_current.append(dictiter)
                            del dictiter


                comm_current = [] # this will be a list of tuples with current records
                with arcpy.da.SearchCursor(segcommtab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        dictiter = {}
                        for i,field in enumerate(cursor.fields):
                            dictiter[field] = row[i]
                        comm_current.append(dictiter)
                        del dictiter

                segment_trans = []  # this will be a list of tuples with current records
                seg_sql_new = sqlGUID("SEG_GUID_NEW", self.GUID)
                with arcpy.da.SearchCursor(transtab, "*", seg_sql_new) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        dictiter = {}
                        for i,field in enumerate(cursor.fields):
                            dictiter[field] = row[i]
                        segment_trans.append(dictiter)
                        del dictiter

                segchange_current = []
                if segment_trans:
                    for st in segment_trans:
                        if st['SEG_GUID_ARCH']:
                            seg_sql_arch = sqlGUID("SEG_GUID_ARCH", st['SEG_GUID_ARCH'])
                            with arcpy.da.SearchCursor(segmentchangetab, "*", seg_sql_arch) as cursor:
                                for row in cursor:
                                    dictiter = {}
                                    for i,field in enumerate(cursor.fields):
                                        dictiter[field] = row[i]
                                    segchange_current.append(dictiter)
                                    del dictiter


                Footprint.footprint = {}  # a dictionary of lists of tuples
                Footprint.footprint['SEGMENT'] = segment_current
                Footprint.footprint['SEG_NAME'] = segname_current
                Footprint.footprint['SEG_SHIELD'] = segshield_current
                Footprint.footprint['LINEAR_REF'] = lr_current
                Footprint.footprint['SLD_ROUTE'] = sld_current
                Footprint.footprint['SEGMENT_COMMENTS'] = comm_current
                Footprint.footprint['SEGMENT_TRANS'] = segment_trans
                Footprint.footprint['SEGMENT_CHANGE'] = segchange_current
                if self.qmode == 'SEG_GUID':
                    Footprint.footprint['SEG_GUID'] = self.GUID
                if self.qmode == 'GLOBALID':
                    Footprint.footprint['SEG_GUID'] = segment_current[0]['SEG_GUID']

                return Footprint.footprint

        except:
            return traceback.format_exc()
            print(traceback.format_exc())

class DomainConverter(object):
    def __init__(self, Domains):
        # make the wak across dictionary. It has 2 dictionaries in it.
        self.Domains = Domains
        self.DomainsReverse = {}
        for dfield, dvaluedict in self.Domains.iteritems():  # reverse the domains, so that the domain value is the key, and the coded value is the value
            mt = {}
            for k,v in dvaluedict.iteritems():
                mt[v] = k
            self.DomainsReverse[dfield] = mt


        self.DomainWx = {}
        self.DomainWx['FieldToDomain'] = {'MUNI_ID_L': 'GNIS_NAME','MUNI_ID_R': 'GNIS_NAME','ELEV_TYPE_ID_FR' : 'ELEV_TYPE','ELEV_TYPE_ID_TO' : 'ELEV_TYPE','ACC_TYPE_ID' : 'ACCESS_TYPE','SURF_TYPE_ID' : 'SURFACE_TYPE','STATUS_TYPE_ID' : 'STATUS_TYPE','SYMBOL_TYPE_ID' : 'SYMBOL_TYPE','JURIS_TYPE_ID' : 'JURIS_TYPE','CHANGE_TYPE_ID' : 'CHANGE_TYPE','TRAVEL_DIR_TYPE_ID' : 'TRAVEL_DIR_TYPE','OIT_REV_TYPE_ID' : 'REVIEW_TYPE', 'DOT_REV_TYPE_ID' : 'REVIEW_TYPE','SHIELD_TYPE_ID' : 'SHIELD_TYPE','LRS_TYPE_ID' : 'LRS_TYPE','ROUTE_TYPE_ID' : 'ROUTE_TYPE','SHIELD_SUBTYPE_ID' : 'SHIELD_SUBTYPE','SEG_TYPE_ID': 'SEGMENT_TYPE','DATA_SRC_TYPE_ID': 'DATA_SOURCE_TYPE','NAME_TYPE_ID': 'NAME_TYPE'}  # unused   [u'Munic_arc_Vertex_Rules', u'PCODE_TYPE', , u'EDIT_TYPE',]
        self.DomainWx['DomainToCoded'] = {}
        for key,val in self.DomainWx['FieldToDomain'].iteritems(): self.DomainWx['DomainToCoded'][val] = key

    def ToDomain(self, Footprint):

        try:
            FpX = Footprint
            for table, recordlist in FpX.iteritems(): # iterate throught the tables
                if recordlist and table != 'SEG_GUID':
                    for i, record in enumerate(recordlist): # iterate throught the list of records in the table
                        for field,val in record.iteritems():  # iterate throught the key and value for the record ***val is the value in the current field***
                            for wxkey, wxval in self.DomainWx['FieldToDomain'].iteritems(): # search to see if there is a domain avaialable
                                if field == wxkey:  # Yes, there is a domain available
                                    for Dkey, DvalueDict in self.Domains[wxval].iteritems(): # iterate throught the actual domain dicts
                                        if val == Dkey: # yes, there is a match
                                            FpX[table][i][field] = DvalueDict  # swap out the coded value with the domain value
            return FpX
        except:
            print traceback.format_exc()
            return None

    def ToCoded(self, Footprint):

        try:
            FpX = Footprint
            for table, recordlist in FpX.iteritems(): # iterate throught the tables
                if recordlist and table != 'SEG_GUID':
                    for i, record in enumerate(recordlist): # iterate throught the list of records in the table
                        for field,val in record.iteritems():  # iterate throught the key and value for the record ***val is the value in the current field***
                            for wxkey, wxval in self.DomainWx['FieldToDomain'].iteritems(): # search to see coded value available
                                if field == wxkey:  # Yes, there is a coded value available
                                    for Dkey, DvalueDict in self.DomainsReverse[wxval].iteritems(): # iterate throught the actual domain dicts
                                        if str(val) == str(Dkey): # yes, there is a match
                                            FpX[table][i][field] = DvalueDict  # swap out the coded value with the domain value
            return FpX
        except:
            print traceback.format_exc()
            return None


class SplitGeoprocessing:
    def __init__(self, Split1_Footprint, Split2_Footprint, ge1, ge2, Footprint1, Footprint2, originalgeo, tables, scratch):
        """The SplitGeoprocessing task is the new implementation of the "excecute" method from the NJRE.pyt Split tool.
        Split1_Footprint - The parsed dictionary object from the first split tool.
        Split2_Footprint - The parsed dictionary object from the second split tool.
        ge1 - Geometry object for the first new segment.
        ge2 - Geometry object for the second new segment.
        Footprint1 - The Footprint object from the newly split first segment.
        Footprint2 - The Footprint object from the newly split second segment.
        originalgeo - The geometry object from the original segment.
        tables - A list of table variables. i.e. ['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']
        """


        import arcpy, traceback, os, sys, logging

        self.Split1_Footprint = Split1_Footprint # {'SEGMENT': [{'OIT_REV_TYPE_ID': u'F', 'ELEV_TYPE_ID_FR': 0, 'ZIPNAME_R': u'BARNEGAT', 'TRAVEL_DIR_TYPE_ID': u'B', 'ACC_TYPE_ID': u'N', 'ZIPCODE_L': u'08005', 'SURF_TYPE_ID': u'I', 'MUNI_ID_R': u'882070', 'ADDR_R_FR': 172, 'ADDR_L_FR': 99999999999999999999L, 'STATUS_TYPE_ID': u'A', 'ELEV_TYPE_ID_TO': 0, 'JURIS_TYPE_ID': u'PUB', 'ADDR_R_TO': 176, 'DOT_REV_TYPE_ID': u'F', 'MUNI_ID_L': u'882070', 'ZIPCODE_R': u'08005', 'SYMBOL_TYPE_ID': 700, 'ZIPNAME_L': u'BARNEGAT', 'ADDR_L_TO': 66666666666666666666L}]}
        self.Split2_Footprint = Split2_Footprint
        self.ge1 = ge1
        self.ge2 = ge2
        self.Footprint1 = Footprint1
        self.Footprint2 = Footprint2
        self.originalgeo = originalgeo
        self.seg_guid1 = calcGUID()
        self.seg_guid2 = calcGUID()


        # tablenames is a list of tablenames  ['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']
        self.segmentfc = tables[0]
        self.segnametab = tables[1]
        self.segshieldtab = tables[2]
        self.linreftab = tables[3]
        self.sldtab = tables[4]
        self.segcommtab = tables[5]
        self.transtab = tables[6]
        self.segmentchangetab = tables[7]

        #####################################
        #LOGGER
        self.logger = logging.getLogger('SplitGeoprocessing')
        self.logger.setLevel(logging.DEBUG)

        # create a file handler
        filehandlerpath = os.path.join(scratch, 'SplitGeoprocessing.log')  #os.path.join(os.path.dirname(__file__), 'SplitGeoprocessing.log')
        if os.path.exists(filehandlerpath):
            os.remove(filehandlerpath)
        self.handler = logging.FileHandler(filehandlerpath)
        self.handler.setLevel(logging.DEBUG)

        # create a logging format
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

        self.logger.info('SplitGeoprocessing Class Called, Geoprocessing started...')
        self.logger.info('Original SEG_GUID: {0}'.format(self.Footprint1["SEG_GUID"]))

        self.logger.info('New SEG_GUID for segment 1 is {0}'. format(self.seg_guid1))
        self.logger.info('New SEG_GUID for segment 2 is {0}'. format(self.seg_guid2))

        self.splittool_result = {'block1': False, 'block2': False, 'block3': False}

    def run(self):
        import arcpy, traceback, os, sys, logging

        try:

            #################################################
            #################################################
            ## BLOCK 1 -- Update and Copy

            self.updateandcopy = UpdateCopy(self.Footprint1["SEG_GUID"], self.seg_guid1, self.seg_guid2) # UpadateCopy class object

            ## SEG_NAME
            segnameresult = self.updateandcopy.segname(self.segnametab)
            if segnameresult['result'] == 'success':
                self.logger.info('SEG_NAME Attributes copied to the 2 new segments')
            elif segnameresult['result'] == 'no matching records':
                self.logger.info('No SEG_NAME records in the original segment')
            else:
                self.logger.warning("\nUpdateCopy.segname failed, result is: {0}".format(segnameresult))

            ## SEG_SHIELD
            segshieldresult = self.updateandcopy.segshield(self.segshieldtab)
            if segshieldresult['result'] == 'success':
                self.logger.info('SEG_SHIELD Attributes copied to the 2 new segments')
            elif segshieldresult['result'] == 'no matching records':
                self.logger.info('No SEG_SHIELD records in the original segment')
            else:
                self.logger.warning("\nUpdateCopy.segshield failed, result is: {0}".format(segshieldresult))

            ## LINEAR_REF
            lrM = True
            try:

                if 'curvePaths' in self.ge1.keys():
                    # format for true curves
                    xym1 = []; xym2 = [];
                    for i in self.ge1['curvePaths'][0]:
                        if type(i) is list:
                            xym1.append(i)
                        elif type(i) is dict:
                            xym1.append(i['c'][0])
                    for i in self.ge2['curvePaths'][0]:
                        if type(i) is list:
                            xym2.append(i)
                        elif type(i) is dict:
                            xym2.append(i['c'][0])
                elif 'paths' in self.ge1.keys():
                    #format for no true curves
                    xym1 = self.ge1['paths'][0] # list of lists. each list has [x,y,m]
                    xym2 = self.ge2['paths'][0]

                round(xym1[0][2],8)
                round(xym2[0][2],8)
            except:
                lrM = False
                self.logger.warning('LINEAR_REF MILEPOST values were not updated, because there are no M-Values on this segment.')
            lrresult = self.updateandcopy.linearref(self.linreftab, self.ge1, self.ge2, lrM)
            if lrresult['result'] == 'success':
                self.logger.info('LINEAR_REF Attributes copied to the 2 new segments')
                #self.logger.info('LINEAR_REF result: {0}'.format(lrresult))
            elif lrresult['result'] == 'no matching records':
                self.logger.info('No LINEAR_REF records in the original segment')
            else:
                self.logger.warning("UpdateCopy.linearref failed, result is: {0}. The purpose of this function is to update the MILEPOST values based on the new M-Values. The failure is most likely due to the segment not having M-Values.".format(lrresult))

            ## SEGMENT_COMMENTS

            commdelresult = delete(self.Footprint1["SEG_GUID"],self.segcommtab)
            if commdelresult['result'] == 'success':
                self.logger.info('SEGMENT_COMMENTS records deleted')
            elif commdelresult['result'] == 'no matches':
                self.logger.info('No SEGMENT_COMMENTS records found')
            elif commdelresult['trace']:
                self.logger.warning("\nerebus.delete failed, result is: {0}".format(lrresult))

            self.splittool_result['block1'] = True; self.splittool_result['segnameresult'] = segnameresult; self.splittool_result['segshieldresult'] = segshieldresult; self.splittool_result['lrresult'] = lrresult; self.splittool_result['commentsdelete'] = commdelresult

            #################################################
            #################################################
            ## BLOCK 2 -- Segment

            # create sql queries
            globalsql1 = sqlGUID("GLOBALID", self.Footprint1['SEGMENT'][0]['GLOBALID'])
            globalsql2 = sqlGUID("GLOBALID", self.Footprint2['SEGMENT'][0]['GLOBALID'])
            self.logger.info('GLOBALID for segment 1 is {0}'. format(globalsql1))
            self.logger.info('GLOBALID for segment 2 is {0}'. format(globalsql2))

            # update cursor for both segments
##            i = 0
##            with arcpy.da.SearchCursor(self.segmentfc, "*") as c:
##                for r in c:
##                    if i < 5:
##                        self.logger.info('value is {0}'. format(r))
##                    i += 1

##
##            with arcpy.da.UpdateCursor(self.segmentfc, ["SEG_GUID"]) as cursor:
##                for row in cursor:
##                    self.logger.info('Segment 1 in da.UpdateCurosr')
##                    row[0] = self.seg_guid1
##                    cursor.updateRow(row)
##
##
##            #['SEG_GUID','ADDR_L_FR' ,'ADDR_L_TO']

            cursor = arcpy.UpdateCursor(self.segmentfc, globalsql1)
            for row in cursor:
                row.setValue('SEG_GUID', self.seg_guid1)
                row.setValue('ADDR_L_FR', self.Split1_Footprint['SEGMENT'][0]['ADDR_L_FR'])
                row.setValue('ADDR_L_TO', self.Split1_Footprint['SEGMENT'][0]['ADDR_L_TO'])
                row.setValue('ADDR_R_FR', self.Split1_Footprint['SEGMENT'][0]['ADDR_R_FR'])
                row.setValue('ADDR_R_TO', self.Split1_Footprint['SEGMENT'][0]['ADDR_R_TO'])
                row.setValue('ZIPCODE_L', self.Split1_Footprint['SEGMENT'][0]['ZIPCODE_L'])
                row.setValue('ZIPCODE_R', self.Split1_Footprint['SEGMENT'][0]['ZIPCODE_R'])
                row.setValue('ZIPNAME_L', self.Split1_Footprint['SEGMENT'][0]['ZIPNAME_L'])
                row.setValue('ZIPNAME_R', self.Split1_Footprint['SEGMENT'][0]['ZIPNAME_R'])
                row.setValue('MUNI_ID_L', self.Split1_Footprint['SEGMENT'][0]['MUNI_ID_L'])
                row.setValue('MUNI_ID_R', self.Split1_Footprint['SEGMENT'][0]['MUNI_ID_R'])
                row.setValue('ELEV_TYPE_ID_FR', self.Split1_Footprint['SEGMENT'][0]['ELEV_TYPE_ID_FR'])
                row.setValue('ELEV_TYPE_ID_TO', self.Split1_Footprint['SEGMENT'][0]['ELEV_TYPE_ID_TO'])
                row.setValue('ACC_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['ACC_TYPE_ID'])
                row.setValue('SURF_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['SURF_TYPE_ID'])
                row.setValue('STATUS_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['STATUS_TYPE_ID'])
                row.setValue('SYMBOL_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['SYMBOL_TYPE_ID'])
                row.setValue('TRAVEL_DIR_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['TRAVEL_DIR_TYPE_ID'])
                row.setValue('JURIS_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['JURIS_TYPE_ID'])
                row.setValue('OIT_REV_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['OIT_REV_TYPE_ID'])
                row.setValue('DOT_REV_TYPE_ID', self.Split1_Footprint['SEGMENT'][0]['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            try: del row
            except: pass
            try: del cursor
            except: pass


            self.logger.info('Segment 1 fields updated in SEGMENT')

            cursor = arcpy.UpdateCursor(self.segmentfc, globalsql2)
            for row in cursor:
                row.setValue('SEG_GUID', self.seg_guid2)
                row.setValue('ADDR_L_FR', self.Split2_Footprint['SEGMENT'][0]['ADDR_L_FR'])
                row.setValue('ADDR_L_TO', self.Split2_Footprint['SEGMENT'][0]['ADDR_L_TO'])
                row.setValue('ADDR_R_FR', self.Split2_Footprint['SEGMENT'][0]['ADDR_R_FR'])
                row.setValue('ADDR_R_TO', self.Split2_Footprint['SEGMENT'][0]['ADDR_R_TO'])
                row.setValue('ZIPCODE_L', self.Split2_Footprint['SEGMENT'][0]['ZIPCODE_L'])
                row.setValue('ZIPCODE_R', self.Split2_Footprint['SEGMENT'][0]['ZIPCODE_R'])
                row.setValue('ZIPNAME_L', self.Split2_Footprint['SEGMENT'][0]['ZIPNAME_L'])
                row.setValue('ZIPNAME_R', self.Split2_Footprint['SEGMENT'][0]['ZIPNAME_R'])
                row.setValue('MUNI_ID_L', self.Split2_Footprint['SEGMENT'][0]['MUNI_ID_L'])
                row.setValue('MUNI_ID_R', self.Split2_Footprint['SEGMENT'][0]['MUNI_ID_R'])
                row.setValue('ELEV_TYPE_ID_FR', self.Split2_Footprint['SEGMENT'][0]['ELEV_TYPE_ID_FR'])
                row.setValue('ELEV_TYPE_ID_TO', self.Split2_Footprint['SEGMENT'][0]['ELEV_TYPE_ID_TO'])
                row.setValue('ACC_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['ACC_TYPE_ID'])
                row.setValue('SURF_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['SURF_TYPE_ID'])
                row.setValue('STATUS_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['STATUS_TYPE_ID'])
                row.setValue('SYMBOL_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['SYMBOL_TYPE_ID'])
                row.setValue('TRAVEL_DIR_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['TRAVEL_DIR_TYPE_ID'])
                row.setValue('JURIS_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['JURIS_TYPE_ID'])
                row.setValue('OIT_REV_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['OIT_REV_TYPE_ID'])
                row.setValue('DOT_REV_TYPE_ID', self.Split2_Footprint['SEGMENT'][0]['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            try: del row
            except: pass
            try: del cursor
            except: pass

            self.logger.info('Segment 2 fields updated in SEGMENT')


            self.splittool_result['block2'] = True

            #################################################
            #################################################
            ## BLOCK 3 -- SEGMENT_TRANS and SEGMENT_CHANGE

            ########################################################################
            ## Insert two new records into SEGMENT_TRANS

            #segment_trans(oldguid, newguid, table, seg_id_arch)
            trans_result1 = segment_trans(self.Footprint1["SEG_GUID"], self.seg_guid1, self.transtab, self.Footprint1["SEGMENT"][0]["SEG_ID"])
            trans_result2 = segment_trans(self.Footprint1["SEG_GUID"], self.seg_guid2, self.transtab, self.Footprint2["SEGMENT"][0]["SEG_ID"])

            if trans_result1['result'] == 'success':
                self.logger.info('New record inserted into SEGMENT_TRANS for segment 1')
            else:
                self.logger.warning("\neFailed to insert record into SEGMENT_TRANS, result is: {0}".format(trans_result1))
            if trans_result2['result'] == 'success':
                self.logger.info('New record inserted into SEGMENT_TRANS for segment 2')
            else:
                self.logger.warning("\neFailed to insert record into SEGMENT_TRANS, result is: {0}".format(trans_result2))

            ########################################################################
            ## Insert one new record into SEGMENT_CHANGE

            sc_obj = SegmentChange(self.Footprint1["SEG_GUID"], self.segmentchangetab)
            scresult = sc_obj.insert(self.originalgeo, seg_id_arch = self.Footprint1["SEGMENT"][0]["SEG_ID"]) # insert(self, segmentgeo, change_type_id = 'R', comments = None, seg_id_arch = None)
            if scresult['result'] == 'success':
                self.logger.info('New record inserted into SEGMENT_CHANGE')
                #self.logger.info('New record inserted into SEGMENT_CHANGE {0}'.format(scresult['method']))
            else:
                self.logger.warning("\neFailed to insert record into SEGMENT_CHANGE, result is: {0}".format(scresult))

            self.splittool_result['block3'] = True; self.splittool_result['trans_result1'] = trans_result1; self.splittool_result['trans_result2'] = trans_result2; self.splittool_result['scresult'] = scresult

            self.logger.info('Geoprocessing Completed Successfully')
            self.logger.removeHandler(self.handler)
            return True, 'You made it'


        except:
            trace = traceback.format_exc()
            self.splittool_result['trace'] = trace
            self.logger.info(self.splittool_result)
            self.logger.exception(trace)
            self.logger.warning('Geoprocessing Failed')
            self.logger.removeHandler(self.handler)
            try: del row
            except: pass
            try: del cursor
            except: pass
            return None, trace

class SegmentGeoprocessing:
    def __init__(self, Pre_Footprint, Post_Footprint, tables, scratch):
        """The SplitGeoprocessing task is the new implementation of the "excecute" method from the NJRE.pyt Split tool.
        Split1_Footprint - The parsed dictionary object from the first split tool.
        Split2_Footprint - The parsed dictionary object from the second split tool.
        ge1 - Geometry object for the first new segment.
        ge2 - Geometry object for the second new segment.
        Footprint1 - The Footprint object from the newly split first segment.
        Footprint2 - The Footprint object from the newly split second segment.
        originalgeo - The geometry object from the original segment.
        tables - A list of table variables. i.e. ['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']
        """

        import arcpy, traceback, os, sys, logging

        self.Pre_Footprint = Pre_Footprint # {'SEGMENT': [{'OIT_REV_TYPE_ID': u'F', 'ELEV_TYPE_ID_FR': 0, 'ZIPNAME_R': u'BARNEGAT', 'TRAVEL_DIR_TYPE_ID': u'B', 'ACC_TYPE_ID': u'N', 'ZIPCODE_L': u'08005', 'SURF_TYPE_ID': u'I', 'MUNI_ID_R': u'882070', 'ADDR_R_FR': 172, 'ADDR_L_FR': 99999999999999999999L, 'STATUS_TYPE_ID': u'A', 'ELEV_TYPE_ID_TO': 0, 'JURIS_TYPE_ID': u'PUB', 'ADDR_R_TO': 176, 'DOT_REV_TYPE_ID': u'F', 'MUNI_ID_L': u'882070', 'ZIPCODE_R': u'08005', 'SYMBOL_TYPE_ID': 700, 'ZIPNAME_L': u'BARNEGAT', 'ADDR_L_TO': 66666666666666666666L}]}
        self.Post_Footprint = Post_Footprint

        # tablenames is a list of tablenames  ['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']
        self.segmentfc = tables[0]
        self.segnametab = tables[1]
        self.segshieldtab = tables[2]
        self.linreftab = tables[3]
        self.sldtab = tables[4]
        self.segcommtab = tables[5]
        self.transtab = tables[6]
        self.segmentchangetab = tables[7]

        self.scratch = scratch

        #####################################
        #LOGGER
        self.logger = logging.getLogger('SegmentGeoprocessing')
        self.logger.setLevel(logging.DEBUG)

        # create a file handler
        filehandlerpath = os.path.join(scratch, 'SegmentGeoprocessing.log')  #os.path.join(os.path.dirname(__file__), 'SplitGeoprocessing.log')
        if os.path.exists(filehandlerpath):
            os.remove(filehandlerpath)
        self.handler = logging.FileHandler(filehandlerpath)
        self.handler.setLevel(logging.DEBUG)

        # create a logging format
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

        self.logger.info('SegmentGeoprocessing Class Called, Geoprocessing started...')
        self.logger.info('SEG_GUID: {0}'.format(self.Pre_Footprint["SEG_GUID"]))

        #self.logger.info('Pre Footprint: {0}'. format(self.Pre_Footprint))
        #self.logger.info('Post Footprint {0}'. format(self.Post_Footprint))

    def run(self):
        import arcpy, traceback, os, sys, logging

        try:
            # create sql queries
            globalsql1 = sqlGUID("GLOBALID", self.Pre_Footprint['SEGMENT'][0]['GLOBALID'])
            #self.logger.info('GLOBALID for segment 1 is {0}'. format(globalsql1))
            self.logger.info('Comparing the original values with new values')

##                for k in ['ADDR_L_FR', 'ADDR_L_TO', 'ADDR_R_FR', 'ADDR_R_TO', 'ZIPCODE_L', 'ZIPCODE_R', 'ZIPNAME_L', 'ZIPNAME_R', 'MUNI_ID_L', 'MUNI_ID_R', 'ELEV_TYPE_ID_FR', 'ELEV_TYPE_ID_TO', 'ACC_TYPE_ID', 'SURF_TYPE_ID', 'STATUS_TYPE_ID', 'SYMBOL_TYPE_ID', 'TRAVEL_DIR_TYPE_ID', 'JURIS_TYPE_ID', 'OIT_REV_TYPE_ID', 'DOT_REV_TYPE_ID']:
##                    if self.Pre_Footprint['SEGMENT'][0][k] == self.Post_Footprint['SEGMENT'][0][k]:
##                        self.logger.warning('{0}\t\tOriginal: {1} New: {2} (match, no update)'.format(k,self.Pre_Footprint['SEGMENT'][0][k],self.Post_Footprint['SEGMENT'][0][k]))
##                    else:
##                        self.logger.warning('{0}\t\tOriginal: {1} New: {2}'.format(k,self.Pre_Footprint['SEGMENT'][0][k],self.Post_Footprint['SEGMENT'][0][k]))

##
##            for k,v in self.Pre_Footprint['SEGMENT'][0].iteritems():
##                if v == self.Post_Footprint['SEGMENT'][0][k]:
##                    self.logger.warning('Original {0} value matches new value: {1}'.format(k,v)
##                else:
##                    self.logger.warning('Original {0} value: {1}  does not match new value: {2}'.format(k, v, self.Post_Footprint['SEGMENT'][0][k]))
##


            cursor = arcpy.UpdateCursor(self.segmentfc, globalsql1)
            for row in cursor:
                #row.setValue('SEG_GUID', self.seg_guid1)
                for k in ['ADDR_L_FR', 'ADDR_L_TO', 'ADDR_R_FR', 'ADDR_R_TO', 'ZIPCODE_L', 'ZIPCODE_R', 'ZIPNAME_L', 'ZIPNAME_R', 'MUNI_ID_L', 'MUNI_ID_R', 'ELEV_TYPE_ID_FR', 'ELEV_TYPE_ID_TO', 'ACC_TYPE_ID', 'SURF_TYPE_ID', 'STATUS_TYPE_ID', 'SYMBOL_TYPE_ID', 'TRAVEL_DIR_TYPE_ID', 'JURIS_TYPE_ID', 'OIT_REV_TYPE_ID', 'DOT_REV_TYPE_ID']:
                    if self.Pre_Footprint['SEGMENT'][0][k] == self.Post_Footprint['SEGMENT'][0][k]:
                        self.logger.warning('{0}\t\tOriginal: {1} New: {2} (match, no update)'.format(k,self.Pre_Footprint['SEGMENT'][0][k],self.Post_Footprint['SEGMENT'][0][k]))
                    else:
                        row.setValue(k, self.Post_Footprint['SEGMENT'][0][k])
                        self.logger.warning('{0}\t\tOriginal: {1} New: {2} (updated)'.format(k,self.Pre_Footprint['SEGMENT'][0][k],self.Post_Footprint['SEGMENT'][0][k]))


##                row.setValue('ADDR_L_FR', self.Post_Footprint['SEGMENT'][0]['ADDR_L_FR'])
##                row.setValue('ADDR_L_TO', self.Post_Footprint['SEGMENT'][0]['ADDR_L_TO'])
##                row.setValue('ADDR_R_FR', self.Post_Footprint['SEGMENT'][0]['ADDR_R_FR'])
##                row.setValue('ADDR_R_TO', self.Post_Footprint['SEGMENT'][0]['ADDR_R_TO'])
##                row.setValue('ZIPCODE_L', self.Post_Footprint['SEGMENT'][0]['ZIPCODE_L'])
##                row.setValue('ZIPCODE_R', self.Post_Footprint['SEGMENT'][0]['ZIPCODE_R'])
##                row.setValue('ZIPNAME_L', self.Post_Footprint['SEGMENT'][0]['ZIPNAME_L'])
##                row.setValue('ZIPNAME_R', self.Post_Footprint['SEGMENT'][0]['ZIPNAME_R'])
##                row.setValue('MUNI_ID_L', self.Post_Footprint['SEGMENT'][0]['MUNI_ID_L'])
##                row.setValue('MUNI_ID_R', self.Post_Footprint['SEGMENT'][0]['MUNI_ID_R'])
##                row.setValue('ELEV_TYPE_ID_FR', self.Post_Footprint['SEGMENT'][0]['ELEV_TYPE_ID_FR'])
##                row.setValue('ELEV_TYPE_ID_TO', self.Post_Footprint['SEGMENT'][0]['ELEV_TYPE_ID_TO'])
##                row.setValue('ACC_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['ACC_TYPE_ID'])
##                row.setValue('SURF_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['SURF_TYPE_ID'])
##                row.setValue('STATUS_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['STATUS_TYPE_ID'])
##                row.setValue('SYMBOL_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['SYMBOL_TYPE_ID'])
##                row.setValue('TRAVEL_DIR_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['TRAVEL_DIR_TYPE_ID'])
##                row.setValue('JURIS_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['JURIS_TYPE_ID'])
##                row.setValue('OIT_REV_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['OIT_REV_TYPE_ID'])
##                row.setValue('DOT_REV_TYPE_ID', self.Post_Footprint['SEGMENT'][0]['DOT_REV_TYPE_ID'])
                cursor.updateRow(row)
            try: del row
            except: pass
            try: del cursor
            except: pass

            self.logger.info('Segment fields updated in SEGMENT')
            self.logger.removeHandler(self.handler)
            self.logger.info('Geoprocessing Completed Successfully')
            return True

        except:
            trace = traceback.format_exc()
            self.logger.exception(trace)
            self.logger.warning('Geoprocessing Failed')
            self.logger.removeHandler(self.handler)
            try: del row
            except: pass
            try: del cursor
            except: pass
            return None, trace


if __name__ == "__main__":
    calcGUID()
    timestamp()
