#!/usr/bin/env python
"""
Loads a NSRL database into flag.

Use this program like so:

>>> nsrl_load.py path_to_nsrl_directory/

An NSRL directory is one of the CDs, and usually has in it NSRLFile.txt,NSRLProd.txt.

IMPORTANT:
After uploading all the disk sets you should generate the index by doing:

alter table NSRL_hashes add index(`md5`(4))

You must do that or searching the NSRL will not work!!
"""

import DB,conf,sys
import csv

#Get a handle to our database
dbh=DB.DBO(None)
dbh.execute("""CREATE TABLE if not exists `NSRL_hashes` (
  `md5` char(16) NOT NULL default '',
  `filename` varchar(60) NOT NULL default '',
  `productcode` int NOT NULL default '',
  `oscode` varchar(60) NOT NULL default ''
)""")

dbh.execute("""CREATE TABLE if not exists `NSRL_products` (
`Code` MEDIUMINT NOT NULL ,
`Name` VARCHAR( 250 ) NOT NULL ,
`Version` VARCHAR( 20 ) NOT NULL ,
`OpSystemCode` VARCHAR( 20 ) NOT NULL ,
`ApplicationType` VARCHAR( 250 ) NOT NULL
) COMMENT = 'Stores NSRL Products'
""")

try:
    dirname = sys.argv[1]
except IndexError:
    print "Usage: %s path_to_nsrl" % sys.argv[0]
    sys.exit(0)

def to_md5(string):
    result=[]
    for i in range(0,32,2):
        result.append(chr(int(string[i:i+2],16)))
    return "".join(result)

## First do the main NSRL hash table
def MainNSRLHash(dirname):
    fd=csv.reader(file(dirname+"/NSRLFile.txt"))
    print "Starting to import %s/NSRLFile.txt" % dirname
    for row in fd:
        try:
            dbh.execute("insert into NSRL_hashes set md5=%r,filename=%r,productcode=%r,oscode=%r",(to_md5(row[1]),row[3],row[5],row[6]))
        except (ValueError,DB.DBError),e:
            print "SQL Error skipped %s" %e

## Now insert the product table:
def ProductTable(dirname):
    fd=csv.reader(file(dirname+"/NSRLProd.txt"))
    print "Starting to import %s/NSRLProd.txt" % dirname
    for row in fd:
        try:
            dbh.execute("insert into NSRL_products set Code=%r,Name=%r,Version=%r,OpSystemCode=%r,ApplicationType=%r",(row[0],row[1],row[2],row[3],row[6]))
        except (ValueError,DB.DBError),e:
            print "SQL Error skipped %s" %e

if __name__=="__main__":
    MainNSRLHash(dirname)
    ProductTable(dirname)
    print "Dont forget to create the index on the table once you have finished uploading all files!!\nALTER TABLE `NSRL_hashes` ADD INDEX  (`md5`(4))"
    
