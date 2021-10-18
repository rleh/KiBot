# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 Salvador E. Tropea
# Copyright (c) 2020-2021 Instituto Nacional de Tecnología Industrial
# License: GPL-3.0
# Project: KiBot (formerly KiPlot)
""" Miscellaneous definitions """

import re
import os
from contextlib import contextmanager


# Error levels
INTERNAL_ERROR = 1    # Unhandled exceptions
WRONG_ARGUMENTS = 2   # This is what argsparse uses
USUPPORTED_OPTION = 3
MISSING_TOOL = 4
DRC_ERROR = 5
EXIT_BAD_ARGS = 6
EXIT_BAD_CONFIG = 7
NO_PCB_FILE = 8
NO_SCH_FILE = 9
ERC_ERROR = 10
BOM_ERROR = 11
PDF_SCH_PRINT = 12
PDF_PCB_PRINT = 13
PLOT_ERROR = 14
NO_YAML_MODULE = 15
NO_PCBNEW_MODULE = 16
CORRUPTED_PCB = 17
KICAD2STEP_ERR = 18
WONT_OVERWRITE = 19
PCBDRAW_ERR = 20
SVG_SCH_PRINT = 21
CORRUPTED_SCH = 22
WRONG_INSTALL = 23
error_level_to_name = ['NONE',
                       'INTERNAL_ERROR',
                       'WRONG_ARGUMENTS',
                       'USUPPORTED_OPTION',
                       'MISSING_TOOL',
                       'DRC_ERROR',
                       'EXIT_BAD_ARGS',
                       'EXIT_BAD_CONFIG',
                       'NO_PCB_FILE',
                       'NO_SCH_FILE',
                       'ERC_ERROR',
                       'BOM_ERROR',
                       'PDF_SCH_PRINT',
                       'PDF_PCB_PRINT',
                       'PLOT_ERROR',
                       'NO_YAML_MODULE',
                       'NO_PCBNEW_MODULE',
                       'CORRUPTED_PCB',
                       'KICAD2STEP_ERR',
                       'WONT_OVERWRITE',
                       'PCBDRAW_ERR',
                       'SVG_SCH_PRINT',
                       'CORRUPTED_SCH',
                       'WRONG_INSTALL',
                       ]
CMD_EESCHEMA_DO = 'eeschema_do'
URL_EESCHEMA_DO = 'https://github.com/INTI-CMNB/kicad-automation-scripts'
CMD_PCBNEW_RUN_DRC = 'pcbnew_do'
URL_PCBNEW_RUN_DRC = URL_EESCHEMA_DO
CMD_PCBNEW_PRINT_LAYERS = 'pcbnew_do'
URL_PCBNEW_PRINT_LAYERS = URL_EESCHEMA_DO
CMD_KIBOM = 'KiBOM_CLI.py'
URL_KIBOM = 'https://github.com/INTI-CMNB/KiBoM'
CMD_IBOM = 'generate_interactive_bom.py'
URL_IBOM = 'https://github.com/INTI-CMNB/InteractiveHtmlBom'
CMD_KICOST = 'kicost'
URL_KICOST = 'https://github.com/INTI-CMNB/KiCost'
KICOST_SUBMODULE = '../submodules/KiCost/src/kicost'
KICAD2STEP = 'kicad2step'
PCBDRAW = 'pcbdraw'
URL_PCBDRAW = 'https://github.com/INTI-CMNB/pcbdraw'
EXAMPLE_CFG = 'example_template.kibot.yaml'
AUTO_SCALE = 0
KICAD_VERSION_5_99 = 5099000

# Internal filter names
IFILT_MECHANICAL = '_mechanical'
IFILT_VAR_RENAME = '_var_rename'
IFILT_VAR_RENAME_KICOST = '_var_rename_kicost'
IFILT_ROT_FOOTPRINT = '_rot_footprint'
IFILT_KICOST_RENAME = '_kicost_rename'
IFILT_KICOST_DNP = '_kicost_dnp'
# KiCad 5 GUI values for the attribute
UI_THT = 0       # 1 for KiCad 6
UI_SMD = 1       # 2 for KiCad 6
UI_VIRTUAL = 2   # 12 for KiCad 6
# KiCad 6 module attributes from class_module.h
MOD_THROUGH_HOLE = 1
MOD_SMD = 2
MOD_EXCLUDE_FROM_POS_FILES = 4
MOD_EXCLUDE_FROM_BOM = 8
MOD_BOARD_ONLY = 16  # Footprint has no corresponding symbol
# This is what a virtual component gets when loaded by KiCad 6
MOD_VIRTUAL = MOD_EXCLUDE_FROM_POS_FILES | MOD_EXCLUDE_FROM_BOM

# Supported values for "do not fit"
DNF = {
    "dnf",
    "dnl",
    "dnp",
    "do not fit",
    "do not place",
    "do not load",
    "nofit",
    "nostuff",
    "noplace",
    "noload",
    "not fitted",
    "not loaded",
    "not placed",
    "no stuff",
}
# String matches for marking a component as "do not change" or "fixed"
DNC = {
    "dnc",
    "do not change",
    "no change",
    "fixed",
}
# KiCost distributors
DISTRIBUTORS = ['arrow', 'digikey', 'farnell', 'lcsc', 'mouser', 'newark', 'rs', 'tme']
DISTRIBUTORS_F = [d+'#' for d in DISTRIBUTORS]
# ISO ISO4217 currency codes
# Not all, but the ones we get from the European Central Bank (march 2021)
ISO_CURRENCIES = set(['EUR', 'USD', 'JPY', 'BGN', 'CZK', 'DKK', 'GBP', 'HUF', 'PLN', 'RON', 'SEK', 'CHF', 'ISK', 'NOK', 'HRK',
                      'RUB', 'TRY', 'AUD', 'BRL', 'CAD', 'CNY', 'HKD', 'IDR', 'ILS', 'INR', 'KRW', 'MXN', 'MYR', 'NZD', 'PHP',
                      'SGD', 'THB', 'ZAR'])

W_VARCFG = '(W001) '
W_VARPCB = '(W002) '
W_PYCACHE = '(W003) '
W_FIELDCONF = '(W004) '
W_NOHOME = '(W005) '
W_NOUSER = '(W006) '
W_BADSYS = '(W007) '
W_NOCONFIG = '(W008) '
W_NOKIENV = '(W009) '
W_NOLIBS = '(W010) '
W_NODEFSYMLIB = '(W011) '
W_UNKGLOBAL = '(W012) '
W_PCBNOSCH = '(W013) '
W_NONEEDSKIP = '(W014) '
W_UNKOPS = '(W015) '
W_AMBLIST = '(W016) '
W_UNRETOOL = '(W017) '
W_USESVG2 = '(W018) '
W_USEIMAGICK = '(W019) '
W_BADVAL1 = '(W020) '
W_BADVAL2 = '(W021) '
W_BADVAL3 = '(W022) '
W_BADPOLI = '(W023) '
W_POLICOORDS = '(W024) '
W_BADSQUARE = '(W025) '
W_BADCIRCLE = '(W026) '
W_BADARC = '(W027) '
W_BADTEXT = '(W028) '
W_BADPIN = '(W029) '
W_BADCOMP = '(W030) '
W_BADDRAW = '(W031) '
W_UNKDCM = '(W032) '
W_UNKAR = '(W033) '
W_ARNOPATH = '(W034) '
W_ARNOREF = '(W035) '
W_MISCFLD = '(W036) '
W_EXTRASPC = '(W037) '
W_NOLIB = '(W038) '
W_INCPOS = '(W039) '
W_NOANNO = '(W040) '
W_MISSLIB = '(W041) '
W_MISSDCM = '(W042) '
W_MISSCMP = '(W043) '
W_VARSCH = '(W044) '
W_WRONGPASTE = '(W045) '
W_MISFLDNAME = '(W046) '
W_MISS3D = '(W047) '
W_FAILDL = '(W048) '
W_NOLAYER = '(W049) '
W_EMPTYZIP = '(W050) '
W_WRONGCHAR = '(W051) '
W_NOKIVER = '(W052) '
W_EXTNAME = '(W053) '
W_TIMEOUT = '(W054) '
W_MUSTBEINT = '(W055) '
W_NOOUTPUTS = '(W056) '
W_NOTASCII = '(W057) '
W_KIAUTO = '(W058) '
W_NUMSUBPARTS = '(W059) '
W_PARTMULT = '(W060) '
W_EMPTYREN = '(W061) '
W_BADFIELD = '(W062) '
W_UNKDIST = '(W063) '
W_UNKCUR = '(W064) '
W_NONETLIST = '(W065) '
W_NOKICOST = '(W066) '
W_UNKOUT = '(W067) '
W_NOFILTERS = '(W068) '
W_NOVARIANTS = '(W069) '
W_NOENDLIB = '(W070) '


class Rect(object):
    """ What KiCad returns isn't a real wxWidget's wxRect.
        Here I add what I really need """
    def __init__(self):
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None

    def Union(self, wxRect):
        if self.x1 is None:
            self.x1 = wxRect.x
            self.y1 = wxRect.y
            self.x2 = wxRect.x+wxRect.width
            self.y2 = wxRect.y+wxRect.height
        else:
            self.x1 = min(self.x1, wxRect.x)
            self.y1 = min(self.y1, wxRect.y)
            self.x2 = max(self.x2, wxRect.x+wxRect.width)
            self.y2 = max(self.y2, wxRect.y+wxRect.height)


def name2make(name):
    return re.sub(r'[ \$\.\\\/]', '_', name)


@contextmanager
def hide_stderr():
    """ Low level stderr supression, used to hide KiCad bugs. """
    newstderr = os.dup(2)
    devnull = os.open('/dev/null', os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)
    yield
    os.dup2(newstderr, 2)
