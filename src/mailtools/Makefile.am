include $(top_srcdir)/config/Makefile.rules

if !HAVE_WINDOWS
bin_PROGRAMS		= readpst
endif
noinst_HEADERS 		= libpst.h libstrfunc.h timeconv.h common.h vbuf.h lzfu.h

readpst_SOURCES		= libpst.c timeconv.c libstrfunc.c timeconv.h common.h \
			  vbuf.c debug.c readpst.c lzfu.c

