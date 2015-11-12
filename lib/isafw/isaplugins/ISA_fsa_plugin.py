#
# ISA_fsa_plugin.py -  Filesystem analyser plugin, part of ISA FW
#
# Copyright (c) 2015, Intel Corporation
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of Intel Corporation nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import os
from stat import *
from lxml import etree

FSAnalyzer = None
full_report = "/fsa_full_report_"
problems_report = "/fsa_problems_report_"
log = "/isafw_fsalog"

class ISA_FSChecker():    
    initialized = False
    def __init__(self, ISA_config):
        self.proxy = ISA_config.proxy
        self.reportdir = ISA_config.reportdir
        self.logdir = ISA_config.logdir
        self.timestamp = ISA_config.timestamp
        self.initialized = True
        self.setuid_files = []
        self.setgid_files = []
        self.ww_files = []
        self.no_sticky_bit_ww_dirs = []
        print("Plugin ISA_FSChecker initialized!")
        with open(self.logdir + log, 'w') as flog:
            flog.write("Plugin ISA_FSChecker initialized!\n")

    def process_filesystem(self, ISA_filesystem):
        if (self.initialized == True):
            if (ISA_filesystem.img_name and ISA_filesystem.path_to_fs):
                with open(self.logdir + log, 'a') as flog:
                    flog.write("Analyzing filesystem at: " + ISA_filesystem.path_to_fs + " for the image: " + ISA_filesystem.img_name)
                self.files = self.find_fsobjects(ISA_filesystem.path_to_fs)
                with open(self.logdir + log, 'a') as flog:
                    flog.write("\n\nFilelist is: " + str(self.files))
                with open(self.reportdir + full_report + ISA_filesystem.img_name + "_" + self.timestamp, 'w') as ffull_report:
                    ffull_report.write("Report for image: " + ISA_filesystem.img_name + '\n')
                    ffull_report.write("With rootfs location at " + ISA_filesystem.path_to_fs + "\n\n")
                    for f in self.files:
                        st = os.lstat(f)
                        i = f.replace(ISA_filesystem.path_to_fs, "")
                        ffull_report.write("File: " + i + ' mode: ' + str(oct(st.st_mode)) + 
                                           " uid: " + str(st.st_uid) + " gid: " + str(st.st_gid) + '\n')
                        if ((st.st_mode&S_ISUID) == S_ISUID):
                            self.setuid_files.append(i)
                        if ((st.st_mode&S_ISGID) == S_ISGID):
                            self.setgid_files.append(i)
                        if ((st.st_mode&S_IWOTH) == S_IWOTH):
                            if (((st.st_mode&S_IFDIR) == S_IFDIR) and ((st.st_mode&S_ISVTX) != S_ISVTX)):
                                self.no_sticky_bit_ww_dirs.append(i)
                            if (((st.st_mode&S_IFREG) == S_IFREG) and ((st.st_mode&S_IFLNK) != S_IFLNK)):        
                                self.ww_files.append(i)
                self.write_problems_report(ISA_filesystem)
                self.write_problems_report_xml(ISA_filesystem)
            else:
                print("Mandatory arguments such as image name and path to the filesystem are not provided!")
                print("Not performing the call.")
                with open(self.logdir + log, 'a') as flog:
                    flog.write("Mandatory arguments such as image name and path to the filesystem are not provided!\n")
                    flog.write("Not performing the call.\n")
        else:
            print("Plugin hasn't initialized! Not performing the call.")
            with open(self.logdir + log, 'a') as flog:
                flog.write("Plugin hasn't initialized! Not performing the call.\n")

    def write_problems_report(self, ISA_filesystem):
        with open(self.reportdir + problems_report + ISA_filesystem.img_name + "_" + self.timestamp, 'w') as fproblems_report:
            fproblems_report.write("Report for image: " + ISA_filesystem.img_name + '\n')
            fproblems_report.write("With rootfs location at " + ISA_filesystem.path_to_fs + "\n\n")
            fproblems_report.write("Files with SETUID bit set:\n")
            for item in self.setuid_files:
                fproblems_report.write(item + '\n')
            fproblems_report.write("\n\nFiles with SETGID bit set:\n")
            for item in self.setgid_files:
                fproblems_report.write(item + '\n')
            fproblems_report.write("\n\nWorld-writable files:\n")
            for item in self.ww_files:
                fproblems_report.write(item + '\n')
            fproblems_report.write("\n\nWorld-writable dirs with no sticky bit:\n")
            for item in self.no_sticky_bit_ww_dirs:
                fproblems_report.write(item + '\n')

    def write_problems_report_xml(self, ISA_filesystem):
        root = etree.Element('filesystem_problemsreport', {'location':ISA_filesystem.path_to_fs}, {'image':ISA_filesystem.img_name})
        sec1 = etree.SubElement(root, 'section', classname='ISA_FSChecker', name='Files_with_SETUID_bit_set')
        if self.setuid_files:
            failrs1 = etree.SubElement(sec1, 'failure', msg='Non-compliant files found', type='violation')                    
            for item in self.setuid_files:
                etree.SubElement(failrs1, 'value').text = item
        sec2 = etree.SubElement(root, 'section', classname='ISA_FSChecker', name='Files_with_SETGID_bit_set')
        if self.setgid_files:
            failrs2 = etree.SubElement(sec2, 'failure', msg='Non-compliant files found', type='violation')                    
            for item in self.setgid_files:
                etree.SubElement(failrs2, 'value').text = item
        sec3 = etree.SubElement(root, 'section', classname='ISA_FSChecker', name='World-writable_files')
        if self.ww_files:
            failrs3 = etree.SubElement(sec3, 'failure', msg='Non-compliant files found', type='violation')
            for item in self.ww_files:
                etree.SubElement(failrs3, 'value').text = item
        sec4 = etree.SubElement(root, 'section', classname='ISA_FSChecker', name='World-writable_dirs_with_no_sticky_bit')
        if self.no_sticky_bit_ww_dirs:
            failrs4 = etree.SubElement(sec4, 'failure', msg='Non-compliant directories found', type='violation')            
            for item in self.no_sticky_bit_ww_dirs:
                etree.SubElement(failrs4, 'value').text = item
        print (etree.tostring(root, pretty_print=True))
        tree = etree.ElementTree(root)
        output = self.reportdir + problems_report + ISA_filesystem.img_name + "_" + self.timestamp + '.xml' 
        tree.write(output, encoding= 'UTF-8', pretty_print=True, xml_declaration=True)

    def find_fsobjects(self, init_path):
        list_of_files = []
        for (dirpath, dirnames, filenames) in os.walk(init_path):
            if (dirpath != init_path):
                list_of_files.append(str(dirpath)[:])
            for f in filenames:
                list_of_files.append(str(dirpath+"/"+f)[:])
        return list_of_files

#======== supported callbacks from ISA =============#

def init(ISA_config):
    global FSAnalyzer 
    FSAnalyzer = ISA_FSChecker(ISA_config)
def getPluginName():
    return "ISA_FSChecker"
def process_filesystem(ISA_filesystem):
    global FSAnalyzer 
    return FSAnalyzer.process_filesystem(ISA_filesystem)

#====================================================#

