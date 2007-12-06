# Michael Cohen <scudette@users.sourceforge.net>
# David Collett <daveco@users.sourceforge.net>
#
# ******************************************************
#  Version: FLAG $Version: 0.84RC4 Date: Wed May 30 20:48:31 EST 2007$
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
""" This Module will automatically load in IE History files (index.dat) files.

We use the files's magic to trigger the scanner off - so its imperative that the TypeScan scanner also be run or this will not work. We also provide a report to view the history files.
"""
import os.path
import pyflag.Scanner as Scanner
import pyflag.Reports as Reports
import pyflag.conf
config=pyflag.conf.ConfObject()
import FileFormats.IECache as IECache
import pyflag.DB as DB
from pyflag.TableObj import StringType, TimestampType, FilenameType
import pyflag.FlagFramework as FlagFramework

class IEIndexEventHandler(FlagFramework.EventHandler):
    def create(self, dbh, case):
        dbh.execute("""CREATE TABLE IF NOT EXISTS history (
        `path` TEXT NOT NULL,
        `type` VARCHAR(20) NOT NULL,
        `url` TEXT NOT NULL,
        `modified` TIMESTAMP DEFAULT 0,
        `accessed` TIMESTAMP DEFAULT 0,
        `filename` VARCHAR(250),
        `filepath` VARCHAR(250),
        `headers` TEXT)""")                

class IEIndex(Scanner.GenScanFactory):
    """ Load in IE History files """
    default = True
    depends = ['TypeScan']

    ## FIXME: Implement multiple_inode_reset
    def reset(self, inode):
        Scanner.GenScanFactory.reset(self, inode)
        dbh=DB.DBO(self.case)
        dbh.execute("delete from history")

    class Scan(Scanner.StoreAndScanType):
        types = ['application/x-ie-index']

        def external_process(self,fd):
            dbh=DB.DBO(self.case)
            history = IECache.IEHistoryFile(fd)
            for event in history:
                if event:
                    dbh.insert('history',
                               path=self.ddfs.lookup(inode=self.inode),
                               type = event['type'],
                               url = event['url'],
                               modified = event['modified_time'],
                               accessed = event['accessed_time'],
                               filename = event['filename'],
                               filepath = '',
                               headers = event['data'])

class IEHistory(Reports.report):
    """ View IE browsing history """
    name = "IE Browser History "
    family = "Disk Forensics"
    description="This report will display all IE browsing history data found in index.dat files"

    def display(self,query,result):
        result.heading("IE History")
        dbh=self.DBO(query['case'])
        dbh.check_index("history" ,"url",10)
        
        result.table(
            elements = [ StringType('Path','path'),
                         StringType('Type','type'),
                         StringType('URL','url'),
                         TimestampType('Modified','modified'),
                         TimestampType('Accessed','accessed'),
                         FilenameType(filename='filename', path='filepath', case=query['case']),
                         StringType('Headers','headers') ],
            table=('history'),
            case=query['case']
            )
