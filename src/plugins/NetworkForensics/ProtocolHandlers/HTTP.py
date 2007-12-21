""" This module implements features specific for HTTP Processing """
# Michael Cohen <scudette@users.sourceforge.net>
# Gavin Jackson <gavz@users.sourceforge.net>
#
# ******************************************************
#  Version: FLAG $Version: 0.84RC5 Date: Wed Dec 12 00:45:27 HKT 2007$
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
import pyflag.conf
config=pyflag.conf.ConfObject()
from pyflag.Scanner import *
import dissect,sys
import struct,sys,cStringIO
import pyflag.DB as DB
from pyflag.FileSystem import File
import pyflag.IO as IO
import pyflag.FlagFramework as FlagFramework
from pyflag.FlagFramework import query_type
from NetworkScanner import *
import pyflag.Reports as Reports
import plugins.NetworkForensics.PCAPFS as PCAPFS
import re,time,cgi
import TreeObj
from pyflag.TableObj import StringType, TimestampType, InodeType, IntegerType, PacketType

def escape(uri):
    """ Make a filename from a URI by escaping / chars """
    filename = FlagFramework.normpath(uri).replace('/', '_')
    return filename

class HTTP:
    """ Class used to parse HTTP Protocol """
    def __init__(self,fd,ddfs):
        self.fd=fd
        self.ddfs = ddfs
        self.request = { 'url':'/unknown_request_%s' % fd.con_id }
        self.response = {}
        self.request_re = re.compile("(GET|POST|PUT|OPTIONS) +([^ ]+) +HTTP/1\..",
                                     re.IGNORECASE)
        self.response_re = re.compile("HTTP/1\.. (\\d+) +", re.IGNORECASE)

    def read_headers(self, dict):
        while True:
            line = self.fd.readline()
            if not line or line=='\r\n':    
                return True

            tmp = line.split(':',1)
            try:
                dict[tmp[0].lower().strip()] =tmp[1].strip()
            except IndexError:
                pass

    def read_request(self, line):
        """ Checks if line looks like a URL request. If it is, we
        continue reading the fd until we finish consuming the request
        (headers including post content if its there).

        We should be positioned at the start of the response after this.
        """
        m=self.request_re.search(line)
        if not m: return False

        self.request = dict(url=m.group(2),
                            method=m.group(1),
                            packet_id = self.fd.get_packet_id(self.fd.tell())
                            )
        self.read_headers(self.request)

        return True
        
    def read_response(self, line):
        """ Checks if line looks like a HTTP Response. If it is, we
        continue reading the fd until we finish consuming the
        response.

        We should be positioned at the start of the next request after this.
        """
        m=self.response_re.search(line)
        if not m: return False

        self.response = dict(HTTP_code= m.group(1),
                             packet_id = self.fd.get_packet_id(self.fd.tell())
                             )
        self.read_headers(self.response)
        return True

    def skip_body(self, headers):
        """ Reads the body of the HTTP object depending on the values
        in the headers. This function takes care of correctly parsing
        chunked encoding.

        We assume that the fd is already positioned at the very start
        of the object. After this function we will be positioned at
        the end of this object.
        """
        try:
            skip = int(headers['content-length'])
            headers['body'] = self.fd.read(skip)
            return
        except KeyError:
            pass

        ## If no content-length is specified maybe its chunked
        try:
            if "chunked" in headers['transfer-encoding'].lower():
                headers['body'] = ''
                while True:
                    line = self.fd.readline()
                    try:
                        length = int(line,16)
                    except:
                        return
                    
                    if length == 0:
                        return

                    ## There is a \r\n delimiter after the data chunk
                    headers['body'] += self.fd.read(length+2)
                    
                return
        except KeyError:
            pass

        ## If the header says close then the rest of the file is the
        ## body (all data until connection is closed)
        try:
            if "closed" in headers['connection'].lower():
                headers['body'] = self.fd.read()
                return
        except KeyError:
            pass
        
    def parse(self):
        """ We assume that we were given the combined stream and we parse it.

        We are a generator returning offset,length for HTTP messages,
        as well as their URLs.
        """
        while True:
            line=self.fd.readline()
            if not line: break

            ## Is this a request?
            if self.read_request(line):
                self.skip_body(self.request)

            ## Maybe a response?
            elif self.read_response(line):
                offset = self.fd.tell()
                self.skip_body(self.response)
                end = self.fd.tell()
                yield (offset, end-offset)

    def identify(self):
        offset = self.fd.tell()
        ## Currently the HTTP scanner needs both sides of the
        ## conversation to work properly. So we must have a request
        ## header. We try to resync if we are given a partial HTTP/1.1
        ## stream by looking ahead for a HTTP request. We check the
        ## first 1024 bytes.
        header = self.fd.read(1024)
        m = self.request_re.search(header)
        if m:
            self.fd.seek(offset+m.start())
            return True

        m = self.response_re.search(header)
        if m:
            self.fd.seek(offset+m.start())
            return True
            
        return False

class HTTPTables(FlagFramework.EventHandler):
    def create(self, dbh, case):
        ## This is the information we store about each http request:
        ## inode - the inode which represents the response to this request
        ## request_packet - the packet id the request was sent in
        ## method - method requested
        ## url - the URL requested (This is the fully qualified url with host header included if present).
        ## response_packet - the packet where the response was seen
        ## content_type - The content type
        
        dbh.execute(
            """CREATE TABLE if not exists `http` (
            `id` INT(11) not null auto_increment,
            `parent` INT(11) default 0 not null,
            `inode` VARCHAR( 255 ) NULL ,
            `request_packet` int null,
            `method` VARCHAR( 10 ) NULL ,
            `url` text NULL,
            `response_packet` int null,
            `content_type` VARCHAR( 255 ) NULL,
            `referrer` text NULL,
            `date` timestamp,
            `host` VARCHAR(255),
            `useragent` VARCHAR(255),
            primary key (`id`)
            )""")

        dbh.execute(
            """CREATE TABLE if not exists `http_parameters` (
            `id` int(11) not null,
            `key` VARCHAR(255) not null,
            `value` text not null
            ) """)

        dbh.check_index("http", "inode")
        dbh.check_index("http", "url", 100)
        
class HTTPScanner(StreamScannerFactory):
    """ Collect information about HTTP Transactions.
    """
    default = True
    
    class Drawer(Scanner.Drawer):
        description = "Network Scanners"
        name = "NetworkScanners"
        contains = [ "IRCScanner", "MSNScanner", "HTTPScanner", "POPScanner",
                     "SMTPScanner","RFC2822", "YahooScanner", "LiveScanner" ]
        default = True
        special_fs_name = 'PCAPFS'


    def prepare(self):
        self.http_inodes = {}

    def reset(self, inode):
        dbh = DB.DBO(self.case)
        dbh.execute("delete from http")

    def parse_date_time_string(self, s):
        try:
            return time.mktime(time.strptime(s, "%a, %d %b %Y %H:%M:%S %Z"))
        except:
            print "Cant parse %s as a time" % s
            return 0

    def handle_parameters(self, request, id):
        """ Store the parameters of the request in the http_parameters
        table
        """
        try:
            base, query = request['url'].split('?',1)
        except:
            return
        
        def insert_query(query):
            dbh = DB.DBO(self.case)
            for key,value in cgi.parse_qsl(query, False):
                ## Non printable keys are probably not keys at all.
                if re.match("[^a-z0-9]+",key): return
                dbh.insert('http_parameters',
                                id = id,
                                key = key,
                                value = value)
                
            ## FIXME: Implement form-multipart parsing too


        insert_query(query)
        if request['method']=='POST':
            insert_query(request['body'])

    def process_stream(self, stream, factories):
        """ We look for HTTP requests to identify the stream. This
        allows us to processes HTTP connections on unusual ports. This
        situation might arise if HTTP proxies are used for example.
        """
        ## We only want to process the combined stream once:
        if stream.con_id>stream.reverse: return

        combined_inode = "I%s|S%s/%s" % (stream.fd.name, stream.con_id, stream.reverse)
        try:
            fd = self.fsfd.open(inode=combined_inode)
        ## If we cant open the combined stream, we quit (This could
        ## happen if we are trying to operate on a combined stream
        ## already
        except IOError: return
        
        p=HTTP(fd,self.fsfd)
        ## Check that this is really HTTP
        if not p.identify():
            return
        
        pyflaglog.log(pyflaglog.DEBUG,"Openning %s for HTTP" % combined_inode)
        ## Iterate over all the messages in this connection
        for f in p.parse():
            if not f: continue
            offset, size = f

            ## Create the VFS node:
            ##path=self.fsfd.lookup(inode="I%s|S%s" % (stream.fd.name, stream.con_id))
            ##path=os.path.dirname(path)
            new_inode="%s|o%s:%s" % (combined_inode,offset,size)

            try:
                if 'chunked' in p.response['transfer-encoding']:
                    new_inode += "|c0"
            except KeyError:
                pass

            try:
                if 'gzip' in p.response['content-encoding']:
                    new_inode += "|G1"

            except KeyError:
                pass

            ## stream.ts_sec is already formatted in DB format
            date_str = stream.ts_sec.split(" ")[0]
            path=self.fsfd.lookup(inode=combined_inode)
            path=os.path.normpath(path+"/../../../../../")

            self.fsfd.VFSCreate(None,new_inode,
                                "%s/HTTP/%s/%s" % (path,date_str,
                                                   escape(p.request['url'])),
                                mtime=stream.ts_sec, size=size
                                )

            ## Store information about this request in the
            ## http table:
            host = p.request.get("host",IP2str(stream.dest_ip))
            url = p.request.get("url")
            try:
                date = p.response.get("date")
                date = int(self.parse_date_time_string(date))
            except (KeyError,ValueError):
                date = 0

            try:
                referer = p.request['referer']
            except KeyError:
                try:
                    referer = p.request['referrer']
                except KeyError:
                    referer = ''

            if not url.startswith("http://") and not url.startswith("ftp://"):
                url = "http://%s%s" % (host, url)

            ## Find referred page:
            parent = 0
            dbh = DB.DBO(self.case)
            if referer:
                dbh.execute("select id from http where url=%r order by id desc limit 1", referer)
                row = dbh.fetch()

                ## If there is no referrer we just make a psuedo entry
                if not row:
                    ## Find out the host
                    m=re.match("(http://|ftp://)([^/]+)([^\?\&\=]*)",
                               "%s" % referer)
                    if m:
                        host = m.group(2)
                        dbh.insert("http", url=referer, host=host)
                        parent = dbh.autoincrement()
                else:
                    parent = row['id']

            dbh.insert('http',
                            inode          = new_inode,
                            request_packet = p.request.get("packet_id",0),
                            method         = p.request.get("method","-"),
                            url            = url,
                            response_packet= p.response.get("packet_id"),
                            content_type   = p.response.get("content-type","text/html"),
                            _date           = "from_unixtime(%r)" % date,
                            referrer       = referer,
                            host           = host,
                            useragent      = p.request.get('user-agent', '-'),
                            parent         = parent)                            

            ## handle the request's parameters:
            self.handle_parameters(p.request, dbh.autoincrement())

            ## Scan the new file using the scanner train. 
            self.scan_as_file(new_inode, factories)
        
class BrowseHTTPRequests(Reports.report):
    """
    Browse HTTP Requests
    --------------------
    
    This allows users to search the HTTP Requests that were loaded as
    part of the PCAP File system.

    This is the information we store about each http request:

       - inode:
         the inode which represents the response to this request

       - request_packet:
         the packet id the request was sent in
         
       - method:
         method requested
         
       - url:
         the URL requested (This is the fully qualified url with host header included if present).
         
       - response_packet:
         the packet where the response was seen
         
       - content_type:
         The content type of the response to this request.

    HTTP Sessions
    -------------

    The HTTP Protocol is typically used to serve up HTML pages. The
    HTML pages make references to other pages via hyperlinks, object
    tags, image tags etc.

    In a typical browsing session, the user follows from page to page
    via a series of links. The browser notifies the web server of
    where its previously been via the referer tag, or via cookies. The
    path of navigation from page to page is thought of as a user
    session.

    In a forensic context, the user session places context around the
    users activity with a clear timeline of events showing
    progression, rather than treating each web request as an
    individual discrete event.

    This report shows the user sessions as deduced by the referer tags
    or cookies.         
    """
    name = "Browse HTTP Requests"
    family = "Network Forensics"
    
    def display(self,query,result):    
        result.heading("Requested URLs")

        def tabular_view(query,result):
            result.table(
                elements = [ TimestampType('Date','ts_sec'),
                             PacketType('Request Packet','request_packet', case=query['case']),
                             InodeType('Inode','inode', case=query['case']),
                             StringType('Method','method'),
                             StringType('URL','url'),
                             StringType('Content Type','content_type') ],
                table=" http join pcap on request_packet=pcap.id ",
                case=query['case']
                )

        def tree_view(query,result):
            def tree_cb(path):
                t = HTTPTree(path=path, case=query['case'], table='http')
                for row in t.children():
                    try:
                        m=re.match("(http://|ftp://)([^/]+)([^\?\&\=]*)",
                                   "%s" % row['url'])
                        child_host = m.group(2)
                        child_uri = m.group(3)

                        m=re.match("(http://|ftp://)([^/]+)([^\?\&\=]*)",
                                   "%s" % t['url'])

                        parent_host = m.group(2)
                        
                        if parent_host==child_host:
                            result = child_uri
                        else:
                            result = row['url']
                    except AttributeError:
                        result=row['url']

                    type='branch'
                    type = 'leaf'
                    for children in row.children():
                        type = 'branch'
                        break

                    yield(("%s" % row['id'],result,type))

            def pane_cb(path, result):
                t = HTTPTree(path=path, case=query['case'], table='http')
                result.heading(t['url'])
                for k,v in t.row.items():
                    if v:
                        result.row(k,v)

            result.tree(tree_cb=tree_cb, pane_cb=pane_cb)

        tabular_view(query,result)
        return

        ## FIXME: The HTTP Sessions stuff takes way too long -
        ## disabled for now
        result.notebook(
            names=['HTTP Requests','HTTP Sessions'],
            callbacks = [tabular_view, tree_view]
            )

class Chunked(File):
    """ This reads chunked HTTP Streams.

    """
    specifier = 'c'

    def create_file(self,filename):
        delimiter="\r\n"
        
        self.cached_fd = open(filename,'w')
        self.fd.seek(0)
        self.data = self.fd.read()
        self.size=0

        while 1:
            end = self.data.find(delimiter)+len(delimiter)
            if end<0: break

            try:
                size = int(self.data[:end],16)
            except:
                pyflaglog.log(pyflaglog.DEBUG, "Expecting chunked data length, found %s. Losing sync." % self.data[:end])
                return
            
            if size==0: break
            self.cached_fd.write(self.data[end:end+size])
            self.size+=size
            self.data=self.data[end+size+len(delimiter):]

        self.cached_fd.close()
        
    def __init__(self, case, fd, inode):
        File.__init__(self, case, fd, inode)

        self.filename = FlagFramework.get_temp_path(self.case,self.inode)

        try:
            self.cached_fd=open(self.filename,'r')
        except IOError:
            self.create_file(self.filename)
            self.cached_fd=open(self.filename,'r')
            

    def seek(self,offset,whence=0):
        self.cached_fd.seek(offset,whence)

    def tell(self):
        return self.cached_fd.tell()

    def read(self,length=None):
        if length==None:
            length=self.size-self.tell()
            
        return self.cached_fd.read(length)

class HTTPTree(TreeObj.TreeObj):
    """ HTTP Requests can be thought of as forming a tree, relating
    each request to its previous ones. The users select nodes in the
    tree which causes more pages to be downloaded.
    """
    node_name = "id"


## UnitTests:
import unittest
import pyflag.pyflagsh as pyflagsh
from pyflag.FileSystem import DBFS

class HTTPTests(unittest.TestCase):
    """ Tests HTTP Scanner """
    test_case = "PyFlag Network Test Case"
    order = 21
    def test01HTTPScanner(self):
        """ Test HTTP Scanner """
        env = pyflagsh.environment(case=self.test_case)
        pyflagsh.shell_execv(env=env,
                             command="scan",
                             argv=["*",                   ## Inodes (All)
                                   "HTTPScanner",
                                   ])                   ## List of Scanners
        dbh = DB.DBO(self.test_case)
        dbh.execute("select count(*) as total from http")
        row = dbh.fetch()
        print "Number of HTTP transfers found %s" % row['total']
        self.failIf(row['total']==0,"Count not find any HTTP transfers?")
