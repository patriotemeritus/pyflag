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
""" This is a test harness for running Unit tests.

Unit tests are defined in plugins as derived unittest.TestCase
classes. These are then picked off by the registry and run within the
harness.

Eventually all plugins will have complete unit tests.
"""
import sys
sys.path.append('.')
sys.path.append("pyflag")

import pyflag.Registry as Registry
import unittest,re
import pyflag.conf
config = pyflag.conf.ConfObject()
from optparse import OptionParser

config.set_usage(usage = """%prog [options]

Generic Test harness for running unit tests.
""")

config.add_option('match', short_option='m', default=None,
                  help='Run only tests matching this RE')

config.add_option('file', short_option='f', default=None,
                  help="Run only tests in this file (file is an RE)")

config.add_option('level', default=10, short_option='l',
                  type='int', help='Testing level (1 least exhaustive)')

config.add_option('list', short_option='L', default=None,
                  action='store_true', dest='list',
                  help='Just list all the available test classes without running them')

config.add_option('pause', short_option='p', default=False, action='store_true',
                  help='Pause after each test')

config.add_option('log', default=None,
                  help="Log file for resuming tests")

Registry.Init()
config.parse_options()

test_registry = Registry.InitTests()
if config.match:
    classes = [ x for x in test_registry.classes if \
                re.search(config.match,"%s" % x.__doc__)]
elif config.file:
    classes = [ x for x in test_registry.classes if \
                re.search(config.file,  \
                          test_registry.filename(test_registry.get_name(x))) ]
else:
    classes = test_registry.classes

if config.log:
    try:
        done = [ x.strip() for x in open(config.log).readlines() ]
    except IOError:
        done = []

## Only do those tests who are below the current level:
tmp = []
for x in classes:
    try:
        if x.level <= config.level:
            tmp.append(x)
    except AttributeError:
        ## If they do not have a level, their level is considered to be 5
        if 5 <= config.level:
            tmp.append(x)

classes = tmp

if config.list:
    import sys
    for test in classes:
        print "%s (%s)" % (test.__doc__,
                           test_registry.filename(test_registry.get_name(test)))
    sys.exit()

## Start up some workers:
import pyflag.Farm as Farm
Farm.start_workers()

import gc
#gc.set_debug(gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_INSTANCES | gc.DEBUG_SAVEALL | gc.DEBUG_LEAK)

for test_class in classes:
    if config.log and test_class.__name__ in done:
        continue

    try:
        doc = test_class.__doc__
    except: pass
    if not doc:
        doc = test_class
        
    print "---------------------------------------"
    print "Running tests in %s (%s)" % (doc, test_registry.filename( \
        test_registry.get_name(test_class)))
    print "---------------------------------------"
    suite = unittest.makeSuite(test_class)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    ## Preform a collection:
    gc.collect()

    print "Garbage is %s" % (gc.garbage,)
    
    ## Only pause for errors
    if config.pause and result.errors:
        raw_input("Pause")
        
    ## Only write logs for tests which work perfectly.
    if config.log and not result.errors:
        fd = open(config.log,'a')
        fd.write(test_class.__name__+"\n")
        fd.close()
