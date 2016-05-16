#-------------------------------------------------------------------------------
# Name:         Roads_addin.py
# Purpose:      Python Add-In file. Includes button tools and extension.
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
import arcpy
import logging
import subprocess
import pythonaddins
import os
import socket
import pickle
import json
import traceback
os.sys.path.append(os.path.dirname(__file__))
import erebus
plist = os.sys.path
esriversion = arcpy.GetInstallInfo()['Version']
if esriversion.split('.')[1] == '2' and 'C:\\Python27\\ArcGIS10.2' not in plist:
    os.sys.path.append(r'C:\Python27\ArcGIS10.2')
    os.sys.path.append(r'C:\Python27\ArcGIS10.2\Scripts')
if esriversion.split('.')[1] == '3' and 'C:\\Python27\\ArcGIS10.3' not in plist:
    os.sys.path.append(r'C:\Python27\ArcGIS10.3')
    os.sys.path.append(r'C:\Python27\ArcGIS10.3\Scripts')
if esriversion.split('.')[1] == '2':
    pyexe = 'C:\Python27\ArcGIS10.2\python.exe'
if esriversion.split('.')[1] == '3':
    pyexe = 'C:\Python27\ArcGIS10.3\python.exe'

# check the user environment PATH.
def pathcheck(version):
    envi = dict(os.environ)
    pathlist = envi['PATH'].split(';')
    pystr = 'C:\\Python27\\ArcGIS10.{0}'.format(version.split('.')[1])
    if pystr not in pathlist:
        # add it to the path
        pass

esesh = dict(inSession=0, onStartOperation=0, onBeforStopOperation=0, onStopOperation = 0, onSaveEdits=0, onChangeFeature=0, onCreateFeature=0, onDeleteFeature=0)
monitorOp = "Empty"
lastselect = "Empty"
selectedfootprints_multiple = "Empty"
lastselect_fields = "Empty"
segmentgeo = "Empty"
INTOOL = False
tbxloc2 = os.path.dirname(__file__) + r"\NJRE.pyt"
tbx_mbi_sld_manager = os.path.dirname(__file__) + r"\SLD_Manager.pyt"

global tbxloc2
global tbx_mbi_sld_manager


segmentfc = ""; segmentchangetab = ""; transtab = ""; segnametab = ""; segshieldtab = ""; segcommtab = ""; linreftab = ""; sldtab = "";
global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab



#####################################
#LOGGER
maxLogsize = 1000000 # 1000000 bytes, 1 mb
if os.path.exists(os.path.join(arcpy.env.scratchWorkspace, 'NJRE_logger.log')):
    if os.path.getsize(os.path.join(arcpy.env.scratchWorkspace, 'NJRE_logger.log')) > maxLogsize:  # 400kb
        os.remove(os.path.join(arcpy.env.scratchWorkspace, 'NJRE_logger.log'))

if os.path.exists(os.path.join(arcpy.env.scratchWorkspace, 'TkUI.log')):
    if os.path.getsize(os.path.join(arcpy.env.scratchWorkspace, 'TkUI.log')) > maxLogsize:  # 400kb
        os.remove(os.path.join(arcpy.env.scratchWorkspace, 'TkUI.log'))

if os.path.exists(os.path.join(arcpy.env.scratchWorkspace, 'SplitGeoprocessing.log')):
    if os.path.getsize(os.path.join(arcpy.env.scratchWorkspace, 'SplitGeoprocessing.log')) > maxLogsize:  # 400kb
        os.remove(os.path.join(arcpy.env.scratchWorkspace, 'SplitGeoprocessing.log'))

if os.path.exists(os.path.join(arcpy.env.scratchWorkspace, 'SegmentGeoprocessing.log')):
    if os.path.getsize(os.path.join(arcpy.env.scratchWorkspace, 'SegmentGeoprocessing.log')) > maxLogsize:  # 400kb
        os.remove(os.path.join(arcpy.env.scratchWorkspace, 'SegmentGeoprocessing.log'))


NJRE_logger = logging.getLogger('NJRE_logger')
NJRE_logger.setLevel(logging.DEBUG)
# create a file handler
#filehandlerpath = os.path.join(arcpy.env.scratchWorkspace, 'NJRE_logger.log')#          os.path.join(arcpy.env.scratchWorkspace, 'NJRE_logger.log')

NJRE_handler = None
#NJRE_handler = logging.FileHandler(filehandlerpath)
#NJRE_handler.setLevel(logging.DEBUG)

# create a logging format
#NJRE_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#NJRE_handler.setFormatter(NJRE_formatter)

#------------------------------------------------------------------------------
# BUTTON - EDIT SEGMENT

class ButtonClass43(object):
    """Implementation for Roads_addin.buttonEditSegment (Button)"""
    def __init__(self):
        self.enabled = False
        self.checked = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
    def onClick(self):

        global tbxloc2, monitorOp,pyexe
        NJRE_logger.info('EditSegment tool called')

        try:
            count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
            if count == 1:
                INTOOL = True
                with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        segguid = row[0]

                Fp = erebus.Footprint(segguid)
                FPrint = Fp.getfootprint([segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab])  #['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']
                NJRE_logger.info('EditSegment input footprint {0}'.format(FPrint))

                # -----------------------------
                # Get the domains and dump them out as a pickle. This is necessary becuase they are too big to push through to a subprocess
                domains = arcpy.da.ListDomains(arcpy.env.workspace)
                self.Domains = {}
                roaddomains = [u'TRAVEL_DIR_TYPE', u'SURFACE_TYPE', u'SEGMENT_TYPE', u'CHANGE_TYPE', u'GNIS_NAME', u'SHIELD_SUBTYPE', u'ROUTE_TYPE', u'LRS_TYPE', u'JURIS_TYPE', u'SHIELD_TYPE', u'ACCESS_TYPE', u'DATA_SOURCE_TYPE', u'ELEV_TYPE', u'REVIEW_TYPE', u'SYMBOL_TYPE', u'NAME_TYPE', u'STATUS_TYPE']
                for domain in domains:
                    if domain.name in roaddomains:
                        self.Domains[domain.name] = domain.codedValues

                domains_path = os.path.join(arcpy.env.scratchWorkspace, "domains.p")
                if os.path.exists(domains_path):
                    os.remove(domains_path)
                with open(domains_path, 'wb') as output:
                    pickle.dump(self.Domains, output, -1)

                # -----------------------------
                # Call the EditSegment.py Tkinter UI
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                idpath = os.path.join(os.path.dirname(__file__), 'EditSegment.py')
                pipe = subprocess.Popen([pyexe, idpath, '1', arcpy.env.scratchWorkspace, str(FPrint), 'None'], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)

                (stdoutdata, stderrdata) = pipe.communicate()
                pipe.terminate()
                if stderrdata:
                    print 'stderrdata:  {0}'.format(stderrdata)
                if stdoutdata:
                    #print 'stdoutdata:  {0}\n'.format(stdoutdata)
                    #print 'stdoutdata type:  {0}'.format(type(stdoutdata))

                    Split1_result = stdoutdata.split('***')[0]; print 'Split1_result', Split1_result
                    Split1_Footprint = eval(stdoutdata.split('***')[1]) ; print 'Split1_Footprint', Split1_Footprint

                    if Split1_result == "OK":
                        NJRE_logger.info('EditNames UI Success')

                        # Make the changes in the database.
                        #segmentgeoprocessing = erebus.SegmentGeoprocessing(Split1_Footprint, Split2_Footprint, ge1, ge2, Footprint1, Footprint2, segmentgeo_copy, [segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab], arcpy.env.scratchWorkspace)

                        segmentgeoprocessing = erebus.SegmentGeoprocessing(FPrint, Split1_Footprint, [segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab], arcpy.env.scratchWorkspace)
                        seggp_result = segmentgeoprocessing.run()

                        print('segmentgeoprocessing {0}'.format(seggp_result))

                        arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                        #arcpy.SelectLayerByAttribute_management(segmentfc, 'NEW_SELECTION', globalsql2)
                        arcpy.RefreshActiveView()

                        # get the log and show the gp results
                        segmentlogpath = os.path.join(arcpy.env.scratchWorkspace, 'SegmentGeoprocessing.log')
                        if os.path.exists(segmentlogpath):
                            # read the log file and display it
                            with open(segmentlogpath, 'r') as segmentlog:
                                segmentloglines = segmentlog.readlines()

                            ########################
                            ########################
                            ########################
                            ## segment GEOPROCESSING RESULTS
                            sgppath = os.path.join(os.path.dirname(__file__), 'GpResults2.py')
                            sgppipe = subprocess.Popen(['python', sgppath, segmentlogpath], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                            (sgpstdoutdata2, sgpstderrdata2) = sgppipe.communicate()
                            sgppipe.terminate()

                        NJRE_logger.info('EditSegment tool ran')

                # -----------------------------
                # Cleanup
                arcpy.RefreshActiveView()
                INTOOL = False
                #print INTOOL
                esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
                monitorOp = "Empty"
                NJRE_logger.info('EditNames tool finished')

            else:
                pythonaddins.MessageBox('No segment, or more than one segment is selected in SEGMENT feature class. Please selected 1 segment and try again.', 'EditSegment Error', 0)
                NJRE_logger.warning('EditSegment tool failed. No segment, or more than one segment is selected in SEGMENT feature class. User received message box.')


        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Edit Segment tool failed with exception')
            NJRE_logger.exception(trace)

#------------------------------------------------------------------------------
# BUTTON - DELETE

class ButtonClass10(object):
    """Implementation for Roads_addin.buttonDel (Button)"""
    def __init__(self):
        self.enabled = False
        self.checked = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
    def onClick(self):
        global INTOOL, esesh, monitorOp
        NJRE_logger.info('Delete tool called')
        INTOOL = True
        try:
            count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
            if count == 1:
                global tbxloc2, monitorOp
                with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        segguid = row[0]
                if segguid:
                    seg_sql = erebus.sqlGUID("SEG_GUID", segguid)
                    delete_pickle = [segguid, seg_sql]
                    # Dump out the pickle
                    deletepath = arcpy.env.scratchWorkspace + "\\deleteselection.p"
                    if os.path.exists(deletepath):
                        os.remove(deletepath)
                    with open(deletepath, 'wb') as output:
                        pickle.dump(delete_pickle, output, -1)
                    # Launch the tool
                    pythonaddins.GPToolDialog(tbxloc2, "Delete")
                    arcpy.RefreshActiveView()
                    esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
                    monitorOp = "Empty"
                    NJRE_logger.info('Delete tool ran. {0}'.format(seg_sql))
                if not segguid:
                    pythonaddins.MessageBox('The segment you selected does not have a SEG_GUID, so you cannot delete it with the NJRE Delete tool. Please try an alternate method to delete this segment.', 'Delete Error', 0)
                    NJRE_logger.warning('Delete tool failed. Segment has no SEG_GUID. User received message box.')
            else:
                pythonaddins.MessageBox('No segment, or more than one segment is selected in SEGMENT feature class. Please selected 1 segment and try again.', 'Delete Error', 0)
                NJRE_logger.warning('Delete tool failed. No segment, or more than one segment is selected in SEGMENT feature class. User received message box.')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Delete tool failed with exception')
            NJRE_logger.exception(trace)
        finally:
            arcpy.RefreshActiveView()
            print 'delete finally: {0}'.format(INTOOL)
            INTOOL = False
            print 'delete finally after: {0}'.format(INTOOL)

#------------------------------------------------------------------------------
# BUTTON - EDIT NAMES
class ButtonClass8(object):
    """Implementation for Roads_addin.buttonAddName (Button)"""
    def __init__(self):
        self.enabled = False
        self.checked = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
    def onClick(self):
        NJRE_logger.info('Edit Names tool called')
        try:
            count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
            if count == 1: # only launch if there is 1 segment selected
                global tbxloc2, monitorOp
                INTOOL = True
                print 'monitorOp is: {0}'.format(monitorOp)
                Records = []
                RecordsDict = {}
                with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID", "SYMBOL_TYPE_ID"]) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        segguid = row[0]
                        symboltype = row[1]
                if segguid and symboltype:
                    if symboltype in (108,208,308,408,508,608,708,808,908):
                        pythonaddins.MessageBox('The segment you selected is a ramp. Ramps are not allowed to have names.', 'EditNames Error', 0)
                    else:
                        seg_sql = erebus.sqlGUID("SEG_GUID", segguid)
                        gg = 1
                        with arcpy.da.SearchCursor(segnametab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                            for row in cursor:
                                if row[3] == 'H':
                                    shieldvars = []
                                    with arcpy.da.SearchCursor(segshieldtab, ["RANK", "SHIELD_TYPE_ID", "SHIELD_SUBTYPE_ID", "SHIELD_NAME", "GLOBALID"], seg_sql) as cursor2:
                                        for row2 in cursor2:
                                            if row[4] == row2[0]:
                                                shieldvars = row2
                                    if shieldvars:
                                        Records.append(['Record {0}'.format(gg),row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], shieldvars[1], shieldvars[2], shieldvars[3]])
                                        RecordsDict['Record {0}'.format(gg)] = [row[16],shieldvars[4]]
                                    else:
                                        Records.append(['Record {0}'.format(gg),row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], "", "", ""])
                                        RecordsDict['Record {0}'.format(gg)] = [row[16],""]
                                if row[3] == 'L':
                                    Records.append(['Record {0}'.format(gg),row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], "", "", ""])
                                    RecordsDict['Record {0}'.format(gg)] = [row[16],""]
                                gg += 1
                        editnames_pickle = {'segment': (True, Records, RecordsDict), 'segmentlocked': False, 'UPDATECOUNT': 0, 'ID': erebus.calcGUID(), 'segguid': segguid}
                        # Dump out the pickle
                        editnamespath = arcpy.env.scratchWorkspace + "\\editnamesselection.p"
                        if os.path.exists(editnamespath):
                            os.remove(editnamespath)
                        with open(editnamespath, 'wb') as output:
                            pickle.dump(editnames_pickle, output, -1)
                        # Launch the tool
                        pythonaddins.GPToolDialog(tbxloc2, "EditNames")
                        INTOOL = False
                        if os.path.exists(editnamespath):
                            os.remove(editnamespath)
                        esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
                        monitorOp = "Empty"
                        NJRE_logger.info('Edit Names tool ran. {0}'.format(seg_sql))
                if not segguid:
                    pythonaddins.MessageBox('The segment you selected does not have a SEG_GUID, so you cannot use the NJRE EditNames tool.', 'EditNames Error', 0)
                    NJRE_logger.warning('Edit Names tool failed. Segment has no SEG_GUID. User received message box.')
            else:
                pythonaddins.MessageBox('No segment, or more than one segment is selected in SEGMENT feature class. Please selected 1 segment and try again.', 'AddName Error', 0)
                NJRE_logger.warning('Edit Names tool failed. No segment, or more than one segment is selected in SEGMENT feature class. User received message box.')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Edit Names tool failed with exception')
            NJRE_logger.exception(trace)

#------------------------------------------------------------------------------
# BUTTON - LRS

class ButtonClass9(object):
    """Implementation for Roads_addin.buttonLRS (Button)"""
    def __init__(self):
        self.enabled = False
        self.checked = False
        global esesh
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
    def onClick(self):
        global tbxloc2, monitorOp
        NJRE_logger.info('LRS tool called')
        try:
            count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
            if count == 1: # only launch if there is 1 segment selected
                INTOOL = True
                print 'monitorOp is: {0}'.format(monitorOp)
                # get the segguid and dump it out for the tool
                with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        segguid = row[0]
                if segguid:
                    seg_sql = erebus.sqlGUID("SEG_GUID", segguid)
                    lrs_pickle = {'segment': (True, segguid), 'linreftab': (False,), 'sldtab': (False,), 'lrslocked': False, 'sldlocked': False, 'UPDATECOUNT': 0, 'ID': erebus.calcGUID()}   #lrs_pickle['UPDATECOUNT']
                    Records = []
                    RecordsDict = {}
                    Records_sld = []
                    RecordsDict_sld = {}
                    sri = []
                    srilist = []
                    gg = 1
                    with arcpy.da.SearchCursor(linreftab, ["SEG_GUID", "SRI", "LRS_TYPE_ID", "SEG_TYPE_ID", "MILEPOST_FR", "MILEPOST_TO", "RCF","GLOBALID"], seg_sql) as cursor:
                        for row in cursor:
                            Records.append(['Record {0}'.format(gg),row[0], row[1], row[2], row[3], row[4], row[5], row[6]])
                            RecordsDict['Record {0}'.format(gg)] = [row[7],""]
                            if row[1]:
                                srilist.append(row[1])
                            gg += 1
                    if Records:
                        lrs_pickle['linreftab'] = (True, Records, RecordsDict)
                    if srilist:
                        [sri.append(item) for item in srilist if item not in sri]  #remove duplicates
                        gg = 1
                        for i,v in enumerate(sri):
                            sri_sql = erebus.sqlGUID("SRI", v) #  0           1             2            3               4               5           6
                            with arcpy.da.SearchCursor(sldtab, ["SRI", "ROUTE_TYPE_ID", "SLD_NAME", "SLD_COMMENT", "SLD_DIRECTION", "SIGN_NAME","GLOBALID"], sri_sql) as cursor2:
                                for row2 in cursor2:
                                    Records_sld.append(['Record {0}'.format(gg),row2[0], row2[1], row2[2], row2[3], row2[4], row2[5]])
                                    RecordsDict_sld['Record {0}'.format(gg)] = [row2[6],""]
                            gg += 1
                    if Records_sld:
                        lrs_pickle['sldtab'] = (True, Records_sld, RecordsDict_sld)
                    # Dump out the pickle
                    lrspath = arcpy.env.scratchWorkspace + "\\lrsselection.p"
                    if os.path.exists(lrspath):
                        os.remove(lrspath)
                    with open(lrspath, 'wb') as output:
                        pickle.dump(lrs_pickle, output, -1)
                    # Launch the tool
                    pythonaddins.GPToolDialog(tbxloc2, "LRS")
                    INTOOL = False
                    NJRE_logger.info('LRS tool ran. {0}'.format(seg_sql))
                if not segguid:
                    pythonaddins.MessageBox('The segment you selected does not have a SEG_GUID, so you cannot use the LRS tool.', 'LRS Error', 0)
                    NJRE_logger.warning('LRS tool failed. Segment has no SEG_GUID. User received message box.')
            else:
                pythonaddins.MessageBox('No segment, or more than one segment is selected in SEGMENT feature class. Please selected 1 segment and try again.', 'BuildName Error', 0)
                NJRE_logger.warning('LRS tool failed. No segment, or more than one segment is selected in SEGMENT feature class. User received message box.')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('LRS tool failed with exception')
            NJRE_logger.exception(trace)

#------------------------------------------------------------------------------
# BUTTON - BatchBuildName
class ButtonClass13(object):
    """Implementation for Roads_addin.buttonBatchBuildName (Button)"""
    def __init__(self):
        if socket.gethostname()[0:3] == 'OIT':
            self.enabled = True
        else:
            self.enabled = False
        self.checked = False
        global esesh
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
    def onClick(self):
        global tbxloc2, monitorOp
        NJRE_logger.info('Batch Build Name tool called')
        try:
            INTOOL = True
            print 'monitorOp is: {0}'.format(monitorOp)
            pythonaddins.GPToolDialog(tbxloc2, "BatchBuildName")
            INTOOL = False
            esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
            monitorOp = "Empty"
            NJRE_logger.info('Batch Build Name tool ran.')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Batch Build Name tool failed with exception')
            NJRE_logger.exception(trace)
#------------------------------------------------------------------------------
# BUTTON - BatchPost

class ButtonClass73(object):
    """Implementation for Roads_addin.buttonBatchPost (Button)"""
    def __init__(self):
        if socket.gethostname()[0:3] == 'OIT':
            self.enabled = True
        else:
            self.enabled = False
        self.checked = False
        global esesh
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
    def onClick(self):
        global tbxloc2, monitorOp
        NJRE_logger.info('Batch Post tool called')
        try:
            INTOOL = True
            print 'monitorOp is: {0}'.format(monitorOp)
            pythonaddins.GPToolDialog(tbxloc2, "BatchPost")
            INTOOL = False
            esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
            monitorOp = "Empty"
            NJRE_logger.info('Batch Post tool ran.')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Batch Post tool failed with exception')
            NJRE_logger.exception(trace)
#------------------------------------------------------------------------------
# Tool - Identify (Depracated)
class ButtonClass33(object):
    """Implementation for Roads_addin.buttonIdentify (Button)"""
    def __init__(self):
        self.enabled = False
        self.checked = False
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger
        global esesh
    def onClick(self):
        import traceback, os
        import sys, subprocess
        os.sys.path.append(os.path.dirname(__file__))
        import erebus
        global tbxloc2, monitorOp
        NJRE_logger.info('Identify tool called')
        try:
            count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
            if count == 1: # only launch if there is 1 segment selected
                ####################################################################
                # GEt the SEG_GUID of the selected feature
                with arcpy.da.SearchCursor(segmentfc, ["SEG_GUID"]) as cursor:  # insert a cursor to access fields, print names
                    for row in cursor:
                        segguid = row[0]
                if segguid:
                    seg_sql = erebus.sqlGUID("SEG_GUID", segguid)
                    ####################################################################
                    segment_current = []  # this will be a list of tuples with current records
                    with arcpy.da.SearchCursor(segmentfc, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            segment_current.append(zip(cursor.fields,row))

                    segname_current = []  # this will be a list of tuples with current records
                    with arcpy.da.SearchCursor(segnametab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            segname_current.append(zip(cursor.fields,row))

                    segshield_current = [] # this will be a list of tuples with current records
                    with arcpy.da.SearchCursor(segshieldtab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            segshield_current.append(zip(cursor.fields,row))
                    lr_current = []  # this will be a list of tuples with current records
                    sris = []
                    with arcpy.da.SearchCursor(linreftab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            lr_current.append(zip(cursor.fields,row))
                            if row[3]:
                                if len(sris) == 0:
                                    sris.append(row[3])
                                if len(sris) == 1:
                                    if sris[0] != row[3]:
                                        sris.append(row[3])
                    sld_current = [] # this will be a list of tuples with current records
                    try:
                        for sri in sris:
                            sri_sql = erebus.sqlGUID("SRI", sri)
                            with arcpy.da.SearchCursor(sldtab, "*", sri_sql) as cursor:  # insert a cursor to access fields, print names
                                for row in cursor:
                                    sld_current.append(zip(cursor.fields,row))
                    except:
                        trace = traceback.format_exc()
                        NJRE_logger.error('Identify tool failed with exception')
                        NJRE_logger.exception(trace)

                    comm_current = [] # this will be a list of tuples with current records
                    with arcpy.da.SearchCursor(segcommtab, "*", seg_sql) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            comm_current.append(zip(cursor.fields,row))

                    segment_trans = []  # this will be a list of tuples with current records
                    seg_sql_new = erebus.sqlGUID("SEG_GUID_NEW", segguid)
                    with arcpy.da.SearchCursor(transtab, "*", seg_sql_new) as cursor:  # insert a cursor to access fields, print names
                        for row in cursor:
                            st_dictiter = {}
                            for i,field in enumerate(cursor.fields):
                                st_dictiter[field] = row[i]
                            segment_trans.append(zip(cursor.fields,row))

                    segchange_current = []
                    if segment_trans:
                        for st in segment_trans:
                            seg_sql_arch = erebus.sqlGUID("SEG_GUID_ARCH", st[2][1])
                            with arcpy.da.SearchCursor(segmentchangetab, "*", seg_sql_arch) as cursor:
                                for row in cursor:
                                    segchange_current.append(zip(cursor.fields,row))
                    Records = {}  # a dictionary of lists of tuples
                    Records['SEGMENT'] = segment_current
                    Records['SEG_NAME'] = segname_current
                    Records['SEG_SHIELD'] = segshield_current
                    Records['LINEAR_REF'] = lr_current
                    Records['SLD_ROUTE'] = sld_current
                    Records['SEGMENT_COMMENTS'] = comm_current
                    Records['SEGMENT_TRANS'] = segment_trans
                    Records['SEGMENT_CHANGE'] = segchange_current
                    #print Records
                    ####################################################################
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    idpath = os.path.join(os.path.dirname(__file__), 'Identify.py')
                    pipe = subprocess.Popen(['python', idpath, str(Records)], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                    NJRE_logger.info('Identify tool ran. {0}'.format(seg_sql))

                if not segguid:
                    pythonaddins.MessageBox('The segment you selected does not have a SEG_GUID, so you cannot use the NJRE Identify tool.', 'Identify Error', 0)
                    NJRE_logger.warning('Identify tool failed. Segment has no SEG_GUID. User received message box.')
            else:
                pythonaddins.MessageBox('No segment, or more than one segment is selected in SEGMENT feature class. Please selected 1 segment and try again.', 'BuildName Error', 0)
                NJRE_logger.warning('Identify tool failed. No segment, or more than one segment is selected in SEGMENT feature class. User received message box.')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Identify tool failed with exception')
            NJRE_logger.exception(trace)

#------------------------------------------------------------------------------
# BUTTON - About
class ButtonClass32(object):
    """Implementation for Roads_addin.buttonAbout (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
        global NJRE_logger
    def onClick(self):
        pythonaddins.MessageBox('New Jersey Road Editor Add-In\n\nType:  \tPython Add-In, Extension, Toolbar\nVersion:  \t3.1.0\nAuthor:  \tNJ Office of GIS,   njgin@oit.state.nj.us\nDepends:  \tPython 2.7.8+ (32 bit), ESRI ArcGIS Desktop 10.3.1\nLicense:  \tGPLv3', 'About NJ Road Editor Python Add-In', 0)

#------------------------------------------------------------------------------
# BUTTON - NJRE Manual
class ButtonClass332(object):
    """Implementation for Roads_addin.buttonDocumentation (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
        global NJRE_logger
    def onClick(self):
        import os
        NJRE_logger.info('Documentation tool called')
        try:
            pdfpath = os.path.join(os.path.dirname(__file__),'NJRoadEditorManual.pdf')
            os.startfile(pdfpath)
            NJRE_logger.info('Documentation tool ran')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Documentation tool failed with exception')
            NJRE_logger.exception(trace)

#------------------------------------------------------------------------------
# BUTTON - Road Data Model
class ButtonClass337(object):
    """Implementation for Roads_addin.buttonDataModel (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
        global NJRE_logger
    def onClick(self):
        import os
        NJRE_logger.info('Data Model tool called')
        try:
            pdfpath = os.path.join(os.path.dirname(__file__),'Centerline_Maintenance_Model.pdf')
            os.startfile(pdfpath)
            NJRE_logger.info('Data Model tool ran')
        except:
            trace = traceback.format_exc()
            NJRE_logger.error('Data Model tool failed with exception')
            NJRE_logger.exception(trace)


#------------------------------------------------------------------------------
# BUTTON - Michael Baker International - Global SRI Change
class ButtonClass701(object):
    """Implementation for Roads_addin.button_mbi_ChangeSRI"""
    def __init__(self):
        self.enabled = False
        self.checked = False
        # global NJRE_logger - consider using existing logging functionality?

    def onClick(self):
        global tbx_mbi_sld_manager
        try:
            pythonaddins.GPToolDialog(tbx_mbi_sld_manager, "ChangeSRI")
            # arcpy.RefreshActiveView()
        except Exception as ex:
            trace = traceback.format_exc()
            print trace
            print "error:" + ex.message
            # arcpy.AddMessage("something went wrong." + ex.message)

class ButtonClass702(object):
    """Implementation for Roads_addin.button_mbi_RemilepostRoute"""
    def __init__(self):
        self.enabled = False
        self.checked = False

    def onClick(self):
        global tbx_mbi_sld_manager
        try:
            pythonaddins.GPToolDialog(tbx_mbi_sld_manager, "RemilepostRoute")
            # arcpy.RefreshActiveView()
        except Exception as ex:
            trace = traceback.format_exc()
            print trace
            print "error:" + ex.message
            # arcpy.AddMessage("something went wrong." + ex.message)


#------------------------------------------------------------------------------
# EXTENSION - NJ ROAD EDITOR EXTENSION
class ExtensionClass1(object):
    """Implementation for Roads_addin.extension1 (Extension)"""
    def __init__(self):
        # For performance considerations, please remove all unused methods in this class.
        self.enabled = True
        global esesh, monitorOp, lastselect, lastselect_fields, INTOOL, selectedfootprints_multiple
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger

        self.NJRE_Env = False
        def get_tool_indicator():
            tool_indicator_path = os.path.join(arcpy.env.scratchWorkspace, 'tool_indicator.p')
            tool_indicator = False
            if os.path.exists(tool_indicator_path):
                with open(tool_indicator_path,'rb') as toolindopen:
                    tool_indicator = pickle.load(toolindopen)
            return tool_indicator
        def getlongnames(workspace, names):
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
        self.gln = getlongnames
        self.get_tool_indicator = get_tool_indicator
    def startup(self):
        pass
    def activeViewChanged(self):
        pass
    def mapsChanged(self):
        pass
    def newDocument(self):
        pass
    def openDocument(self):
        pass
    def beforeCloseDocument(self):
        pass
    def closeDocument(self):
        global NJRE_logger, NJRE_handler
        try:
            NJRE_logger.removeHandler(NJRE_handler)
        except:
            pass
    def beforePageIndexExtentChange(self, old_id):
        pass
    def pageIndexExtentChanged(self, new_id):
        pass
    def contentsChanged(self):
        pass
    def spatialReferenceChanged(self):
        pass
    def itemAdded(self, new_item):
        pass
    def itemDeleted(self, deleted_item):
        pass
    def itemReordered(self, reordered_item, new_index):
        pass
    def onEditorSelectionChanged(self):
        # Endpoint: NewFeature, DeleteFeature,
        print "onEditorSelectionChanged"
        #print esesh
        global monitorOp, esesh, INTOOL, lastselect, lastselect_fields, lastselect_multiple, segmentgeo, segmentgeo_multiple, NJRE_logger, selectedfootprints_multiple, pyexe
        print monitorOp
        import erebus

        if self.NJRE_Env:
            # Grab the last selected segment (only one segment)
            try:
                with arcpy.da.SearchCursor(segmentfc, "*") as cursor:  # insert a cursor to access fields, print names
                    ii = 0
                    for row in cursor:
                        segselect = row
                        segselect_fields = cursor.fields
                        ii += 1
                        if ii > 1:
                            break
                with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"]) as geocursor:  # get the geometry object
                    ii = 0
                    for geo in geocursor:
                        geoobject = geo
                        ii += 1
                        if ii > 1:
                            break
                if ii == 1:
                    dictiter = {}
                    for i,field in enumerate(segselect_fields):
                        dictiter[field] = segselect[i]

                    if "SEG_GUID" in dictiter.keys():
                        #print 'dictiter %s' % type(dictiter['SEG_GUID'])
                        if dictiter["SEG_GUID"] is not None:
                            Fp = erebus.Footprint(dictiter["SEG_GUID"])
                            lastselect = Fp.getfootprint([segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab])  #['SEGMENT', 'SEG_NAME', 'SEG_SHIELD', 'LINEAR_REF', 'SLD_ROUTE', 'SEGMENT_COMMENTS', 'SEGMENT_TRANS', 'SEGMENT_CHANGE']
                        else:
                            lastselect = {'SEGMENT': [dictiter]}
                    else:
                        lastselect = {'SEGMENT': [dictiter]}
                    for g in geoobject:
                        segmentgeo = g
            except:
                print(traceback.format_exc())
                trace = traceback.format_exc()
                NJRE_logger.error('Last selected segment tool failed with exception')
                NJRE_logger.exception(trace)
            # Grab the last mulitple selection (this maxes out at 10)
            try:
                selectedrows = []; selectedgeo = []; selectedfootprints = [];
                maxselect = 10
                with arcpy.da.SearchCursor(segmentfc, "*") as cursor:  # insert a cursor to access fields, print names
                    jj = 0
                    segselect_fields = cursor.fields
                    for row in cursor:
                        selectedrows.append(row)
                        dictiter = {}
                        for i,field in enumerate(segselect_fields):
                            dictiter[field] = row[i]
                        if "SEG_GUID" in dictiter.keys():
                            Fp = erebus.Footprint(dictiter["SEG_GUID"])
                            selectedfootprints.append(Fp.getfootprint([segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab]))
                        jj += 1
                        if jj > maxselect:
                            break
                with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"]) as geocursor:  # get the geometry object
                    jj = 0
                    for geo in geocursor:
                        selectedgeo.append(geo[0])
                        jj += 1
                        if jj > maxselect:
                            break
                if jj > 1 and jj <= maxselect:
                    lastselect_multiple = selectedrows
                    segmentgeo_multiple = selectedgeo
                    selectedfootprints_multiple = selectedfootprints
                try:
                    multipleselectlength = len(lastselect_multiple)
                except:
                    multipleselectlength = False
            except:
                trace = traceback.format_exc()
                print(trace)
                NJRE_logger.error('Last selected multiple segment tool failed with exception')
                NJRE_logger.exception(trace)

        ########################################################################
        ########################################################################
        # Endpoint for NewSegment
        if monitorOp == "1010" and self.NJRE_Env:
            NJRE_logger.info('New Segment endpoint')
            try:
                newsegmentpath = arcpy.env.scratchWorkspace + "\\newsegmentselection.p"
                with open(newsegmentpath, 'wb') as output:
                    pickle.dump([lastselect, segmentgeo], output, -1) # outputs the row from the last selected segment, and ["SHAPE@"]
                INTOOL = True
                NJRE_logger.info('New Segment tool called')
                pythonaddins.GPToolDialog(tbxloc2, "NewSegment") # launch the NewSegment script tool
                INTOOL = False
                esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
                monitorOp = "Empty"
                # clear the selected feature
                try:
                    arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                except:
                    print 'Failed to clear selected feature of segmentfc'
                NJRE_logger.info('New Segment tool ran')
            except:
                trace = traceback.format_exc()
                NJRE_logger.error('New Segment tool failed with exception')
                pythonaddins.MessageBox('The NJRE Python Add-In New Segment tool failed due to an error. Please email the "NJRE_logger.log" log file (in your scratch workspace) to njgin@oit.state.nj.us\n\n\n{0}'.format(trace), 'New Segment Error', 0)
                NJRE_logger.exception(trace)

        ########################################################################
        ########################################################################
        if monitorOp == "1101" and self.NJRE_Env: # merge endpoint
            NJRE_logger.info('Merge endpoint')
            try:
                contin = True
                if multipleselectlength > 2:  #multipleselectlength >= maxselect how it used to be for multiple features.
                    selecterror = pythonaddins.MessageBox('You have selcted more than 2 features to merge. The NJ Road Editor Add-In does not support this operation.\n\n Please "undo" the merge and try again. ', 'Merge Error', 0)
                    esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                    monitorOp = "Empty"
                    contin = False
                if multipleselectlength == 0:  #multipleselectlength >= maxselect how it used to be for multiple features.
                    esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                    monitorOp = "Empty"
                    contin = False
                if contin == True:
                    # What mode would you like to run in? Cleanup or Standard?
                    # Pickling an arcpy Polyline object strips out the "curvePaths" key. To avoid this lets export as WKT with the curve vertices (all of them)
                    # convert the wkt to esrijson

                    segmentgeo_multiple2 = []
                    for g in segmentgeo_multiple:
                        segmentgeo_multiple2.append(str(g.WKT))
                    segmentgeo_multiple = segmentgeo_multiple2

                    splitpath = arcpy.env.scratchWorkspace + "\\mergeselection_multiple.p"
                    with open(splitpath, 'wb') as output:
                        pickle.dump([lastselect_multiple, segmentgeo_multiple, selectedfootprints_multiple], output, -1) # outputs the row from the last selected segment, and ["SHAPE@"]
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    idpath = os.path.join(os.path.dirname(__file__), 'mergeOptions.py')
                    pipe = subprocess.Popen([pyexe, idpath], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                    (stdoutdata, stderrdata) = pipe.communicate()
                    pipe.terminate()
                    if stderrdata:
                            print 'stderrdata:  {0}'.format(stderrdata)
                    if stdoutdata:
                            mergemode = stdoutdata.split('***')[0]

                    if mergemode == "Cleanup":
                        INTOOL = True
                        NJRE_logger.info('Merge Cleanup tool called on {0} and {1}'.format(erebus.sqlGUID("SEG_GUID", lastselect_multiple[0][2]), erebus.sqlGUID("SEG_GUID", lastselect_multiple[1][2])))
                        pythonaddins.GPToolDialog(tbxloc2, "MergeCleanup")  # launch the Merge script tool
                        INTOOL = False
                        esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                        monitorOp = "Empty"
                        # clear the selected feature
                        try:
                            arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                        except:
                            print 'Failed to clear selected feature of segmentfc'
                    if mergemode == "Merge":
                        INTOOL = True
                        NJRE_logger.info('Merge tool called on {0} and {1}'.format(erebus.sqlGUID("SEG_GUID", lastselect_multiple[0][2]), erebus.sqlGUID("SEG_GUID", lastselect_multiple[1][2])))
                        pythonaddins.GPToolDialog(tbxloc2, "Merge")  # launch the Merge script tool
                        INTOOL = False
                        esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                        monitorOp = "Empty"
                        # clear the selected feature
                        try:
                            arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                        except:
                            print 'Failed to clear selected feature of segmentfc'
                    if mergemode == "Cancel":
                        INTOOL = False
                        esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                        monitorOp = "Empty"
                NJRE_logger.info('Merge tool ran')
            except:
                trace = traceback.format_exc()
                NJRE_logger.error('Merge tool failed with exception')
                pythonaddins.MessageBox('The NJRE Python Add-In Merge tool failed to due to an error. Please email the "NJRE_logger.log" log file (in your scratch workspace) to njgin@oit.state.nj.us\n\n\n{0}'.format(trace), 'Merge Error', 0)
                NJRE_logger.exception(trace)

    def onCurrentLayerChanged(self):
        pass
    def onCurrentTaskChanged(self):
        pass
    def onStartEditing(self):
        ########################################################################
        ## Define the user schema tables and layers.
        global segmentfc, segmentchangetab, transtab, segnametab, segshieldtab, segcommtab, linreftab, sldtab, NJRE_logger, NJRE_handler, pyexe
        import subprocess, sys, os
        global INTOOL, esesh, monitorOp

        filehandlerpath = os.path.join(arcpy.env.scratchWorkspace, 'NJRE_logger.log')
        NJRE_handler = logging.FileHandler(filehandlerpath)
        NJRE_logger.addHandler(NJRE_handler)
        NJRE_handler.setLevel(logging.DEBUG)

        # create a logging format
        NJRE_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        NJRE_handler.setFormatter(NJRE_formatter)

        try:

            longnames = self.gln(arcpy.env.workspace, ["SEGMENT", "SEGMENT_CHANGE", "SEGMENT_TRANS", "SEG_NAME", "SEG_SHIELD", "SEGMENT_COMMENTS", "LINEAR_REF", "SLD_ROUTE"])
            missing = [False,False,False,False,False,False,False,False]
            segmentfc = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT"], "Layer")
            if segmentfc == None:
                missing[0] = True
            segmentchangetab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_CHANGE"], "Layer")
            if segmentchangetab == None:
                missing[1] = True
            transtab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_TRANS"], "Table")
            if transtab == None:
                missing[2] = True
            segnametab = erebus.getlongname(arcpy.env.workspace, longnames["SEG_NAME"], "Table")
            if segnametab == None:
                missing[3] = True
            segshieldtab = erebus.getlongname(arcpy.env.workspace, longnames["SEG_SHIELD"], "Table")
            if segshieldtab == None:
                missing[4] = True
            segcommtab = erebus.getlongname(arcpy.env.workspace, longnames["SEGMENT_COMMENTS"], "Table")
            if segcommtab == None:
                missing[5] = True
            linreftab = erebus.getlongname(arcpy.env.workspace, longnames["LINEAR_REF"], "Table")
            if linreftab == None:
                missing[6] = True
            sldtab = erebus.getlongname(arcpy.env.workspace, longnames["SLD_ROUTE"], "Table")
            if sldtab == None:
                missing[7] = True
            realnames = ["SEGMENT", "SEGMENT_CHANGE", "SEGMENT_TRANS", "SEG_NAME", "SEG_SHIELD", "SEGMENT_COMMENTS", "LINEAR_REF", "SLD_ROUTE"]

            misslist = []
            i = 0
            for miss in missing:
                if miss:
                    misslist.append(realnames[i])
                i += 1

            if misslist:
                self.NJRE_Env = False
                NJRE_logger.warning('NJRE Python Add-In edit session error. Missing fearure classes or tables. User received message box.')
                pythonaddins.MessageBox('Missing these feature classes or tables: {0}\n\nStop Editing, add the missing layers, and start editing again.'.format(misslist),'Missing Table/Layer Error',0)

            # Check the user and set the njre_config.p file
            user_config = False
            njre_config_path = os.path.join(os.path.dirname(__file__), 'njre_config.p')
            if os.path.exists(njre_config_path):
                with open(njre_config_path,'rb') as njreconfig:
                    USER = pickle.load(njreconfig)
                user_config = True
            else:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                userRadioPath = os.path.join(os.path.dirname(__file__), 'userRadio.py')
                NJRE_logger.info('userRadio UI Called')
                NJRE_logger.info('userRadio path {0}'.format(userRadioPath))



                try:


                    pipe = subprocess.Popen([pyexe, userRadioPath], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                    (stdoutdata, stderrdata) = pipe.communicate()
                    pipe.terminate()
                    if stderrdata:
                        NJRE_logger.exception(stderrdata)
                        USER = 'Other'
                        with open(njre_config_path, 'wb') as output:
                            pickle.dump(USER, output, -1)
                        user_config = True
                        pythonaddins.MessageBox('There was an error with the NJRE Python Add-In while selecting the user type. By default, your user type will be set to "Other". You can still use the Add-In, but your REVIEW_TYPE fields will not be autopopulated. Please email the "NJRE_logger.log" log file (in your scratch workspace) to njgin@oit.nj.gov', 'User Selection Error', 0)
                    if stdoutdata:
                        userchoice = stdoutdata.split('***')
                        if userchoice[0] == 'OK':
                            if userchoice[1] in ['NJ OIT', 'NJ DOT', 'County', 'Other']:
                                NJRE_logger.info('userRadio UI selection was: {0}'.format(userchoice[1]))
                                USER = userchoice[1]
                                print("User Choice: {0}".format(USER))
                                # save the picklefile
                                with open(njre_config_path, 'wb') as output:
                                    pickle.dump(USER, output, -1)
                                user_config = True
                except WindowsError as e:
                    USER = 'Other'
                    with open(njre_config_path, 'wb') as output:
                        pickle.dump(USER, output, -1)
                    user_config = True
                    NJRE_logger.error('userRadio.py call failed with error.Python Path:{0}'.format(sys.path.__str__()))
                    NJRE_logger.error('userRadio.py call failed with error.Python Traceback:{0}'.format(traceback.format_exc()))
                    pythonaddins.MessageBox('There was an error with the NJRE Python Add-In while selecting the user type. By default, your user type will be set to "Other". You can still use the Add-In, but your REVIEW_TYPE fields will not be autopopulated. Please email the "NJRE_logger.log" log file (in your scratch workspace) to njgin@oit.nj.gov', 'User Selection Error', 0)


            if not misslist and user_config:
                #pythonaddins.MessageBox('onStartEditing', 'INFO', 0)
                esesh['inSession'] = 1; esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                buttonEditSegment.enabled = True
                buttonDel.enabled = True
                buttonAddName.enabled = True
                buttonLRS.enabled = True
                #buttonIdentify.enabled = 
                
                # mbi buttons
                buttonChangeSRI.enabled = True
                buttonRemilepostRoute.enabled = True
                
                self.NJRE_Env = True

                domains = arcpy.da.ListDomains(arcpy.env.workspace)
                self.Domains = {}
                roaddomains = [u'TRAVEL_DIR_TYPE', u'SURFACE_TYPE', u'SEGMENT_TYPE', u'CHANGE_TYPE', u'GNIS_NAME', u'SHIELD_SUBTYPE', u'ROUTE_TYPE', u'LRS_TYPE', u'JURIS_TYPE', u'SHIELD_TYPE', u'ACCESS_TYPE', u'DATA_SOURCE_TYPE', u'ELEV_TYPE', u'REVIEW_TYPE', u'SYMBOL_TYPE', u'NAME_TYPE', u'STATUS_TYPE']
                for domain in domains:
                    if domain.name in roaddomains:
                        self.Domains[domain.name] = domain.codedValues

                # Clean up the pickled objects in the scratch workspace...
                picklepaths = [arcpy.env.scratchWorkspace + "\\splitselection.p", arcpy.env.scratchWorkspace + "\\global1global2.p", arcpy.env.scratchWorkspace + "\\splitgeometries.p", arcpy.env.scratchWorkspace + "\\splitselectionvariables.p", arcpy.env.scratchWorkspace + "\\splitselection_multiple.p", arcpy.env.scratchWorkspace + "\\newsegmentselection.p"]
                pickleexist = [x for x in picklepaths if os.path.exists(x)]
                for p in pickleexist:
                    if p:
                        os.remove(p)

                NJRE_logger.info('------------------------------------------------------------------------------------')
                NJRE_logger.info('NJRE Python Add-In edit session started successfully. USER is: {0}'.format(USER))

            workspace_type = arcpy.env.workspace.split(".")[-1]
            if workspace_type == "gdb":
                NJRE_logger.info('NJRE Python Add-In edit session using a file geodatabase. User received message box.')
                pythonaddins.MessageBox('You are using a file geodatabase to edit the road centerlines maintenance database. Please do not have any other road centerlines file geodatabases present in the table of contents. If edits are made with multiple file geodatabases present, unexpected behavior with the NJRE Add-In may occur.','NJRE Addin File Geodatabase Message',0)

        except:
            trace = traceback.format_exc()
            NJRE_logger.error('NJRE Python Add-In Edit session failed with exception')
            NJRE_logger.exception(trace)
            self.NJRE_Env = False



    def onStopEditing(self, save_changes):
        global NJRE_logger, NJRE_handler
        global INTOOL, esesh, monitorOp
        #pythonaddins.MessageBox('onStopEditing', 'INFO', 0)
        esesh['inSession'] = 0; esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
        monitorOp = "Empty"
        buttonEditSegment.enabled = False
        buttonDel.enabled = False
        buttonAddName.enabled = False
        buttonLRS.enabled = False
        #buttonIdentify.enabled = False
        
        # mbi buttons disable
        buttonChangeSRI.enabled = False
        buttonRemilepostRoute.enabled = False
        
        #buttonBatchBuildName.enabled = False

        # Clean up the pickled objects in the scratch workspace...
        picklepaths = [arcpy.env.scratchWorkspace + "\\deleteselection.p", arcpy.env.scratchWorkspace + "\\splitselection.p", arcpy.env.scratchWorkspace + "\\global1global2.p", arcpy.env.scratchWorkspace + "\\splitgeometries.p", arcpy.env.scratchWorkspace + "\\splitselectionvariables.p", arcpy.env.scratchWorkspace + "\\splitselection_multiple.p", arcpy.env.scratchWorkspace + "\\domains.p", arcpy.env.scratchWorkspace + "\\editnamesselection.p", arcpy.env.scratchWorkspace + "\\lrsselection.p", arcpy.env.scratchWorkspace + "\\tool_indicator.p", arcpy.env.scratchWorkspace + "\\mergeselection_multiple.p", arcpy.env.scratchWorkspace + "\\newsegmentselection.p"]
        pickleexist = [x for x in picklepaths if os.path.exists(x)]
        for p in pickleexist:
            if p:
                os.remove(p)

        NJRE_logger.info('Edit session ended')
        NJRE_logger.removeHandler(NJRE_handler)
        NJRE_logger.info('Handler removed')
    def onStartOperation(self):
        global INTOOL, esesh, monitorOp
        print "onStartOperation {0}".format(INTOOL)
        INTOOL = self.get_tool_indicator()
        if INTOOL == False:
            esesh['onStartOperation'] = 1
            print "onStartOperation"
            print esesh
            global monitorOp
            print monitorOp
    def beforeStopOperation(self):
        pass
    def onStopOperation(self):
        print "onStopOperation"
        global monitorOp, NJRE_logger, pyexe, esesh
        global INTOOL
        tool_indicator_path = os.path.join(arcpy.env.scratchWorkspace, 'tool_indicator.p')
        # print 'XXpath exists: {0}'.format(os.path.exists(tool_indicator_path))
        if os.path.exists(tool_indicator_path):
            with open(tool_indicator_path,'rb') as toolindopen:
                tool_indicator = pickle.load(toolindopen)
                print 'tool indicator: {0}'.format(tool_indicator)
                INTOOL = tool_indicator
                print 'INTOOL: {0}'.format(INTOOL)
        if not INTOOL:
            monitorOp = str(esesh['onStartOperation']) + str(esesh['onChangeFeature']) + str(esesh['onCreateFeature']) + str(esesh['onDeleteFeature'])
            print "monitorOp is: " + monitorOp
        # New: 1010
        # Delete: 1001
        # Split: 1110
        # Merge: 1101
        # ChangeFeature: 1100
        # Copy Parallel: 1010
        # Buffer: 1010

        if not INTOOL:
            if monitorOp == "1100": # ChangeFeature
                print "you just changed a feature " + monitorOp
                esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                monitorOp = "Empty"
                print "after change, tokens are cleared, esesh is: {0}".format(esesh)
                print "monitorOp is: " + monitorOp

            if monitorOp == "1000": # Hidden Start
                print "you just did a hidden start " + monitorOp
                esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                monitorOp = "Empty"
                print "after hidden op, tokens are cleared, esesh is: {0}".format(esesh)
                print "monitorOp is: " + monitorOp

            if monitorOp == "1010":  # NewFeature
                print "you just created a new feature " + monitorOp

            if monitorOp == "1001":  # Delete
                print "you just deleted a feature " + monitorOp
                esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                monitorOp = "DF"
                print "after delete, tokens are cleared, esesh is: {0}".format(esesh)
                print "monitorOp is: " + monitorOp

            if monitorOp == "1101":  # Merge
                print "you just merged a feature " + monitorOp
            if monitorOp == "1110" and self.NJRE_Env:  # Split Endpoint
                try:
                    NJRE_logger.info('Split endpoint. {0}'.format(erebus.sqlGUID("SEG_GUID",lastselect['SEG_GUID'])))
                    print "you just split a feature " + monitorOp
                    esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                    monitorOp = "Split"
                    print "monitorOp is: " + monitorOp
                    ####################################################################
                    ## 1) Dump out the original segment along with its geometry
                    splitpath = arcpy.env.scratchWorkspace + "\\splitselection.p"
                    with open(splitpath, 'wb') as output:
                        pickle.dump([lastselect, segmentgeo], output, -1)  # outputs the row from the last selected segment, and ["SHAPE@"]
                    segmentgeo_copy = segmentgeo
                    ####################################################################
                    ## 2) Grab the first new segment and launch the Split_segment GP Dialog
                    # Now there are two new segments in SEGMENT, both with the same SEG_GUID, different GLOBALID
                    Xsegguid = {}
                    for i, v in enumerate(lastselect_fields):
                        Xsegguid[v] = i
                    # for a fgdb Xsegguid is...   note the order is different fram an enterprise gdb
                    #{u'ZIPNAME_R': 12, u'TRAVEL_DIR_TYPE_ID': 21, u'ADDR_R_FR': 7, u'SEG_ID': 2, u'ADDR_L_TO': 6, u'ZIPNAME_L': 11, u'JURIS_TYPE_ID': 22, u'OBJECTID': 0, u'DOT_REV_TYPE_ID': 24, u'ADDR_L_FR': 5, u'SYMBOL_TYPE_ID': 20, u'UPDATE_USER': 25, u'ACC_TYPE_ID': 17, u'ZIPCODE_L': 9, u'SURF_TYPE_ID': 18, u'MUNI_ID_L': 13, u'STATUS_TYPE_ID': 19, u'ELEV_TYPE_ID_TO': 16, u'UPDATEDATE': 26, u'ZIPCODE_R': 10, u'OIT_REV_TYPE_ID': 23, u'ELEV_TYPE_ID_FR': 15, u'Shape_Length': 28, u'PRIME_NAME': 4, u'SEG_GUID': 3, u'GLOBALID': 27, u'Shape': 1, u'MUNI_ID_R': 14, u'ADDR_R_TO': 8}
                    segsql = erebus.sqlGUID("SEG_GUID",lastselect['SEG_GUID'])
                    globalids = []
                    with arcpy.da.SearchCursor(segmentfc, ["GLOBALID"],segsql) as cursor:
                        for row in cursor:
                            globalids.append(row[0])
                    global1global2 = {'global1': globalids[0], 'global2': globalids[1]}
                    ggpath = arcpy.env.scratchWorkspace + "\\global1global2.p"
                    with open(ggpath, 'wb') as output:
                        pickle.dump(global1global2, output, -1)
                    # Go select the first segment and give the user a chance to update it...
                    #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                    globalsql1 = erebus.sqlGUID("GLOBALID",globalids[0]) # this is the
                    globalsql2 = erebus.sqlGUID("GLOBALID",globalids[1])
                    #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
                    try:
                        # Get the geometry of the segment 1
                        with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"], globalsql1) as geocursor:
                            for geo in geocursor:
                                ge1 = json.loads(geo[0].JSON)
                        # Get the geometry of the segment 2
                        with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"], globalsql2) as geocursor:
                            for geo in geocursor:
                                ge2 = json.loads(geo[0].JSON)
                    except:
                        trace = traceback.format_exc()
                        NJRE_logger.error('Geometry query on segment failed due to true curve. WKT will be used instead.')
                        NJRE_logger.exception(trace)
                        # Get the geometry of the segment 1
                        with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"], globalsql1) as cursor:
                            for row in cursor:
                                geometry1 = row[0]
                        # convert the wkt to esrijson
                        ej1 = erebus.wkt_to_esrijson(geometry1)
                        ge1 = ej1['esrijson']
                        # Get the geometry of the segment 2
                        with arcpy.da.SearchCursor(segmentfc, ["SHAPE@"], globalsql2) as cursor:
                            for row in cursor:
                                geometry2 = row[0]
                        # convert the wkt to esrijson
                        ej2 = erebus.wkt_to_esrijson(geometry2)
                        ge2 = ej2['esrijson']
                    # dump out a geometry pickle so that the SplitSegment tool can use it to interpolate the address ranges
                    splitpath = arcpy.env.scratchWorkspace + "\\splitgeometries.p"
                    with open(splitpath, 'wb') as output:
                        pickle.dump([ge1, ge2], output, -1)
                    # Select segment one so the use knows which one that they are working on
                    arcpy.SelectLayerByAttribute_management(segmentfc, 'NEW_SELECTION', globalsql1)
                    killsplit = False; splitchoice1 = False
                    count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
                    ############################################################
                    ############################################################
                    NewSplit = True
                    if NewSplit == True:
                        if count == 1:
                            import subprocess
                            import sys
                            import time

                            SplitHolderOne = pythonaddins.MessageBox('Use the NJRE Python Add-In to complete the split?', 'NJRE Split Message', 1)  # hold and wait for the segment to be selected
                            if SplitHolderOne == 'OK': # user click ok on the dialog
                                NJRE_logger.info('Split OK number 1')
                                arcpy.RefreshActiveView()

                                ################################################
                                ## Footprint --Get the Footprint for each of the segments.
                                Fp1 = erebus.Footprint(globalids[0], qmode = 'GLOBALID')
                                Footprint1 = Fp1.getfootprint([segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab])

                                NJRE_logger.info('Split Footprint 1')
                                #print '\nglobal id 1 $$$$$$', globalids[0]
                                #print 'fp1 $$$$$$$$$$$$$$\n', Footprint1

                                ################################################
                                ## ELEVATION INTERPOLATION -- You already have the geometries for each of the segments.
                                ## Figure out which elevation should be left blank for each.
                                ## By blank, I mean the place where the split took place, so that
                                ## the user has to input the elevation, becausse it is unknown

                                #Get the bisector points on either side of the split
                                bisector = erebus.bisect_points(ge1, ge2, droplength = 10, plot = False)
                                NJRE_logger.info('\nbisector {0}'.format(str(bisector)) )

                                Elev_to_Split = {}   #{'ELEV_TYPE_ID_FR': 'At Grade', 'ELEV_TYPE_ID_TO': None}
                                if bisector['result'] == 'success':
                                    bis_start_end = bisector['splitstartend 1']
                                    elevdict = {0: 'At Grade', 1: 'Level 1', 2: 'Level 2', 3: 'Level 3'}
                                    if bis_start_end == 'end':
                                        Elev_to_Split['ELEV_TYPE_ID_FR'] = elevdict[Footprint1['SEGMENT'][0]['ELEV_TYPE_ID_FR']]
                                        Elev_to_Split['ELEV_TYPE_ID_TO'] = None
                                    if bis_start_end == 'start':
                                        Elev_to_Split['ELEV_TYPE_ID_TO'] = elevdict[Footprint1['SEGMENT'][0]['ELEV_TYPE_ID_TO']]
                                        Elev_to_Split['ELEV_TYPE_ID_FR'] = None

                                ################################################
                                ## ADDRESS INTERPOLATION --
                                IntAdd1 = erebus.InterpolateAddress(Footprint1)
                                geocodeurl = 'http://geodata.state.nj.us/arcgis/rest/services/Tasks/Addr_NJ_road/GeocodeServer'
                                #NJRE_logger.info('geometries: {0}\n\n{1}'.format(ge1,ge2))
                                (IntVal_1, addintmess_1) = IntAdd1.interpolate(ge1,ge2,geocodeurl,1)   # {'ADDR_L_FR': None, 'ADDR_L_TO': None, 'ADDR_R_FR': None, 'ADDR_R_TO': None}, {'even': None, 'odd': None, 'result': 'na', 'message': 'na', 'primename': False, 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}
                                NJRE_logger.info('Split 1 Geocoded')
                                #print '\nIntVal_1', IntVal_1
                                # if IntVal_1['ADDR_L_FR'] = (LF, False), then the LF value is what was in there to begin with. LF could be None !!!
                                # if IntVal_1['ADDR_L_FR'] = (LF, True), then the LF value is interpolated

                                ################################################
                                ## Split UI #1
                                ################################################
                                startupinfo = subprocess.STARTUPINFO()
                                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                                INTOOL = True
                                idpath = os.path.join(os.path.dirname(__file__), 'Split_Test.py')
                                NJRE_logger.info('Split 1 UI Called')
                                NJRE_logger.info('\n  idpath {0}'.format(idpath))
                                NJRE_logger.info('\n  arcpy.env.scratchWorkspace {0}'.format(arcpy.env.scratchWorkspace))
                                NJRE_logger.info('\n  Footprint 1 {0}'.format(str(Footprint1)) )
                                NJRE_logger.info('\n  Footprint Length {0}'.format(len(str(Footprint1))))
                                NJRE_logger.info('\n  Elev_to_Split {0}'.format(str(Elev_to_Split)))
                                NJRE_logger.info('\n  IntVal_1 {0}'.format(str(IntVal_1)))
                                domains_path = os.path.join(arcpy.env.scratchWorkspace, "domains.p")
                                if os.path.exists(domains_path):
                                    os.remove(domains_path)
                                with open(domains_path, 'wb') as output:
                                    pickle.dump(self.Domains, output, -1)
                                pipe = subprocess.Popen([pyexe, idpath, '1', arcpy.env.scratchWorkspace, str(Footprint1), 'None', str(Elev_to_Split), str(IntVal_1)], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                                (stdoutdata, stderrdata) = pipe.communicate()
                                pipe.terminate()
                                if stderrdata:
                                    print 'stderrdata:  {0}'.format(stderrdata)
                                if stdoutdata:
                                    #print 'stdoutdata:  {0}\n'.format(stdoutdata)
                                    #print 'stdoutdata type:  {0}'.format(type(stdoutdata))
                                    Split1_result = stdoutdata.split('***')[0]; print 'Split1_result', Split1_result
                                    Split1_Footprint = eval(stdoutdata.split('***')[1]) ; print 'Split1_Footprint', Split1_Footprint
                                    if Split1_result == "OK":
                                        NJRE_logger.info('Split 1 Success')
                                        ################################################
                                        ## Split UI #2
                                        ################################################
                                        arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                                        arcpy.SelectLayerByAttribute_management(segmentfc, 'NEW_SELECTION', globalsql2)
                                        arcpy.RefreshActiveView()
                                        count = int(arcpy.GetCount_management(segmentfc).getOutput(0))
                                        if count == 1:
                                            SplitHolderTwo = pythonaddins.MessageBox('Continue?', 'NJRE Split Message', 1)
                                            if SplitHolderTwo == 'OK':
                                                NJRE_logger.info('Split OK number 2')
                                                Fp2 = erebus.Footprint(globalids[1], qmode = 'GLOBALID')
                                                Footprint2 = Fp2.getfootprint([segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab])
                                                NJRE_logger.info('Footprint 2')
                                                bis_start_end = bisector['splitstartend 2']
                                                Elev_to_Split = {}
                                                if bis_start_end == 'end':
                                                    Elev_to_Split['ELEV_TYPE_ID_FR'] = elevdict[Footprint2['SEGMENT'][0]['ELEV_TYPE_ID_FR']]
                                                    Elev_to_Split['ELEV_TYPE_ID_TO'] = None
                                                if bis_start_end == 'start':
                                                    Elev_to_Split['ELEV_TYPE_ID_TO'] = elevdict[Footprint2['SEGMENT'][0]['ELEV_TYPE_ID_TO']]
                                                    Elev_to_Split['ELEV_TYPE_ID_FR'] = None
                                                ################################################
                                                ## ADDRESS INTERPOLATION --
                                                IntAdd2 = erebus.InterpolateAddress(Footprint2)
                                                (IntVal_2, addintmess_2) = IntAdd2.interpolate(ge1,ge2,geocodeurl,2)   # {'ADDR_L_FR': None, 'ADDR_L_TO': None, 'ADDR_R_FR': None, 'ADDR_R_TO': None}, {'even': None, 'odd': None, 'result': 'na', 'message': 'na', 'primename': False, 'addrlfr': False, 'addrlto': False, 'addrrfr': False, 'addrrto': False}
                                                NJRE_logger.info('Split 2 Geocoded')
                                                ################################################
                                                ## SPLIT 2 --
                                                NJRE_logger.info('Split 2 UI Called')
                                                pipe = subprocess.Popen([pyexe, idpath, '2', arcpy.env.scratchWorkspace, str(Footprint2), 'None', str(Elev_to_Split), str(IntVal_2)], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                                                (stdoutdata2, stderrdata2) = pipe.communicate()
                                                pipe.terminate()
                                                if stderrdata2:
                                                    print 'stderrdata2:  {0}'.format(stderrdata2)
                                                if stdoutdata2:
                                                    #print 'stdoutdata2:  {0}\n'.format(stdoutdata2)
                                                    Split2_result = stdoutdata2.split('***')[0]; print 'Split2_result', Split2_result
                                                    Split2_Footprint = eval(stdoutdata2.split('***')[1]) ; print 'Split2_Footprint', Split2_Footprint
                                                    if Split2_result == "OK":
                                                        NJRE_logger.info('Split 2 Success')
                                                        ## SPLIT GEOPROCESSING
                                                        # This is what you get back from the tool. It needs to go throught to the SplitGeoprocessing class functionality
                                                        # so that
                                                        #{'SEGMENT': [{'OIT_REV_TYPE_ID': u'F', 'ELEV_TYPE_ID_FR': 0, 'ZIPNAME_R': u'BARNEGAT', 'TRAVEL_DIR_TYPE_ID': u'B', 'ACC_TYPE_ID': u'N', 'ZIPCODE_L': u'08005', 'SURF_TYPE_ID': u'I', 'MUNI_ID_R': u'882070', 'ADDR_R_FR': 172, 'ADDR_L_FR': 99999999999999999999L, 'STATUS_TYPE_ID': u'A', 'ELEV_TYPE_ID_TO': 0, 'JURIS_TYPE_ID': u'PUB', 'ADDR_R_TO': 176, 'DOT_REV_TYPE_ID': u'F', 'MUNI_ID_L': u'882070', 'ZIPCODE_R': u'08005', 'SYMBOL_TYPE_ID': 700, 'ZIPNAME_L': u'BARNEGAT', 'ADDR_L_TO': 66666666666666666666L}]}
                                                        arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                                                        NJRE_logger.info('Split geoprocessing results called')
                                                        splitgeoprocessing = erebus.SplitGeoprocessing(Split1_Footprint, Split2_Footprint, ge1, ge2, Footprint1, Footprint2, segmentgeo_copy, [segmentfc, segnametab, segshieldtab, linreftab, sldtab, segcommtab, transtab, segmentchangetab], arcpy.env.scratchWorkspace)
                                                        (splitgp_result, msg) = splitgeoprocessing.run()
                                                        # get the log and show the gp results
                                                        splitlogpath = os.path.join(arcpy.env.scratchWorkspace, 'SplitGeoprocessing.log')
                                                        if os.path.exists(splitlogpath):
                                                            # read the log file and display it
                                                            with open(splitlogpath, 'r') as splitlog:
                                                                splitloglines = splitlog.readlines()
                                                            ########################
                                                            ## SPLIT GEOPROCESSING RESULTS
                                                            sgppath = os.path.join(os.path.dirname(__file__), 'GpResults2.py')
                                                            sgppipe = subprocess.Popen([pyexe, sgppath, splitlogpath], startupinfo=startupinfo, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                                                            (sgpstdoutdata2, sgpstderrdata2) = sgppipe.communicate()
                                                            sgppipe.terminate()
                                                        NJRE_logger.info('Split tool ran')

                            arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                            INTOOL = False
                            esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                            monitorOp = 'Empty'

                except:
                    trace = traceback.format_exc()
                    arcpy.SelectLayerByAttribute_management(segmentfc, 'CLEAR_SELECTION')
                    INTOOL = False
                    esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0
                    monitorOp = 'Empty'
                    pythonaddins.MessageBox('The NJRE Python Add-In Split tool failed due to an error. Please try the operation again in a new edit session. If the issue persists, please email the "NJRE_logger.log" log file (in your scratch workspace) to njgin@oit.state.nj.us\n\n\n{0}'.format(trace), 'Split Error', 0)
                    NJRE_logger.error('Split tool failed with exception. User received message box with error')
                    NJRE_logger.exception(trace)
                    try:
                        pipe.terminate()
                    except:
                        pass





    def onSaveEdits(self):
        print "onSaveEdits"
        esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
    def onChangeFeature(self):
        # New Feature: "10101"
        INTOOL = self.get_tool_indicator()
        print "OnChangeFeature {0}".format(INTOOL)
        if INTOOL == False:
            esesh['onChangeFeature'] = 1
            print "OnChangeFeature"

    def onCreateFeature(self):
        #pythonaddins.MessageBox('onCreateFeature', 'INFO', 0)
        INTOOL = self.get_tool_indicator()
        print "onCreateFeature {0}".format(INTOOL)
        if INTOOL == False:
            print "OnChangeFeature"
            esesh['onCreateFeature'] = 1
            print esesh
            print monitorOp

    def onDeleteFeature(self):
        #pythonaddins.MessageBox('onDeleteFeature', 'INFO', 0)
        INTOOL = self.get_tool_indicator()
        print "onDeleteFeature {0}".format(INTOOL)
        if INTOOL == False:
            print "onDeleteFeature"
            esesh['onDeleteFeature'] = 1

    def onUndo(self):
        esesh['onStartOperation'] = 0; esesh['onChangeFeature'] = 0; esesh['onCreateFeature'] = 0; esesh['onDeleteFeature'] = 0;
        monitorOp = 'Empty'
        #pythonaddins.MessageBox('onUndo', 'INFO', 0)

    def onRedo(self):
        pass
        #pythonaddins.MessageBox('onRedo', 'INFO', 0)

