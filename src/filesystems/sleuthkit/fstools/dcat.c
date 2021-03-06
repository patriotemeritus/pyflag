/*
** dcat
** The  Sleuth Kit 
**
** $Date: 2007/04/05 16:01:55 $
**
** Given an image , block number, and size, display the contents
** of the block to stdout.
** 
** Brian Carrier [carrier@sleuthkit.org]
** Copyright (c) 2006 Brian Carrier, Basis Technology.  All Rights reserved
** Copyright (c) 2003-2005 Brian Carrier.  All rights reserved
**
** TASK
** Copyright (c) 2002 Brian Carrier, @stake Inc.  All rights reserved
**
** TCTUTILs
** Copyright (c) 2001 Brian Carrier.  All rights reserved
**
**
** This software is distributed under the Common Public License 1.0
**
*/

#include <locale.h>
#include "fs_tools.h"

#define DLS_TYPE "dls"
#define RAW_STR "raw"

static TSK_TCHAR *progname;

void
usage()
{
    TFPRINTF(stderr,
        _TSK_T
        ("usage: %s [-ahsvVw] [-f fstype] [-i imgtype] [-o imgoffset] [-u usize] image [images] unit_addr [num]\n"),
        progname);
    tsk_fprintf(stderr, "\t-a: displays in all ASCII \n");
    tsk_fprintf(stderr, "\t-h: displays in hexdump-like fashion\n");
    tsk_fprintf(stderr,
        "\t-i imgtype: The format of the image file (use '-i list' for supported types)\n");
    tsk_fprintf(stderr,
        "\t-o imgoffset: The offset of the file system in the image (in sectors)\n");
    tsk_fprintf(stderr,
        "\t-f fstype: File system type (use '-f list' for supported types)\n");
    tsk_fprintf(stderr,
        "\t-s: display basic block stats such as unit size, fragments, etc.\n");
    tsk_fprintf(stderr, "\t-v: verbose output to stderr\n");
    tsk_fprintf(stderr, "\t-V: display version\n");
    tsk_fprintf(stderr, "\t-w: displays in web-like (html) fashion\n");
    tsk_fprintf(stderr,
        "\t-u usize: size of each data unit in image (for raw, dls, swap)\n");
    tsk_fprintf(stderr,
        "\t[num] is the number of data units to display (default is 1)\n");

    exit(1);
}


int
MAIN(int argc, TSK_TCHAR ** argv)
{
    TSK_FS_INFO *fs = NULL;
    TSK_IMG_INFO *img;
    DADDR_T addr = 0;
    TSK_TCHAR *fstype = NULL;
    TSK_TCHAR *cp, *imgtype = NULL;
    DADDR_T read_num_units;     /* Number of data units */
    int usize = 0;              /* Length of each data unit */
    int ch;
    char format = 0;
    extern int optind;
    SSIZE_T imgoff = 0;

    progname = argv[0];
    setlocale(LC_ALL, "");

    while ((ch = getopt(argc, argv, _TSK_T("af:hi:o:su:vVw"))) > 0) {
        switch (ch) {
        case _TSK_T('a'):
            format |= TSK_FS_DCAT_ASCII;
            break;
        case _TSK_T('f'):
            fstype = optarg;
            if (TSTRCMP(fstype, _TSK_T(DLS_TYPE)) == 0)
                fstype = _TSK_T(RAW_STR);
            if (TSTRCMP(fstype, _TSK_T("list")) == 0) {
                tsk_fprintf(stderr, "\t%s (Unallocated Space)\n",
                    DLS_TYPE);
                tsk_fs_print_types(stderr);
                exit(1);
            }
            break;
        case _TSK_T('h'):
            format |= TSK_FS_DCAT_HEX;
            break;
        case _TSK_T('i'):
            imgtype = optarg;
            if (TSTRCMP(imgtype, _TSK_T("list")) == 0) {
                tsk_img_print_types(stderr);
                exit(1);
            }
            break;
        case _TSK_T('o'):
            if ((imgoff = tsk_parse_offset(optarg)) == -1) {
                tsk_error_print(stderr);
                exit(1);
            }
            break;
        case _TSK_T('s'):
            format |= TSK_FS_DCAT_STAT;
            break;
        case _TSK_T('u'):
            usize = TSTRTOUL(optarg, &cp, 0);
            if (*cp || cp == optarg) {
                TFPRINTF(stderr, _TSK_T("Invalid block size: %s\n"),
                    optarg);
                usage();
            }
            break;
        case _TSK_T('v'):
            tsk_verbose++;
            break;
        case _TSK_T('V'):
            tsk_print_version(stdout);
            exit(0);
            break;
        case _TSK_T('w'):
            format |= TSK_FS_DCAT_HTML;
            break;
        case _TSK_T('?'):
        default:
            TFPRINTF(stderr, _TSK_T("Invalid argument: %s\n"),
                argv[optind]);
            usage();
        }
    }

    if (format & TSK_FS_DCAT_STAT) {
        if (optind == argc)
            usage();

        if (format & (TSK_FS_DCAT_HTML | TSK_FS_DCAT_ASCII |
                TSK_FS_DCAT_HEX)) {
            tsk_fprintf(stderr,
                "NOTE: Additional flags will be ignored\n");
        }
    }
    /* We need at least two more arguments */
    else if (optind + 1 >= argc) {
        tsk_fprintf(stderr, "Missing image name and/or address\n");
        usage();
    }

    if ((format & TSK_FS_DCAT_ASCII) && (format & TSK_FS_DCAT_HEX)) {
        tsk_fprintf(stderr,
            "Ascii and Hex flags can not be used together\n");
        usage();
    }

    /* We need to figure out if there is a length argument... */
    /* Check out the second argument from the end */

    /* default number of units is 1 */
    read_num_units = 1;

    /* Get the block address */
    if (format & TSK_FS_DCAT_STAT) {
        if ((img =
                tsk_img_open(imgtype, argc - optind,
                    (const TSK_TCHAR **) &argv[optind])) == NULL) {
            tsk_error_print(stderr);
            exit(1);
        }

    }
    else {
        addr = TSTRTOULL(argv[argc - 2], &cp, 0);
        if (*cp || *cp == *argv[argc - 2]) {

            /* Not a number, so it is the image name and we do not have a length */
            addr = TSTRTOULL(argv[argc - 1], &cp, 0);
            if (*cp || *cp == *argv[argc - 1]) {
                TFPRINTF(stderr, _TSK_T("Invalid block address: %s\n"),
                    argv[argc - 1]);
                usage();
            }

            if ((img =
                    tsk_img_open(imgtype, argc - optind - 1,
                        (const TSK_TCHAR **) &argv[optind])) == NULL) {
                tsk_error_print(stderr);
                exit(1);
            }

        }
        else {
            /* We got a number, so take the length as well while we are at it */
            read_num_units = TSTRTOULL(argv[argc - 1], &cp, 0);
            if (*cp || *cp == *argv[argc - 1]) {
                TFPRINTF(stderr, _TSK_T("Invalid size: %s\n"),
                    argv[argc - 1]);
                usage();
            }
            else if (read_num_units <= 0) {
                tsk_fprintf(stderr, "Invalid size: %" PRIuDADDR "\n",
                    read_num_units);
                usage();
            }

            if ((img =
                    tsk_img_open(imgtype, argc - optind - 2,
                        (const TSK_TCHAR **) &argv[optind])) == NULL) {

                tsk_error_print(stderr);
                exit(1);
            }
        }
    }

    /* open the file */
    if ((fs = tsk_fs_open(img, imgoff, fstype)) == NULL) {
        tsk_error_print(stderr);
        if (tsk_errno == TSK_ERR_FS_UNSUPTYPE)
            tsk_fs_print_types(stderr);
        img->close(img);
        exit(1);
    }


    /* Set the default size if given */
    if ((usize != 0) &&
        (((fs->ftype & TSK_FS_INFO_TYPE_FS_MASK) ==
                TSK_FS_INFO_TYPE_RAW_TYPE)
            || ((fs->ftype & TSK_FS_INFO_TYPE_FS_MASK) ==
                TSK_FS_INFO_TYPE_SWAP_TYPE))) {

        DADDR_T sectors;
        int orig_dsize, new_dsize;

        if (usize % 512) {
            tsk_fprintf(stderr,
                "New data unit size not a multiple of 512 (%d)\n", usize);
            usage();
        }

        /* We need to do some math to update the block_count value */

        /* Get the original number of sectors */
        orig_dsize = fs->block_size / 512;
        sectors = fs->block_count * orig_dsize;

        /* Convert that to the new size */
        new_dsize = usize / 512;
        fs->block_count = sectors / new_dsize;
        if (sectors % new_dsize)
            fs->block_count++;
        fs->last_block = fs->block_count - 1;

        fs->block_size = usize;
    }

    if (addr > fs->last_block) {
        tsk_fprintf(stderr,
            "Data unit address too large for image (%" PRIuDADDR ")\n",
            fs->last_block);
        fs->close(fs);
        img->close(img);
        exit(1);
    }
    if (addr < fs->first_block) {
        tsk_fprintf(stderr,
            "Data unit address too small for image (%" PRIuDADDR ")\n",
            fs->first_block);
        fs->close(fs);
        img->close(img);
        exit(1);
    }

    if (tsk_fs_dcat(fs, format, addr, read_num_units)) {
        tsk_error_print(stderr);
        fs->close(fs);
        img->close(img);
        exit(1);
    }

    fs->close(fs);
    img->close(img);

    exit(0);
}
