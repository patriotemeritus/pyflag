#!/usr/bin/python
# ******************************************************
# Michael Cohen <scudette@users.sourceforge.net>
#
# ******************************************************
#  Version: FLAG $Version: 0.87-pre1 Date: Thu Jun 12 00:48:38 EST 2008$
# ******************************************************
#
# * This program is free software; you can redistribute it and/or
# * modify it under the terms of the GNU General Public License
# * as published by the Free Software Foundation; either version 2
# * of the License, or (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# ******************************************************

import pypcap,sys,os,time,fcntl
import pyflag.conf
config = pyflag.conf.ConfObject()
import pyflag.pyflagsh as pyflagsh
import pyflag.Registry as Registry
import pyflag.Reports as Reports
import pyflag.DB as DB
import pyflag.pyflaglog as pyflaglog
import pyflag.ScannerUtils as ScannerUtils
import pyflag.Farm as Farm
import pyflag.FlagFramework as FlagFramework
import select

Registry.Init()

config.set_usage(usage = """%prog [options] directory_to_monitor output_file

Monitors the directory for files periodically. When a pcap file
appears in the directory it will be processed and scanned
automatically, the pcap file will be also written (merged) to the
output file. The pcap file will be unlinked (removed) afterwards.

NOTE: This loader does not start any workers, if you want to scan the
data as well you will need to start seperate workers.

if output_file is '-' we skip writing altogether. This is useful if
you never want to examine packets and only want to see reassembled
streams.
""", version = "Version: %%prog PyFlag %s" % config.VERSION)

config.add_option("case", default=None,
                  help="Case to load the files into (mandatory). Case must have been created already.")

config.add_option("iosource", default="o",
                  help="Iosource name to make for the output file")

config.add_option("mountpoint", default='/',
                  help='Mount point for the VFS')

config.add_option("sleep", default=60, type="int",
                  help='Length of time to wait between directory polls')

config.add_option("scanners", default='NetworkScanners,CompressedFile',
                  help='A comma delimited string of scanners to run')

config.add_option("timeout", default=120, type='int',
                  help="The maximum inactivity time after which the tcp reassembler will be flushed")

config.add_option("log", default="log.txt", 
                  help='This is a log file where we maintain a list of files that we already processed.')

config.add_option("lock", default='.lock',
                  help="Do not operate on directory while lock file is present")

config.add_option("single", default=False, action='store_true',
                  help = "Single shot (exit once done)")

config.parse_options(True)

try:
    directory = config.args[0]
    output_file = config.args[1]
except IndexError:
    print "You must specify both a directory to monitor and an output file"
    sys.exit(-1)

if not config.case:
    print "You must specify a case to load into"
    sys.exit(-1)

scanners = config.scanners.split(',')
scanners = ScannerUtils.fill_in_dependancies(scanners)
print scanners

output_fd = None

def create_output_file():
    global output_fd, output_file

    print "Will read from %s and write to %s. Will use these scanners: %s" % (directory, output_file, scanners)

    ## Check if the file is already there:
    filename = config.UPLOADDIR + '/' + output_file
    if output_file != '-':
        try:
            os.stat(filename)
            ## Yep its there:
            output_fd = open(filename, 'a')
            output_fd.seek(0,os.SEEK_END)
            offset = output_fd.tell()

            ## There can be only one:
            try:
                fcntl.flock(output_fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError,e:
                print "Highlander Error: %s" % e
                sys.exit(1)

        except OSError:
            output_fd = open(filename, 'w')

            ## This is a hardcoded header for the output file:
            header = '\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x01\x00\x00\x00'
            offset = len(header)

            ## Write the file header on
            output_fd.write(header)
            output_fd.flush()
    else:
        output_fd = None
        offset =0


    ## Make a new IO source for the output:
    try:
        pyflagsh.shell_execv(command="execute",
                             argv=["Load Data.Load IO Data Source",'case=%s' % config.case,
                                   "iosource=%s" % config.iosource,
                                   "subsys=Standard",
                                   "filename=%s" % (output_file),
                                   "offset=0",
                                   ])
    except Reports.ReportError:
        FlagFramework.print_bt_string()
    

def load_file(filename, processor,  pcap_dbh):
    global offset

    pyflaglog.log(pyflaglog.INFO, "%s: Processing %s" % (time.ctime(),filename))

    pcap_dbh.execute("select max(id) as m from pcap")
    row = pcap_dbh.fetch()
    pcap_id = row['m'] or 0

    try:
        input_file = pypcap.PyPCAP(open(filename), output='little')
    except IOError,e:
        pyflaglog.log(pyflaglog.INFO, "Error reading %s: %s" % (filename, e))
        return
    
    ## Iterate over all the packets in the file:
    while 1:
        try:
            packet = input_file.dissect()
            pcap_id += 1
        except StopIteration:
            break

        try:
            args = dict(
                    id = pcap_id,
                    iosource = config.iosource,
                    offset = offset,
                    length = packet.caplen,
                    _ts_sec =  "from_unixtime('%s')" % packet.ts_sec,
                    ts_usec = packet.ts_usec,
                )

            try:
                args['ipid']= packet.root.eth.payload.id
            except: pass

            try:
                if packet.root.eth.payload.payload.tsval:
                    args['tcp_ts'] = packet.root.eth.payload.payload.tsval
            except: pass

            pcap_dbh.mass_insert(**args)

            #pcap_dbh.mass_insert(
            #    id = pcap_id,
            #    iosource = config.iosource,
            #    offset = offset,
            #    length = packet.caplen,
            #    _ts_sec =  "from_unixtime('%s')" % packet.ts_sec,
            #    ts_usec = packet.ts_usec,
            #    )
        except KeyError,e:
            print packet.list()
            print e
            continue

        input_file.set_id(pcap_id)

        ## Some progress reporting
        if pcap_id % 10000 == 0:
            pyflaglog.log(pyflaglog.DEBUG, "processed %s packets (%s bytes)" % (pcap_id, offset))

        processor.process(packet)

        if output_fd:
            ## Write the packet on the output file:
            packet_data = packet.serialise("little")
            offset += len(packet_data)
            output_fd.write(packet_data)
        else:
            offset += packet.caplen

    if output_fd:
        output_fd.flush()
        
    pcap_dbh.delete("connection_details",
                    where = "inode_id is null")
    pcap_dbh.mass_insert_commit() 

last_mtime = 0
offset = 0

## Start up some workers if needed:
Farm.start_workers()

def update_files(files_we_have):
    try:
        log_fd = open(config.log)
        print "Reading log file"
        for l in log_fd:
            files_we_have.add(l.strip())
        print "Done - added %s files from log" % len(files_we_have)
        log_fd.close()
    except IOError:
        pass

    
def run(keepalive=None):
    global last_mtime, offset, output_fd

    create_output_file()

    print "Created output_fd"
    ## Get the PCAPFS class and instantiate it:
    pcapfs = Registry.FILESYSTEMS.dispatch("PCAP Filesystem")(config.case)
    pcapfs.mount_point = config.mountpoint
    pcapfs.VFSCreate(None, "I%s" % config.iosource, config.mountpoint, 
                     directory=True)

    pcap_dbh = DB.DBO(config.case)
    pcap_dbh.mass_insert_start("pcap")

    pcap_dbh.execute("select max(id) as m from pcap")
    pcap_id = pcap_dbh.fetch()['m'] or 0
    cookie, processor = pcapfs.make_processor(config.iosource, scanners)

    last_time = 0

    files_we_have = set()
    update_files(files_we_have)
    log_fd = open(config.log, "a")
    last_mtime = os.stat(directory).st_mtime

    while 1:
        ## Check that our parent process is still there:
        fds = select.select([keepalive],[],[], 0)
        if fds[0]:
            data = os.read(fds[0][0],1024)
            if len(data)==0:
                pyflaglog.log(pyflaglog.INFO, "Main process disappeared - closing children")
                ## Parent quit - kill our child
                os.kill(pid,signal.SIGABRT)
                os._exit(0)
        
        t = os.stat(directory).st_mtime
        if t>=last_mtime:
            last_mtime = t
            files = os.listdir(directory)
            files.sort()
            count = 0

            if not os.access(config.lock, os.F_OK):
                for f in files:
                   count +=1
                   if f in files_we_have: continue

                   ## Detect if the lock file appeared:
                   if os.access(config.lock, os.F_OK): break

                   if (count % 10) ==0 and config.MAXIMUM_WORKER_MEMORY > 0:
                       Farm.check_mem(finish)

                   filename = "%s/%s" % (directory,f)
                   if config.log:
                       log_fd.write(f+"\n")
                       log_fd.flush()
                       files_we_have.add(f)

                   load_file(filename, processor, pcap_dbh)

                   last_time = time.time()
            else:
               print "Lock file found"

            if config.single:
                ## Wait untill all our jobs are done
                pdbh = DB.DBO()
                while 1:
                    pdbh.execute("select count(*) as c from jobs where cookie = %r", cookie)
                    row = pdbh.fetch()
                    if row and row['c'] >0:
                        time.sleep(5)
                        continue
                    else:
                        break

                sys.exit(0)

            ## We need to flush the decoder:
            if time.time() - last_time > config.timeout:
                print "Flushing reassembler"
                processor.flush()
                last_time = time.time()

        print "%s: Sleeping for %s seconds" % (time.ctime(), config.sleep)
        time.sleep(config.sleep)

def finish():
    print "Loader Process size increased above threashold. Exiting and restarting."
    processor.flush()
    os._exit(0)

## Run the main loader under the nanny
import os
r,w = os.pipe()
Farm.nanny(run, keepalive=r)
while 1:
    print "Waiting"
    time.sleep(10)
