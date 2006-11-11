""" These Flash commands allow more sophisticated operations, most of
which may not be needed by most users. Some operations are
specifically designed for testing and have little use in practice.
"""
import pyflag.pyflagsh as pyflagsh
import pyflag.Registry as Registry
import pyflag.DB as DB
import fnmatch
import pyflag.FileSystem as FileSystem
import pyflag.Scanner as Scanner
import time

class scan(pyflagsh.command):
    def help(self):
        return "scan inode [list of scanners]: Scans the inodes with the scanners specified"

    def __init__(self, args, environment):
        pyflagsh.command.__init__(self,args,environment)
        self.dbh = DB.DBO(environment._CASE)
        self.case = environment._CASE
        self.ddfs = FileSystem.DBFS(self.case)

    def complete(self, text,state):
        if len(self.args)>2 or len(self.args)==2 and not text:
            scanners = [ x for x in Registry.SCANNERS.scanners if x.startswith(text) ]
            return scanners[state]
        else:
            self.dbh.execute("select  substr(inode,1,%r) as abbrev,inode from inode where inode like '%s%%' group by abbrev limit %s,1",(len(text)+1,text,state))
            return self.dbh.fetch()['inode']
    
    def execute(self):
        if len(self.args)<2:
            yield self.help()
            return

        ## Try to glob the inode list:
        self.dbh.execute("select inode from inode where inode rlike %r",fnmatch.translate(self.args[1]))
        dbh = DB.DBO()
        dbh.mass_insert_start('jobs')
        scanners = [ x for x in fnmatch.filter(Registry.SCANNERS.scanners, self.args[2]) ]
        
        for row in self.dbh:
            inode = row['inode']
            dbh.mass_insert(
                command = 'Scan',
                arg1 = self.case,
                arg2 = row['inode'],
                arg3 = ','.join(scanners)
                )

        dbh.mass_insert_commit()
        
        ## Wait until there are no more jobs left. FIXME: this is a
        ## short cut, we should probably only wait for our own jobs to
        ## finish. Maybe we need to add a cookie field to the jobs
        ## table so we can easily find our own jobs only.
        while 1:
            dbh.execute("select count(*) as total from jobs where arg1=%r", self.case)
            row = dbh.fetch()
            if row['total']==0: break

            time.sleep(1)
            
        yield "Scanning complete"

class scanner_reset(scan):
    def help(self):
        return "reset inode [list of scanners]: Resets the inodes with the scanners specified"
    
    def execute(self):
        if len(self.args)<2:
            yield self.help()
            return

        ## Try to glob the inode list:
        self.dbh.execute("select inode from inode where inode rlike %r",fnmatch.translate(self.args[1]))
        scanners = ["%s:%s" % (self.case,x) for x in fnmatch.filter(Registry.SCANNERS.scanners,self.args[2])]
        factories = Scanner.get_factories(scanners)

        for row in self.dbh:
            inode = row['inode']
            Scanner.resetfile(self.ddfs, inode, factories)

        yield "Resetting complete"
    
class load_and_scan(pyflagsh.command):
    def help(self):
        return "load_and_scan iosource fstype mount_point [list of scanners]: Loads the iosource into the right mount point and scans all new inodes using the scanner list. This allows scanning to start as soon as VFS inodes are produced and before the VFS is fully populated."

    def __init__(self, args, environment):
        pyflagsh.command.__init__(self,args,environment)
        self.dbh = DB.DBO(environment._CASE)
        self.case = environment._CASE
        self.ddfs = FileSystem.DBFS(self.case)

    def complete(self, text,state):
        if len(self.args)>4 or len(self.args)==4 and not text:
            scanners = [ x for x in Registry.SCANNERS.scanners if x.startswith(text) ]
            return scanners[state]
        elif len(self.args)>3 or len(self.args)==3 and not text:
            fstypes = [ x for x in Registry.FILESYSTEMS.fs.keys() if x.startswith(text) ]
            return fstypes[state]
        elif len(self.args)>2 or len(self.args)==2 and not text:
            return 
        elif len(self.args)>1 or len(self.args)==1 and not text:
            self.dbh.execute("select substr(value,1,%r) as abbrev,value from meta where property='iosource' and value like '%s%%' group by abbrev limit %s,1",(len(text)+1,text,state))
            return self.dbh.fetch()['value']
    
    def execute(self):
        if len(self.args)<4:
            yield self.help()
            return

        iosource,mnt_point,filesystem = self.args[1:4]

        dbh = DB.DBO()
        dbh.mass_insert_start('jobs')
        scanners = [ x for x in fnmatch.filter(Registry.SCANNERS.scanners, self.args[4]) ]

        ## Load the filesystem:
        try:
            fs = Registry.FILESYSTEMS.fs[filesystem]
        except KeyError:
            yield "Unable to find a filesystem of %s" % filesystem
            return

        fs=fs(self.case)
        fs.load(mnt_point, iosource, scanners)

        yield "Loading complete"
