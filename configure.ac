# basics
AC_INIT(pyflag.in)

# Store the configuration in this header
AC_CONFIG_HEADER([src/include/config.h])
AC_CONFIG_HEADER([src/filesystems/sleuthkit/sleuthkit-2.52/tsk/tsk_config.h])
AC_CONFIG_AUX_DIR(config)
AM_INIT_AUTOMAKE(pyflag, 0.87-pre1)
AC_CONFIG_MACRO_DIR([config])

# check standard stuff
AC_PROG_LIBTOOL
AC_PROG_CC

# check headers
AC_CHECK_HEADER(zlib.h,,AC_MSG_ERROR([You Must install zlib-dev to build pyflag]))
AC_CHECK_HEADER(magic.h,,AC_MSG_ERROR([You Must install libmagic-dev to build pyflag this may be part of file the package for some distros]))

## Are we running on windows?
AC_CHECK_HEADER(windows.h,have_windows=yes,have_windows=no)

## Allow users to disable optional libraries:
## Afflib needs some special libraries to link against - is that a bug in afflib?
ac_my_check_lib_save_LIBS=$LIBS
LIBS="-lz -lcrypto -lstdc++  $LIBS"

AC_ARG_ENABLE(afflib, 
        [  --disable-afflib        Do not use AFFLIB even if it is installed],
# Action if they gave this argument
        [ if test "x$enableval" = "xyes" ; then
            AC_CHECK_LIB([afflib], [af_open], have_libafflib=yes, have_libafflib=no)
          elif test "x$enableval" = "xno" ; then
	    have_libafflib=disabled
            echo "Ignoring AFFLIB."
          else
            echo "Error: Unknown enable-afflib argument."
            exit -1
          fi
        ],
# if they did not specify aff, look for it
        [AC_CHECK_LIB([afflib], [af_open], have_libafflib=yes, [
		have_libafflib=no
		AC_MSG_WARN([You must install libaff (http://www.afflib.org/) for AFF image support])
		])]
        )

## Now work out which version of AFFLIB it is:
libaff_version=unknown
if test $have_libafflib = yes; then
	AC_CHECK_HEADER(afflib.h, libaff_version=1,)

   	if test $libaff_version = unknown; then
  		AC_CHECK_HEADER(afflib/afflib.h, libaff_version=3,)
   	fi

	if test $libaff_version = unknown; then
    		AC_MSG_WARN([I cant seem to find afflib.h (do you need to install afflib-dev)])
        	have_libafflib=no
   	fi
fi

AC_SUBST(LIBAFFLIB_VERSION, $libaff_version)
LIBS=$ac_my_check_lib_save_LIBS

ac_my_check_lib_save_LIBS=$LIBS
LIBS="-lz  $LIBS"

AC_ARG_ENABLE(ewf, 
        [  --disable-ewf           Do not use libewf even if it is installed],
# Action if they gave this argument
        [ if test "x$enableval" = "xyes" ; then
            AC_CHECK_LIB([ewf], [libewf_open], have_libewf=yes, [
		have_libewf=no; 
		])
          elif test "x$enableval" = "xno" ; then
	    have_libewf=disabled
            echo "Ignoring LibEWF."
          else
            echo "Error: Unknown enable-ewf argument."
            exit -1
          fi
        ],
# if they did not specify ewf, look for it
        [
	  AC_CHECK_LIB([ewf], [libewf_open], have_libewf=yes, 
	  [
	    have_libewf=no
	    AC_MSG_WARN([You must install libewf (http://www.uitwisselplatform.nl/projects/libewf/) for Expert Witness Format (encase) support])
	  ])
       ])
LIBS=$ac_my_check_lib_save_LIBS

## We only can use a later version than 20080501 - we compile a small
## program to check the version string:
if test $have_libewf = yes; then
	  ## Save libs
	  ac_check_lib_save_LIBS=$LIBS
	  LIBS="-lewf $LIBS"
	  AC_RUN_IFELSE(
	    [
	       AC_LANG_PROGRAM([[#include "libewf.h"]], 
	                       [[return(strcmp("20080501", libewf_get_version())>0);]])
	    ], have_libewf=yes ## If we succeeded we just do nothing
	    ,[
	       have_libewf=no
	       AC_MSG_WARN([You libewf version must be more recent then 20080501.])
	     ], have_libewf=yes ## Just compile it if cross compiling
	  )
	  ## Restore the libs
	  LIBS=$ac_check_lib_save_LIBS
fi

AC_CHECK_HEADER(GeoIP.h,have_geoip=yes, [
		have_geoip=no
		AC_MSG_WARN([please install libgeoip-dev for ip geolocation])
	])

AC_CHECK_HEADER(jpeglib.h,have_libjpeg=yes,AC_MSG_WARN([please install libjpeg62-dev for jpeg carving]))


## Conditionals for automake
AM_CONDITIONAL(HAVE_LIBAFFLIB, test "$have_libafflib" = yes)
AM_CONDITIONAL(HAVE_LIBEWF, test "$have_libewf" = yes)
AM_CONDITIONAL(HAVE_GEOIP, test "$have_geoip" = yes)
AM_CONDITIONAL(HAVE_LIBJPEG, test "$have_libjpeg" = yes)
AM_CONDITIONAL(HAVE_WINDOWS, test "$have_windows" = yes)

# python checks 
# (requires autoconf 1.5+ and the macros in acinclude.m4)
AC_ARG_WITH(
	windows_python,
	AC_HELP_STRING([--with-windows-python@<:@=WINDOWS_PYTHON@:>@],
			[Windows Python path (for cross compiling)]
	),
	[
		AM_PATH_PYTHON([2.5])
		AC_MSG_RESULT(Setting windows python for cross compiling $withval )
		AC_PYTHON_XCOMPILE_WINDOWS($withval)
	],
	[
		## Not specified - use the system python
		AM_PATH_PYTHON([2.5])
		AC_PYTHON_DEVEL()
AC_PYTHON_MODULE(MySQLdb, REQUIRED, [ You must install the python-mysql package ])
AC_PYTHON_MODULE(pexpect, REQUIRED, [ You must install the python-pexpect package ])
AC_PYTHON_MODULE(PIL, REQUIRED, [ You must install the python-imaging package ])
AC_PYTHON_MODULE(dateutil, REQUIRED, [ You must install the python-dateutil package ])

	])



# check for binaries
#AC_PATH_PROG([MYSQL], mysql)

# try to find magic files
AC_ARG_WITH(magic, AC_HELP_STRING([--with-magic], [specify a colon-separated list of system magic files, default autodetect]),,[magic=$(file -v 2>&1 | tail -1 | awk '{print $4}')])
AC_SUBST(magic)
            

# defines and output
AC_DEFINE([__DEBUG__], [], [Debuging enabled])

# endianess support
AC_C_BIGENDIAN()

# Large file support
AC_SYS_LARGEFILE

AC_OUTPUT([ 
	Makefile 
	src/Makefile 
	src/pyflag/Makefile 
	src/lib/Makefile 
	src/lib/pyewf/Makefile
	src/lib/pyaff/Makefile
	src/mmedia/Makefile
	src/mailtools/Makefile 
	src/indextools_ng/Makefile
	src/regtools/Makefile
	src/network/Makefile
	src/filesystems/Makefile
	src/filesystems/sleuthkit/Makefile
	src/filesystems/sleuthkit/python/Makefile
	src/filesystems/magic/Makefile
	src/distorm/Makefile
	src/include/Makefile
	src/include/crypto/Makefile
	debian/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/tsk/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/tsk/base/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/tsk/img/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/tsk/vs/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/tsk/fs/Makefile
	src/filesystems/sleuthkit/sleuthkit-2.52/tsk/hashdb/Makefile
	])

#	src/lib/libsgzip/Makefile
#	src/lib/libiosubsys/Makefile
#	src/filesystems/sleuthkit/auxtools/Makefile
#	src/filesystems/sleuthkit/imgtools/Makefile
#	src/filesystems/sleuthkit/fstools/Makefile
#	src/filesystems/sleuthkit/mmtools/Makefile

## Tell the use what we found:
AC_MSG_NOTICE([])
AC_MSG_NOTICE([*****************************************])
AC_MSG_NOTICE([PyFlag ${PACKAGE} ${VERSION} configuration])
AC_MSG_NOTICE([EWF Support:             $have_libewf ])
AC_MSG_NOTICE([AFF Support:             $have_libafflib ])
AC_MSG_NOTICE([MaxMind GeoIP:           $have_geoip ])
AC_MSG_NOTICE([Advanced JpegCarving:    $have_libjpeg ])
AC_MSG_NOTICE([*****************************************])
AC_MSG_NOTICE([])
