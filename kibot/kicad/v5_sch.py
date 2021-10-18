# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 Salvador E. Tropea
# Copyright (c) 2020-2021 Instituto Nacional de Tecnología Industrial
# License: GPL-3.0
# Project: KiBot (formerly KiPlot)
"""
KiCad v5 (and older) Schematic format.
A basic implementation of the .sch file format.
Currently oriented to collect the components for the BoM.
"""
# Encapsulate file/line
import re
import os
from datetime import datetime
from copy import deepcopy
from collections import OrderedDict
from .config import KiConf, un_quote
from ..gs import GS
from ..misc import (W_BADPOLI, W_POLICOORDS, W_BADSQUARE, W_BADCIRCLE, W_BADARC, W_BADTEXT, W_BADPIN, W_BADCOMP, W_BADDRAW,
                    W_UNKDCM, W_UNKAR, W_ARNOPATH, W_ARNOREF, W_MISCFLD, W_EXTRASPC, W_NOLIB, W_INCPOS, W_NOANNO, W_MISSLIB,
                    W_MISSDCM, W_MISSCMP, W_MISFLDNAME, W_NOENDLIB)
from .. import log

logger = log.get_logger(__name__)


class SchError(Exception):
    pass


class SchFileError(SchError):
    def __init__(self, msg, code, reader):
        super().__init__()
        self.line = reader.line
        self.file = reader.file
        self.msg = msg
        self.code = code


class SchLibError(SchFileError):
    def __init__(self, msg, code, reader):
        super().__init__(msg, code, reader)


class LineReader(object):
    def __init__(self, f, file):
        super().__init__()
        self.line = 0
        self.file = file
        self.f = f


class SCHLineReader(LineReader):
    def __init__(self, f, file):
        super().__init__(f, file)

    def get_line(self):
        res = self.f.readline()
        if not res:
            raise SchFileError('Unexpected end of file', '', self)
        self.line += 1
        return res.rstrip()


class LibLineReader(LineReader):
    def __init__(self, f, file):
        super().__init__(f, file)

    def get_line(self):
        res = self.f.readline()
        while res and res[0] == '#':
            if res.startswith('#End Library') or res.startswith('# End Library'):
                return res.rstrip()
            self.line += 1
            res = self.f.readline()
        if not res:
            raise SchLibError('Unexpected end of file', '', self)
        self.line += 1
        return res.rstrip()


class DCMLineReader(LineReader):
    def __init__(self, f, file):
        super().__init__(f, file)

    def get_line(self):
        res = self.f.readline()
        while res and res[0] == '#':
            if res.startswith('#End Doc Library'):
                return res.rstrip()
            self.line += 1
            res = self.f.readline()
        if not res:
            raise SchLibError('Unexpected end of file', '', self)
        self.line += 1
        return res.rstrip()


def _split_space(s):
    res = s.lstrip().split(' ')
    return [a for a in res if a]


class LibComponentField(object):
    """ A field for a component in the library.
        Almost the same as a field in the schematic, but incompatible!!! """
    # F n "text" posx posy dimension orientation visibility hjustify vjustify/italic/bold "name"
    field_re = re.compile(r'F\s*(\d+)\s+'  # 0 Field number
                          r'"([^"]*)"\s+'  # 1 Field value
                          r'(-?\d+)\s+'    # 2 Pos X
                          r'(-?\d+)\s+'    # 3 Pos Y
                          r'(\d+)\s+'      # 4 Dimension
                          r'([HV])\s+'     # 5 Orientation
                          r'([VI])\s+'     # 6 Visibility
                          r'([LRCBT])\s+'  # 7 HJustify
                          r'([LRCBT][IN][BN])\s*'  # 8 VJustify+Italic+Bold
                          r'("[^"]*")?')   # 9 Name for user fields

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line, lib_name, f):
        m = LibComponentField.field_re.match(line)
        if not m:
            raise SchLibError('Malformed component field', line, f)
        field = LibComponentField()
        gs = m.groups()
        field.number = int(gs[0])
        field.value = gs[1]
        field.x = int(gs[2])
        field.y = int(gs[3])
        field.size = int(gs[4])
        field.horizontal = gs[5] == 'H'  # H -> True, V -> False
        field.visible = gs[6] == 'V'
        field.hjustify = gs[7]
        field.vjustify = gs[8][0]
        field.italic = gs[8][1] == 'I'
        field.bold = gs[8][2] == 'B'
        if gs[9]:
            field.name = gs[9][1:-1]
        else:
            if field.number > 3:
                logger.warning(W_MISFLDNAME + 'Missing component field name ({} line {})'.format(lib_name, f.line))
                # KiCad falls-back to `FieldN`
                field.name = 'Field'+str(field.number)
            else:
                field.name = ['Reference', 'Value', 'Footprint', 'Datasheet'][field.number]
        return field

    def write(self, f):
        s = 'F'+str(self.number)
        s += ' "{}" {} {} {} '.format(self.value, self.x, self.y, self.size)
        s += 'H' if self.horizontal else 'V'
        s += ' '
        s += 'V' if self.visible else 'I'
        s += ' '+self.hjustify+' '+self.vjustify
        s += 'I' if self.italic else 'N'
        s += 'B' if self.bold else 'N'
        if self.number > 3:
            s += ' "'+self.name+'"'
        f.write(s+'\n')


class DrawPoligon(object):
    pol_re = re.compile(r'P\s+(\d+)\s+'     # 0 Number of points
                        r'(\d+)\s+'         # 1 Sub-part (0 == all)
                        r'([012])\s+'       # 2 Which representation (0 == both) for DeMorgan
                        r'(-?\d+)\s+'       # 3 Thickness (Components from 74xx.lib has poligons with -1000)
                        r'((?:-?\d+\s+)+)'  # 4 The points
                        r'([NFf])')         # 5 Normal, Filled

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line):
        m = DrawPoligon.pol_re.match(line)
        if not m:
            logger.warning(W_BADPOLI + 'Unknown poligon definition `{}`'.format(line))
            return None
        pol = DrawPoligon()
        g = m.groups()
        pol.points = int(g[0])
        pol.sub_part = int(g[1])
        pol.convert = int(g[2])
        pol.thickness = int(g[3])
        pol.fill = g[5]
        coords = _split_space(g[4])
        if len(coords) != 2*pol.points:
            logger.warning(W_POLICOORDS + 'Expected {} coordinates and got {} in poligon'.format(2*pol.points, len(coords)))
            pol.points = int(len(coords)/2)
        pol.coords = [int(c) for c in coords]
        return pol

    def write(self, f):
        f.write('P {} {} {} {}'.format(self.points, self.sub_part, self.convert, self.thickness))
        for p in self.coords:
            f.write(' '+str(p))
        f.write(' '+self.fill+'\n')

    def get_rect(self):
        if not self.points:
            return 0, 0, 0, 0, False
        xm = xM = self.coords[0]
        ym = yM = self.coords[1]
        for i in range(1, self.points):
            x = self.coords[i*2]
            y = self.coords[i*2+1]
            xm = min(x, xm)
            xM = max(x, xM)
            ym = min(y, ym)
            yM = max(y, yM)
        return xm, ym, xM, yM, True


class DrawRectangle(object):
    rec_re = re.compile(r'S\s+'
                        r'(-?\d+)\s+'   # 0 Start X
                        r'(-?\d+)\s+'   # 1 Start Y
                        r'(-?\d+)\s+'   # 2 End X
                        r'(-?\d+)\s+'   # 3 End X
                        r'(\d+)\s+'     # 4 Sub-part (0 == all)
                        r'([012])\s+'   # 5 Which representation (0 == both) for DeMorgan
                        r'(\d+)\s+'     # 6 Thickness
                        r'([NFf])')     # 7 Normal, Filled

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line):
        m = DrawRectangle.rec_re.match(line)
        if not m:
            logger.warning(W_BADSQUARE + 'Unknown square definition `{}`'.format(line))
            return None
        rec = DrawRectangle()
        g = m.groups()
        rec.start_x = int(g[0])
        rec.start_y = int(g[1])
        rec.end_x = int(g[2])
        rec.end_y = int(g[3])
        rec.sub_part = int(g[4])
        rec.convert = int(g[5])
        rec.thickness = int(g[6])
        rec.fill = g[7]
        return rec

    def write(self, f):
        f.write('S {} {} {} {}'.format(self.start_x, self.start_y, self.end_x, self.end_y))
        f.write(' {} {} {} {}\n'.format(self.sub_part, self.convert, self.thickness, self.fill))

    def get_rect(self):
        xm = min(self.start_x, self.end_x)
        ym = min(self.start_y, self.end_y)
        xM = max(self.start_x, self.end_x)
        yM = max(self.start_y, self.end_y)
        return xm, ym, xM, yM, True


class DrawCircle(object):
    cir_re = re.compile(r'C\s+'
                        r'(-?\d+)\s+'   # 0 Pos X
                        r'(-?\d+)\s+'   # 1 Pos Y
                        r'(\d+)\s+'     # 2 Radius
                        r'(\d+)\s+'     # 3 Sub-part (0 == all)
                        r'([012])\s+'   # 4 Which representation (0 == both) for DeMorgan
                        r'(\d+)\s+'     # 5 Thickness
                        r'([NFf])')     # 6 Normal, Filled

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line):
        m = DrawCircle.cir_re.match(line)
        if not m:
            logger.warning(W_BADCIRCLE + 'Unknown circle definition `{}`'.format(line))
            return None
        cir = DrawCircle()
        g = m.groups()
        cir.pos_x = int(g[0])
        cir.pos_y = int(g[1])
        cir.radius = int(g[2])
        cir.sub_part = int(g[3])
        cir.convert = int(g[4])
        cir.thickness = int(g[5])
        cir.fill = g[6]
        return cir

    def write(self, f):
        f.write('C {} {} {}'.format(self.pos_x, self.pos_y, self.radius))
        f.write(' {} {} {} {}\n'.format(self.sub_part, self.convert, self.thickness, self.fill))

    def get_rect(self):
        xm = self.pos_x-self.radius
        ym = self.pos_y-self.radius
        xM = self.pos_x+self.radius
        yM = self.pos_y+self.radius
        return xm, ym, xM, yM, True


class DrawArc(object):
    arc_re = re.compile(r'A\s+'
                        r'(-?\d+)\s+'   # 0 Pos X
                        r'(-?\d+)\s+'   # 1 Pos Y
                        r'(\d+)\s+'     # 2 Radius
                        r'(-?\d+)\s+'   # 3 Start
                        r'(-?\d+)\s+'   # 4 End
                        r'(\d+)\s+'     # 5 Sub-part (0 == all)
                        r'([012])\s+'   # 6 Which representation (0 == both) for DeMorgan
                        r'(\d+)\s+'     # 7 Thickness
                        r'([NFf])\s+'   # 8 Normal, Filled
                        r'(-?\d+)\s+'   # 9 Start Pos X
                        r'(-?\d+)\s+'   # 10 Start Pos Y
                        r'(-?\d+)\s+'   # 11 End Pos X
                        r'(-?\d+)')     # 12 End Pos Y

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line):
        m = DrawArc.arc_re.match(line)
        if not m:
            logger.warning(W_BADARC + 'Unknown arc definition `{}`'.format(line))
            return None
        arc = DrawArc()
        g = m.groups()
        arc.pos_x = int(g[0])
        arc.pos_y = int(g[1])
        arc.radius = int(g[2])
        arc.start = int(g[3])
        arc.end = int(g[4])
        arc.sub_part = int(g[5])
        arc.convert = int(g[6])
        arc.thickness = int(g[7])
        arc.fill = g[8]
        arc.start_x = int(g[9])
        arc.start_y = int(g[10])
        arc.end_x = int(g[11])
        arc.end_y = int(g[12])
        return arc

    def write(self, f):
        f.write('A {} {} {}'.format(self.pos_x, self.pos_y, self.radius))
        f.write(' {} {}'.format(self.start, self.end))
        f.write(' {} {} {} {}'.format(self.sub_part, self.convert, self.thickness, self.fill))
        f.write(' {} {} {} {}\n'.format(self.start_x, self.start_y, self.end_x, self.end_y))

    def get_rect(self):
        xm = self.pos_x-self.radius
        ym = self.pos_y-self.radius
        xM = self.pos_x+self.radius
        yM = self.pos_y+self.radius
        return xm, ym, xM, yM, True


class DrawText(object):
    txt_re = re.compile(r'T\s+'
                        r'(\d+)\s+'                  # 0 Orientation (0 horizontal)
                        r'(-?\d+)\s+'                # 1 Pos X
                        r'(-?\d+)\s+'                # 2 Pos Y
                        r'(\d+)\s+'                  # 3 Dimension
                        r'(\d+)\s+'                  # 4 Type?
                        r'(\d+)\s+'                  # 5 Sub-part (0 == all)
                        r'([012])\s+'                # 6 Which representation (0 == both) for DeMorgan
                        r'(\S+|"(?:[^"]|\\")+")\s+'  # 7 Text
                        r'(Normal|Italic)\s+'        # 8 Italic
                        r'([01])\s+'                 # 9 Bold
                        r'([CLR])\s+'                # 10 HJustify
                        r'([CBT])')                  # 11 VJustify

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line):
        m = DrawText.txt_re.match(line)
        if not m:
            logger.warning(W_BADTEXT + 'Unknown text definition `{}`'.format(line))
            return None
        txt = DrawText()
        g = m.groups()
        txt.orientation = int(g[0])
        txt.pos_x = int(g[1])
        txt.pos_y = int(g[2])
        txt.size = int(g[3])
        txt.type = int(g[4])
        txt.sub_part = int(g[5])
        txt.convert = int(g[6])
        txt.text = un_quote(g[7])
        txt.italic = g[8] == 'Italic'
        txt.bold = g[9] == '1'
        txt.hjustify = g[10]
        txt.vjustify = g[11]
        return txt

    def write(self, f):
        f.write('T {} {} {} {}'.format(self.orientation, self.pos_x, self.pos_y, self.size))
        f.write(' {} {} {} "{}"'.format(self.type, self.sub_part, self.convert, self.text))
        f.write(' {} {} {} {}\n'.format(['Normal', 'Italic'][self.italic], int(self.bold), self.hjustify, self.vjustify))

    def get_rect(self):
        return 0, 0, 0, 0, False


class Pin(object):
    pin_re = re.compile(r'X\s+'
                        r'(\S+)\s+'         # 0 Name (~ for empty)
                        r'(\S+)\s+'         # 1 "Number" (alphanumeric)
                        r'(-?\d+)\s+'       # 2 Pos X
                        r'(-?\d+)\s+'       # 3 Pos Y
                        r'(\d+)\s+'         # 4 Length
                        r'([RLUD])\s+'      # 5 Direction
                        r'(\d+)\s+'         # 6 Text size for the pin name
                        r'(\d+)\s+'         # 7 Text size for the pin number
                        r'(\d+)\s+'         # 8 Sub-part (0 == all)
                        r'([012])\s+'       # 9 Which representation (0 == both) for DeMorgan
                        r'([IOBTPUWwCEN])'  # 10 Electrical type
                        r'((?:\s+)\S+)?')   # 11 Graphic type

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line):
        m = Pin.pin_re.match(line)
        if not m:
            logger.warning(W_BADPIN + 'Unknown pin definition `{}`'.format(line))
            return None
        pin = Pin()
        g = m.groups()
        pin.name = g[0]
        pin.number = g[1]
        pin.pos_x = int(g[2])
        pin.pos_y = int(g[3])
        pin.len = int(g[4])
        pin.dir = g[5]
        pin.size_name = int(g[6])
        pin.size_num = int(g[7])
        pin.sub_part = int(g[8])
        pin.convert = int(g[9])
        pin.type = g[10]
        pin.gtype = g[11]
        return pin

    def write(self, f):
        f.write('X {} {} {} {}'.format(self.name, self.number, self.pos_x, self.pos_y))
        f.write(' {} {} {} {}'.format(self.len, self.dir, self.size_name, self.size_num))
        f.write(' {} {} {}'.format(self.sub_part, self.convert, self.type))
        if self.gtype:
            f.write(' '+self.gtype)
        f.write('\n')

    def get_rect(self):
        if self.dir == 'U':
            return self.pos_x, self.pos_y, self.pos_x, self.pos_y+self.len, True
        if self.dir == 'D':
            return self.pos_x, self.pos_y-self.len, self.pos_x, self.pos_y, True
        if self.dir == 'R':
            return self.pos_x, self.pos_y, self.pos_x+self.len, self.pos_y, True
        if self.dir == 'L':
            return self.pos_x-self.len, self.pos_y, self.pos_x, self.pos_y, True
        return 0, 0, 0, 0, False


class LibComponent(object):
    def_re = re.compile(r'DEF\s+'
                        r'(\S+)\s+'     # 0 Name
                        r'(\S+)\s+'     # 1 Reference prefix
                        r'(\S+)\s+'     # 2 Unused field (0)
                        r'(-?\d+)\s+'   # 3 Text offset
                        r'([YN])\s+'    # 4 Draw pin number
                        r'([YN])\s+'    # 5 Draw pin name
                        r'(\d+)\s+'     # 6 Unit count
                        r'([LF])\s+'    # 7 Unit is locked
                        r'([NP])')      # 8 Power/Normal

    def __init__(self, line, f, lib_name):
        super().__init__()
        self.dcm = None  # Extra info from the Doc-Lib (DCM) file
        m = self.def_re.match(line)
        if m:
            g = m.groups()
            self.name = g[0]
            self.ref_prefix = g[1]
            self.unused = g[2]
            self.text_offset = int(g[3])
            self.draw_pinnumber = g[4] == 'Y'
            self.draw_pinname = g[5] == 'Y'
            self.unit_count = int(g[6])
            self.units_locked = g[7] == 'L'
            self.is_power = g[8] == 'P'
            if self.name[0] == '~':
                self.name = self.name[1:]
                self.vname = True
            else:
                self.vname = False
            if GS.debug_level > 2:
                logger.debug('- Loading component {} from {}'.format(self.name, lib_name))
        else:
            logger.warning(W_BADCOMP + 'Failed to load component definition: `{}`'.format(line))
            # Mark it as broken
            self.name = None
        self.fields = []
        self.dfields = {}
        self.alias = None
        self.fp_list = []
        self.draw = []
        line = f.get_line()
        while not line.startswith('ENDDEF'):
            if len(line) == 0:
                # Skip empty lines
                line = f.get_line()
                continue
            if line[0] == 'F':
                # A field
                field = LibComponentField.parse(line, lib_name, f)
                self.fields.append(field)
                self.dfields[field.name.lower()] = field
            elif line.startswith('ALIAS'):
                self.alias = _split_space(line[6:])
            elif line.startswith('$FPLIST'):
                line = f.get_line()
                while not line.startswith('$ENDFPLIST'):
                    self.fp_list.append(line[1:])
                    line = f.get_line()
            elif line.startswith('DRAW'):
                line = f.get_line()
                while not line.startswith('ENDDRAW'):
                    if line[0] == 'P':
                        self.draw.append(DrawPoligon.parse(line))
                    elif line[0] == 'S':
                        self.draw.append(DrawRectangle.parse(line))
                    elif line[0] == 'C':
                        self.draw.append(DrawCircle.parse(line))
                    elif line[0] == 'A':
                        self.draw.append(DrawArc.parse(line))
                    elif line[0] == 'T':
                        self.draw.append(DrawText.parse(line))
                    elif line[0] == 'X':
                        self.draw.append(Pin.parse(line))
                    else:
                        logger.warning(W_BADDRAW + 'Unknown draw element `{}`'.format(line))
                    line = f.get_line()
            line = f.get_line()

    def write(self, f, id, cross=False):
        """ cross is used to cross the component (DNF) """
        id = id.replace(':', '_')
        if self.vname:
            id = '~'+id
        f.write('#\n# '+id+'\n#\n')
        f.write('DEF {} {} {} {} {} {} {} {} {}\n'.
                format(id, self.ref_prefix, self.unused, self.text_offset, ['N', 'Y'][self.draw_pinnumber],
                       ['N', 'Y'][self.draw_pinname], self.unit_count, ['F', 'L'][self.units_locked],
                       ['N', 'P'][self.is_power]))
        for field in self.fields:
            field.write(f)
        f.write('$FPLIST\n')
        for fp in self.fp_list:
            f.write(' '+fp+'\n')
        f.write('$ENDFPLIST\n')
        if self.alias:
            f.write('ALIAS '+' '.join(self.alias)+'\n')
        f.write('DRAW\n')
        for dr in self.draw:
            dr.write(f)
        if cross:
            # Generated the crossed stuff
            # logger.debug('Computing size for {}:'.format(id))
            for unit in range(self.unit_count):
                xmt = ymt = 1e6
                xMt = yMt = -1e6
                ok_t = False
                # logger.debug("Unit "+str(unit+1))
                for dr in self.draw:
                    if dr.sub_part != unit + 1 and dr.sub_part != 0:
                        continue
                    xm, ym, xM, yM, ok = dr.get_rect()
                    # logger.debug([dr, xm, ym, xM, yM, ok])
                    if ok:
                        ok_t = True
                        xmt = min(xm, xmt)
                        ymt = min(ym, ymt)
                        xMt = max(xM, xMt)
                        yMt = max(yM, yMt)
                if ok_t:
                    # Cross this component using 2 lines
                    o = DrawPoligon()
                    o.points = 2
                    o.sub_part = unit+1
                    o.convert = 0
                    o.thickness = 30
                    o.fill = 'N'
                    o.coords = [xmt, ymt, xMt, yMt]
                    o.write(f)
                    o.coords = [xmt, yMt, xMt, ymt]
                    o.write(f)
        f.write('ENDDRAW\n')
        f.write('ENDDEF\n')


#     def __repr__(self):
#         s = 'Component('+self.name
#         if self.desc:
#             s += " desc: '{}'".format(self.desc)
#         s += ')'
#         return s


class SymLib(object):
    """ Content from a symbols library """
    def __init__(self):
        super().__init__()
        self.comps = OrderedDict()
        self.alias = {}

    @staticmethod
    def _check_add(o, id, lib, needed, translate):
        if lib is None:
            # From a cache
            if id in translate:
                needed[translate[id]] = o
                return True
            return False
        name = lib+':'+id
        if name in needed:
            needed[name] = o
            return True
        else:
            name = 'None:'+id
            if name in needed:
                needed[name] = o
                return True
        return False

    def load(self, file, lib_alias, needed):
        """ Populates the class, file must exist """
        logger.debug('Loading library `{}`'.format(file))
        with open(file, 'rt') as fh:
            f = LibLineReader(fh, file)
            line = f.get_line()
            if not line.startswith('EESchema-LIBRARY'):
                raise SchLibError('Missing library signature', line, f)
            line = f.get_line()
            translate = {k.replace(':', '_'): k for k, v in needed.items() if v is None} if lib_alias is None else None
            while not (line.startswith('#End Library') or line.startswith('# End Library')):
                if line.startswith('DEF'):
                    o = LibComponent(line, f, file)
                    if o.name:
                        # Only add components we need
                        if self._check_add(o, o.name, lib_alias, needed, translate):
                            self.comps[o.name] = o
                        if o.alias and lib_alias is not None:
                            for a in o.alias:
                                if self._check_add(o, a, lib_alias, needed, translate):
                                    self.alias[a] = o
                else:
                    raise SchLibError('Unknown library entry', line, f)
                try:
                    line = f.get_line()
                except SchLibError:
                    logger.warning(W_NOENDLIB + 'Library without end of file comment: `{}`'.format(file))
                    break


class DocLibEntry(object):
    def __init__(self, name, f):
        super().__init__()
        self.name = name
        self.desc = None
        self.keys = None
        self.datasheet = None
        line = f.get_line()
        while not line.startswith('$ENDCMP'):
            if line[0] == 'D':
                self.desc = line[2:].lstrip()
            elif line[0] == 'K':
                self.keys = _split_space(line[2:])
            elif line[0] == 'F':
                self.datasheet = line[2:].lstrip()
            else:
                logger.warning(W_UNKDCM + 'Unknown DCM attribute `{}` on line {}'.format(line, f.line))
            line = f.get_line()

    def __repr__(self):
        s = 'DCM('+self.name
        if self.desc:
            s += " desc: '{}'".format(self.desc)
        s += ')'
        return s


class DocLib(object):
    """ Content from a DCM """
    def __init__(self):
        super().__init__()
        self.comps = OrderedDict()

    def load(self, file):
        """ Populates the class, file must exist """
        logger.debug('Loading doc-lib `{}`'.format(file))
        with open(file, 'rt') as fh:
            f = DCMLineReader(fh, file)
            line = f.get_line()
            if not line.startswith('EESchema-DOCLIB'):
                raise SchLibError('Missing DCM signature', line, f)
            line = f.get_line()
            while not line.startswith('#End Doc Library'):
                if line.startswith('$CMP'):
                    o = DocLibEntry(line[5:].lstrip(), f)
                    self.comps[o.name] = o
                    if GS.debug_level > 1:
                        logger.debug('- '+repr(o))
                else:
                    raise SchLibError('Unknown DCM entry', line, f)
                line = f.get_line()


class SchematicField(object):
    # F n "text" orientation posx posy dimension flags hjustify vjustify/italic/bold "name"
    field_re = re.compile(r'F\s*(\d+)\s+"([^"]*)"\s+([HV])\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)'
                          r'\s+([LRCBT])\s+([LRCBT][IN][BN])\s*("[^"]*")?')

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line, f):
        m = SchematicField.field_re.match(line)
        if not m:
            raise SchFileError('Malformed component field', line, f)
        field = SchematicField()
        gs = m.groups()
        field.number = int(gs[0])
        field.value = gs[1]
        field.horizontal = gs[2] == 'H'  # H -> True, V -> False
        field.x = int(gs[3])
        field.y = int(gs[4])
        field.size = int(gs[5])
        field.flags = gs[6]
        field.hjustify = gs[7]
        field.vjustify = gs[8][0]
        field.italic = gs[8][1] == 'I'
        field.bold = gs[8][2] == 'B'
        if gs[9]:
            field.name = gs[9][1:-1]
        else:
            if field.number > 3:
                raise SchFileError('Missing component field name', line, f)
            field.name = ['Reference', 'Value', 'Footprint', 'Datasheet'][field.number]
        return field

    def write(self, f):
        f.write('F {} "{}" {}'.format(self.number, self.value, ['V', 'H'][self.horizontal]))
        f.write(' {} {} {} {}'.format(self.x, self.y, self.size, self.flags))
        f.write(' {} {}{}{}'.format(self.hjustify, self.vjustify, ['N', 'I'][self.italic], ['N', 'B'][self.bold]))
        if self.number > 3:
            f.write(' "{}"'.format(self.name))
        f.write('\n')

    def __str__(self):
        return self.name+'='+self.value


class SchematicAltRef():
    def __init__(self):
        super().__init__()
        self.path = None
        self.ref = None
        self.part = None

    @staticmethod
    def parse(line):
        ar = SchematicAltRef()
        res = _split_space(line[3:])
        for r in res:
            if r.startswith('Path='):
                ar.path = r[6:-1]
            elif r.startswith('Ref='):
                ar.ref = r[5:-1]
            elif r.startswith('Part='):
                ar.part = r[6:-1]
            else:
                logger.warning(W_UNKAR + 'Unknown AR field `{}`'.format(r))
        if not ar.path:
            logger.warning(W_ARNOPATH + 'Alternative Reference without path `{}`'.format(line))
        if not ar.ref:
            logger.warning(W_ARNOREF + 'Alternative Reference without reference `{}`'.format(line))
        return ar

    def write(self, f):
        f.write('AR')
        if self.path:
            f.write(' Path="{}"'.format(self.path))
        if self.ref:
            f.write(' Ref="{}"'.format(self.ref))
        if self.part:
            f.write(' Part="{}"'.format(self.part))
        f.write('\n')


class SchematicComponent(object):
    """ Class for a component in the schematic.
        Here are special members currently computed elsehere:
        - fitted: equivalent to 'Exclude from board' but inverted
                  - Solded: only if True
                  - BoM normal: only if True
                  - BoM DNF: only if False
        - included: related to 'Exclude from BoM' but inverted,
                   but also applied to other situations.
                  - Solded: doesn't affected
                  - BoM normal: only if True
                  - BoM DNF: only if True (and fitted is False)
        - fixed: means you can't change it by a replacement without authorization
                 Is just a flag and doesn't affect much.
        - footprint_rot: angle to rotate the part in the pick & place.
        - qty: ammount of this part used.
        """
    ref_re = re.compile(r'([^\d]+)([\?\d]+)')

    def __init__(self):
        super().__init__()
        self.field_ref = ''
        self.value = ''
        self.footprint = ''
        self.datasheet = ''
        self.desc = ''
        self.fields = []
        self.dfields = {}
        self.fields_bkp = None
        self.dfields_bkp = None
        # Will be computed
        self.fitted = True
        self.included = True
        self.fixed = False
        self.bottom = False
        self.footprint_rot = 0.0
        self.qty = 1
        self.annotation_error = False
        # KiCad 5 PCB flags (mutually exclusive)
        self.smd = False
        self.virtual = False
        self.tht = False

    def get_field_value(self, field):
        field = field.lower()
        if field in self.dfields:
            return self.dfields[field].value
        return ''

    def is_field(self, field):
        return field in self.dfields

    def get_free_field_number(self):
        """ Looks for a field number that isn't currently in use """
        max_num = -1
        for f in self.fields:
            if f.number > max_num:
                max_num = f.number
        return max_num+1

    def set_field(self, field, value):
        """ Change the value for an existing field """
        field_lc = field.lower()
        if field_lc in self.dfields:
            target = self.dfields[field_lc]
            target.value = value
            # Adjust special fields
            if target.number < 4:
                self._solve_fields(LineReader(None, '**Internal**'))
        else:
            f = SchematicField()
            f.name = field
            f.value = value
            f.number = self.get_free_field_number()
            self.add_field(f)

    def get_field_names(self):
        """ List of all the available field names for this component """
        return self.dfields.keys()

    def get_user_fields(self):
        """ Returns a list of tuples with the user defined fields (name, value) """
        return [(f.name, f.value) for f in self.fields if f.number > 3]

    def add_field(self, field):
        self.fields.append(field)
        self.dfields[field.name.lower()] = field

    def rename_field(self, old_name, new_name):
        old_name = old_name.lower()
        field = self.dfields[old_name]
        field.name = new_name
        del self.dfields[old_name]
        self.dfields[new_name.lower()] = field

    def back_up_fields(self):
        """ First call makes a back-up of the fields.
            Next calls restores the back-up. """
        if self.fields_bkp:
            # We have a back-up, restore from it
            self.fields = deepcopy(self.fields_bkp)
            self.dfields = {f.name.lower(): f for f in self.fields}
            self._solve_fields(LineReader(None, '**Internal**'))
        else:
            # No back-up. Make one for the next reset
            self.fields_bkp = deepcopy(self.fields)
            self.dfields_bkp = {f.name.lower(): f for f in self.fields_bkp}

    def _solve_ref(self, path):
        """ Look fo the correct reference for this path.
            Returns the default reference if no paths defined.
            Returns the first not empty reference if the current is empty. """
        ref = self.f_ref
        # If the reference is empty try the reference field
        if ref[-1] == '?' and self.field_ref and self.field_ref[-1] != '?':
            ref = self.fields[0].value
        if self.ar:
            path += '/'+self.id
            for o in self.ar:
                if o.path == path and o.ref[-1] != '?':
                    return o.ref
                if ref[-1] == '?' and o.ref[-1] != '?':
                    ref = o.ref
        return ref

    def _solve_fields(self, fr):
        """ Fills the default fields from the fields attribute """
        f = self.fields
        self.field_ref = None
        self.value = None
        self.footprint = None
        self.footprint_lib = None
        self.datasheet = None
        basic = 0
        for f in self.fields:
            if f.number == 0:
                self.field_ref = f.value
                basic += 1
            elif f.number == 1:
                self.value = f.value
                basic += 1
            elif f.number == 2:
                res = f.value.split(':')
                cres = len(res)
                if cres == 1:
                    self.footprint = res[0]
                elif cres == 2:
                    self.footprint_lib = res[0]
                    self.footprint = res[1]
                else:
                    raise SchFileError('Footprint with more than one colon', f.value, fr)
                basic += 1
            elif f.number == 3:
                self.datasheet = f.value
                basic += 1
        if basic < 4:
            logger.warning(W_MISCFLD + 'Component `{}` without the basic fields'.format(self.f_ref))

    def _validate(self):
        for field in self.fields:
            cur_val = field.value
            stripped_val = cur_val.strip()
            if len(cur_val) != len(stripped_val):
                logger.warning(W_EXTRASPC + "Field {} of component {} contains extra spaces: `{}` removing them.".
                               format(field.name, self, field.value))
                field.value = stripped_val

    def __str__(self):
        ref = self.ref
        # Add the sub-part id
        # How to know if unit 1 is A?
        if self.unit > 1:
            ref += chr(ord('A')+self.unit-1)
        if self.name == self.value:
            return '{} ({})'.format(ref, self.name)
        return '{} ({} {})'.format(ref, self.name, self.value)

    @staticmethod
    def load(f, project, sheet_path, sheet_path_h, libs, fields, fields_lc):
        # L lib:name reference
        line = f.get_line()
        if not line or line[0] != 'L':
            raise SchFileError('Missing component label', line, f)
        res = _split_space(line[2:])
        if len(res) != 2:
            raise SchFileError('Malformed component label', line, f)
        comp = SchematicComponent()
        comp.project = project
        comp.name, comp.f_ref = res
        res = comp.name.split(':')
        comp.lib = None
        if len(res) == 2:
            comp.name = res[1]
            comp.lib = res[0]
            libs[comp.lib] = None
        else:
            logger.warning(W_NOLIB + "Component `{}` doesn't specify its library".format(comp.name))
        # U N mm time_stamp
        line = f.get_line()
        if line[0] != 'U':
            raise SchFileError('Missing component unit', line, f)
        res = _split_space(line[2:])
        if len(res) != 3:
            raise SchFileError('Malformed component unit', line, f)
        comp.unit = int(res[0])
        comp.unit2 = int(res[1])
        comp.id = res[2]
        # P x y
        line = f.get_line()
        if line[0] != 'P':
            raise SchFileError('Missing component position', line, f)
        res = _split_space(line[2:])
        if len(res) != 2:
            raise SchFileError('Malformed component position', line, f)
        comp.x = int(res[0])
        comp.y = int(res[1])
        # Optional "Alternative References"
        line = f.get_line()
        comp.ar = []
        while line[:2] == 'AR':
            comp.ar.append(SchematicAltRef.parse(line))
            line = f.get_line()
        # F field_number "text" orientation posX posY size Flags (see below) hjustify vjustify/italic/bold "name"
        while line[0] == 'F':
            field = SchematicField.parse(line, f)
            name_lc = field.name.lower()
            # Add to the global collection
            if name_lc not in fields_lc:
                fields.append(field.name)
                fields_lc.add(name_lc)
            # Add to the component
            comp.add_field(field)
            line = f.get_line()
        # Fake 'Part' field
        field = SchematicField()
        field.name = 'part'
        field.value = comp.name
        field.number = -1
        comp.add_field(field)
        # Redundant pos
        if not line.startswith('\t'+str(comp.unit)):
            raise SchFileError('Missing component redundant position', line, f)
        res = _split_space(line[1:])
        if len(res) != 3:
            raise SchFileError('Malformed component redundant position', line, f)
        xr = int(res[1])
        yr = int(res[2])
        if comp.x != xr or comp.y != yr:
            logger.warning(W_INCPOS + 'Inconsistent position for component {} ({},{} vs {},{})'.
                           format(comp.f_ref, comp.x, comp.y, xr, yr))
        # Orientation matrix
        line = f.get_line()
        if line[0] != '\t':
            raise SchFileError('Missing component orientation matrix', line, f)
        res = _split_space(line[1:])
        if len(res) != 4:
            raise SchFileError('Malformed component orientation matrix', line, f)
        comp.matrix = [int(v) for v in res]
        line = f.get_line()
        while not line.startswith('$EndComp'):
            line = f.get_line()
        comp._solve_fields(f)
        comp.ref = comp._solve_ref(sheet_path)
        # Power, ground or power flag
        comp.is_power = comp.ref.startswith('#PWR') or comp.ref.startswith('#FLG')
        if comp.ref[-1] == '?':
            logger.warning(W_NOANNO + 'Component {} is not annotated'.format(comp))
            comp.annotation_error = True
        # Separate the reference in its components
        m = SchematicComponent.ref_re.match(comp.ref)
        if not m:
            raise SchFileError('Malformed component reference', comp.ref, f)
        comp.ref_prefix, comp.ref_suffix = m.groups()
        # Location in the project
        comp.sheet_path = sheet_path
        comp.sheet_path_h = sheet_path_h
        if GS.debug_level > 1:
            logger.debug("- Loaded component {}".format(comp))
        # Report abnormal situations
        comp._validate()
        return comp

    def write(self, f):
        # Fake lib to reflect fitted status
        lib = 'y' if self.fitted or not self.included else 'n'
        # Fake name using cache style
        name = '{}:{}_{}'.format(lib, self.lib, self.name)
        f.write('$Comp\n')
        f.write('L {} {}\n'.format(name, self.f_ref))
        f.write('U {} {} {}\n'.format(self.unit, self.unit2, self.id))
        f.write('P {} {}\n'.format(self.x, self.y))
        for ar in self.ar:
            ar.write(f)
        for field in self.fields:
            if field.number >= 0:
                field.write(f)
        f.write('\t{} {} {}\n'.format(self.unit, self.x, self.y))
        f.write('\t{} {} {} {}\n'.format(self.matrix[0], self.matrix[1], self.matrix[2], self.matrix[3]))
        f.write('$EndComp\n')


class SchematicConnection(object):
    conn_re = re.compile(r'\s*~\s+(-?\d+)\s+(-?\d+)')

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(connect, line, f):
        m = SchematicConnection.conn_re.match(line)
        if not m:
            raise SchFileError('Malformed no/connection', line, f)
        c = SchematicConnection()
        c.connect = connect
        c.x = int(m.group(1))
        c.y = int(m.group(2))
        return c

    def write(self, f):
        f.write('{} ~ {} {}\n'.format(['NoConn', 'Connection'][self.connect], self.x, self.y))


class SchematicText(object):
    label_re = re.compile(r'Text\s+(Notes|HLabel|GLabel|Label)\s+(-?\d+)\s+(-?\d+)\s+(\d)\s+(\d+)\s+(\S+)')
    TYPES = ['Notes', 'HLabel', 'GLabel', 'Label']

    def __init__(self):
        super().__init__()

    @staticmethod
    def load(f, line):
        gs = _split_space(line)
        c = len(gs)
        if c < 6 or gs[0] != 'Text' or gs[1] not in SchematicText.TYPES:
            raise SchFileError('Malformed `Text`', line, f)
        text = SchematicText()
        text.type = gs[1]
        try:
            text.x = int(gs[2])
            text.y = int(gs[3])
            text.orient = int(gs[4])
            text.size = int(gs[5])
            offset = 6
            text.shape = None
            if gs[1][0] in 'GH':
                if c < 7:
                    raise SchFileError('Missing `Text` shape', line, f)
                text.shape = gs[6]
                offset += 1
            # New versions adds Italics and Bold, in a different way of course
            text.italic = False
            if c > offset:
                text.italic = gs[offset] == 'Italic'
                offset += 1
            text.thickness = 0
            if c > offset:
                text.thickness = int(gs[offset])
                offset += 1
        except ValueError:
            raise SchFileError('Not a number in `Text`', line, f)
        text.text = f.get_line()
        return text

    def write(self, f):
        f.write('Text {} {} {} {} {}'.format(self.type, self.x, self.y, self.orient, self.size))
        if self.type[0] in 'GH':
            f.write(' '+self.shape)
        f.write(' {} {}\n'.format(['~', 'Italic'][self.italic], self.thickness))
        f.write(self.text+'\n')


class SchematicWire(object):
    WIRE = 0
    WIRE_BUS = 1
    WIRE_DOT = 2
    WIRES = {'Wire': WIRE, 'Bus': WIRE_BUS, 'Notes': WIRE_DOT}
    ENTRY_WIRE = 3
    ENTRY_BUS = 4
    ENTRIES = {'Wire': ENTRY_WIRE, 'Bus': ENTRY_BUS}
    NAMES = ['Wire Wire Line', 'Wire Bus Line', 'Wire Notes Line', 'Entry Wire Line', 'Entry Bus Bus']

    def __init__(self, width=None, style=None, rgb=None):
        super().__init__()
        self.width = width
        self.rgb = rgb
        self.style = style

    @staticmethod
    def load(f, line):
        res = _split_space(line)
        res_l = len(res)
        width = style = rgb = None
        if res_l > 3 and res[0] == 'Wire' and res[1] == 'Notes' and res[2] == 'Line':
            offset = 3
            while offset < res_l:
                if res[offset] == 'width' and res_l > offset+1:
                    width = res[offset+1]
                    offset += 2
                elif res[offset] == 'style' and res_l > offset+1:
                    style = res[offset+1]
                    offset += 2
                elif res[offset].startswith('rgb(') and res_l > offset+2:
                    rgb = res[offset]+' '+res[offset+1]+' '+res[offset+2]
                    offset += 3
                else:
                    raise SchFileError('Malformed wire note', line, f)
        elif res_l != 3:
            raise SchFileError('Malformed wire', line, f)
        wire = SchematicWire(width, style, rgb)
        if res[0] == 'Wire':
            # Wire Wire Line
            # Wire Bus Line
            # Wire Notes Line
            if res[2] != 'Line' or res[1] not in SchematicWire.WIRES:
                raise SchFileError('Malformed wire', line, f)
            wire.type = SchematicWire.WIRES[res[1]]
        else:  # Entry
            # Entry Wire Line
            # Entry Bus Bus
            if (res[2] != 'Bus' and res[2] != 'Line') or res[1] not in SchematicWire.ENTRIES:
                raise SchFileError('Malformed entry', line, f)
            wire.type = SchematicWire.ENTRIES[res[1]]
        line = f.get_line()
        if line[0] != '\t':
            raise SchFileError('Malformed wire', line, f)
        res = _split_space(line[1:])
        if len(res) != 4:
            raise SchFileError('Malformed wire', line, f)
        wire.x = int(res[0])
        wire.y = int(res[1])
        wire.ex = int(res[2])
        wire.ey = int(res[3])
        return wire

    def write(self, f):
        extra = ''
        if self.width is not None:
            extra += ' width '+self.width
        if self.style is not None:
            extra += ' style '+self.style
        if self.rgb is not None:
            extra += ' '+self.rgb
        f.write(SchematicWire.NAMES[self.type]+extra)
        f.write('\n\t{} {} {} {}\n'.format(self.x, self.y, self.ex, self.ey))


class SchematicBitmap(object):
    def __init__(self):
        super().__init__()

    @staticmethod
    def load(f):
        # Position
        line = f.get_line()
        res = _split_space(line)
        if res and res[0] != 'Pos':
            raise SchFileError('Missing bitmap position', line, f)
        if len(res) != 3:
            raise SchFileError('Malformed bitmap position', line, f)
        bmp = SchematicBitmap()
        bmp.x = int(res[1])
        bmp.y = int(res[2])
        # Scale
        line = f.get_line()
        res = _split_space(line)
        if res and res[0] != 'Scale':
            raise SchFileError('Missing bitmap scale', line, f)
        if len(res) != 2:
            raise SchFileError('Malformed bitmap scale', line, f)
        bmp.scale = float(res[1].replace(',', '.'))
        # Data
        line = f.get_line()
        if line != 'Data':
            raise SchFileError('Missing bitmap data', line, f)
        line = f.get_line()
        bmp.data = b''
        while line != 'EndData':
            res = _split_space(line)
            try:
                bmp.data += bytes([int(b, 16) for b in res])
            except ValueError:
                raise SchFileError('Malformed bitmap data', line, f)
            line = f.get_line()
        # End of bitmap
        line = f.get_line()
        if line != '$EndBitmap':
            raise SchFileError('Missing end of bitmap', line, f)
        return bmp

    def write(self, f):
        f.write('$Bitmap\n')
        f.write('Pos {} {}\n'.format(self.x, self.y))
        f.write('Scale {}\n'.format(self.scale))
        f.write('Data')
        for c, b in enumerate(self.data):
            if (c % 32) == 0:
                f.write('\n')
            f.write('%02X ' % b)
        f.write('\nEndData\n')
        f.write('$EndBitmap\n')


class SchematicPort(object):
    port_re = re.compile(r'(\d+)\s+"(.*?)"\s+([IOBTU])\s+([RLTB])\s+(-?\d+)\s+(-?\d+)\s+(\d+)$')

    def __init__(self):
        super().__init__()

    @staticmethod
    def parse(line, f):
        m = SchematicPort.port_re.match(line)
        if not m:
            raise SchFileError('Malformed sheet port label', line, f)
        port = SchematicPort()
        res = m.groups()
        port.number = int(res[0])
        port.name = res[1]
        port.form = res[2]
        port.side = res[3]
        port.x = int(res[4])
        port.y = int(res[5])
        port.size = int(res[6])
        return port

    def write(s, f):
        f.write('F{} "{}" {} {} {} {} {}\n'.format(s.number, s.name, s.form, s.side, s.x, s.y, s.size))


class SchematicSheet(object):
    name_re = re.compile(r'"(.*?)"\s+(\d+)$')

    def __init__(self):
        super().__init__()
        self.sheet = None
        self.id = ''
        self.annotation_error = False

    def load_sheet(self, project, parent, sheet_path, sheet_path_h, libs, fields, fields_lc):
        assert self.name
        self.sheet = Schematic()
        parent_dir = os.path.dirname(parent)
        sheet_path += '/'+self.id
        if len(sheet_path_h) > 1:
            sheet_path_h += '/'
        sheet_path_h += self.name if self.name else 'Unknown'
        self.sheet.load(os.path.join(parent_dir, self.file), project, sheet_path, sheet_path_h, libs, fields, fields_lc)
        return self.sheet

    @staticmethod
    def load(f):
        # Position & Size
        line = f.get_line()
        if line[0] != 'S':
            raise SchFileError('Missing sheet size and position', line, f)
        res = _split_space(line[2:])
        if len(res) != 4:
            raise SchFileError('Malformed sheet size and position', line, f)
        sch = SchematicSheet()
        sch.x = int(res[0])
        sch.y = int(res[1])
        sch.w = int(res[2])
        sch.h = int(res[3])
        # Optional U
        line = f.get_line()
        if line[0] == 'U':
            sch.id = line[2:]
            line = f.get_line()
        # Labels
        sch.labels = []
        sch.name = None
        sch.file = None
        while not line.startswith('$EndSheet'):
            if line[0] != 'F':
                raise SchFileError('Malformed sheet label', line, f)
            if line[1] == '0':
                m = SchematicSheet.name_re.match(line[2:].lstrip())
                if not m:
                    raise SchFileError('Malformed sheet name', line, f)
                sch.name = m.group(1)
                sch.name_size = int(m.group(2))
            elif line[1] == '1' and line[2] == ' ':
                m = SchematicSheet.name_re.match(line[2:].lstrip())
                if not m:
                    raise SchFileError('Malformed sheet file name', line, f)
                sch.file = m.group(1)
                sch.file_size = int(m.group(2))
            else:
                sch.labels.append(SchematicPort.parse(line[1:], f))
            line = f.get_line()
        if not sch.name:
            raise SchFileError('Missing sub-sheet name', 'pos: {},{}'.format(sch.x, sch.y), f)
        if not sch.file:
            raise SchFileError('Missing sub-sheet file name', sch.name, f)
        return sch

    def write(self, f):
        # Fake file name
        file = self.file.replace('/', '_')
        f.write('$Sheet\n')
        f.write('S {} {} {} {}\n'.format(self.x, self.y, self.w, self.h))
        f.write('U {}\n'.format(self.id))
        f.write('F0 "{}" {}\n'.format(self.name, self.name_size))
        f.write('F1 "{}" {}\n'.format(file, self.file_size))
        for label in self.labels:
            label.write(f)
        f.write('$EndSheet\n')


class Schematic(object):
    def __init__(self):
        super().__init__()
        self.dcms = {}
        self.lib_comps = {}
        self.annotation_error = False

    def _get_title_block(self, f):
        line = f.get_line()
        m = re.match(r'\$Descr (\S+) (\d+) (\d+)', line)
        if not m:
            raise SchFileError('Missing $Descr', line, f)
        self.page_type = m.group(1)
        self.page_width = m.group(2)
        self.page_height = m.group(3)
        self.sheet = 1
        self.nsheets = 1
        self.title_block = OrderedDict()
        while True:
            line = f.get_line()
            if line.startswith('$EndDescr'):
                self.title = self.title_block['Title'] if 'Title' in self.title_block else ''
                self.date = self.title_block['Date'] if 'Date' in self.title_block else ''
                self.revision = self.title_block['Rev'] if 'Rev' in self.title_block else ''
                self.company = self.title_block['Comp'] if 'Comp' in self.title_block else ''
                return
            elif line.startswith('encoding'):
                if line[9:14] != 'utf-8':
                    raise SchFileError('Unsupported encoding', line, f)
            elif line.startswith('Sheet'):
                res = _split_space(line[6:])
                if len(res) != 2:
                    raise SchFileError('Wrong sheet number', line, f)
                self.sheet = int(res[0])
                self.nsheets = int(res[1])
            else:
                m = re.match(r'(\S+)\s+"(.*)"', line)
                if not m:
                    raise SchFileError('Wrong entry in title block', line, f)
                self.title_block[m.group(1)] = m.group(2)

    def load(self, fname, project, sheet_path='', sheet_path_h='/', libs={}, fields=[], fields_lc=set()):
        """ Load a v5.x KiCad Schematic.
            The caller must be sure the file exists.
            Only the schematics are loaded not the libs. """
        logger.debug("Loading sheet from "+fname)
        self.fname = fname
        self.libs = libs
        self.fields = fields
        self.fields_lc = fields_lc
        self.project = project
        with open(fname, 'rt') as fh:
            f = SCHLineReader(fh, fname)
            line = f.get_line()
            m = re.match(r'EESchema Schematic File Version (\d+)', line)
            if not m:
                raise SchFileError('No eeschema signature', line, f)
            self.version = int(m.group(1))
            line = f.get_line()
            if line.startswith('LIBS'):
                # LIBS is optional and can be skipped
                line = f.get_line()
            m = re.match(r'EELAYER (\d+) (\d+)', line)
            if not m:
                raise SchFileError('Missing EELAYER', line, f)
            self.eelayer_n = int(m.group(1))
            self.eelayer_m = int(m.group(2))
            line = f.get_line()
            if not line.startswith('EELAYER END'):
                raise SchFileError('Missing EELAYER END', line, f)
            # Load the title block
            self._get_title_block(f)
            # Fill in some missing info
            if not self.date:
                file_mtime = os.path.getmtime(fname)
                self.date = datetime.fromtimestamp(file_mtime).strftime('%Y-%m-%d_%H-%M-%S')
            if not self.title:
                self.title = os.path.splitext(os.path.basename(fname))[0]
            logger.debug("SCH title: `{}`".format(self.title))
            logger.debug("SCH date: `{}`".format(self.date))
            logger.debug("SCH revision: `{}`".format(self.revision))
            logger.debug("SCH company: `{}`".format(self.company))
            line = f.get_line()
            self.all = []
            self.components = []
            self.conn = []
            self.texts = []
            self.wires = []
            self.bitmaps = []
            self.sheets = []
            while not line.startswith('$EndSCHEMATC'):
                if line.startswith('$Comp'):
                    obj = SchematicComponent.load(f, project, sheet_path, sheet_path_h, libs, fields, fields_lc)
                    if obj.annotation_error:
                        self.annotation_error = True
                    self.components.append(obj)
                elif line.startswith('NoConn'):
                    obj = SchematicConnection.parse(False, line[7:], f)
                    self.conn.append(obj)
                elif line.startswith('Connection'):
                    obj = SchematicConnection.parse(True, line[11:], f)
                    self.conn.append(obj)
                elif line.startswith('Text'):
                    obj = SchematicText.load(f, line)
                    self.texts.append(obj)
                elif line.startswith('Wire') or line.startswith('Entry'):
                    obj = SchematicWire.load(f, line)
                    self.wires.append(obj)
                elif line.startswith('$Bitmap'):
                    obj = SchematicBitmap.load(f)
                    self.bitmaps.append(obj)
                elif line.startswith('$Sheet'):
                    obj = SchematicSheet.load(f)
                    self.sheets.append(obj)
                else:
                    raise SchFileError('Unknown definition', line, f)
                self.all.append(obj)
                line = f.get_line()
            # Load sub-sheets
            self.sub_sheets = []
            for sch in self.sheets:
                sheet = sch.load_sheet(project, fname, sheet_path, sheet_path_h, libs, fields, fields_lc)
                if sheet.annotation_error:
                    self.annotation_error = True
                self.sub_sheets.append(sheet)

    def get_files(self):
        """ A list of the names for all the sheets, including this one.
            We avoid repeating the same file. """
        files = {self.fname}
        for sch in self.sheets:
            files.update(sch.sheet.get_files())
        return sorted(files)

    def get_components(self, exclude_power=True):
        """ A list of all the components. """
        if exclude_power:
            components = [c for c in self.components if not c.is_power]
        else:
            components = [c for c in self.components]
        for sch in self.sheets:
            components.extend(sch.sheet.get_components(exclude_power))
        components.sort(key=lambda g: g.ref)
        return components

    def get_field_names(self, fields):
        """ Appends the collected field names to the provided names """
        fields_lc = {v.lower() for v in fields}
        for f in self.fields:
            name_lc = f.lower()
            if name_lc not in fields_lc:
                fields.append(f)
                fields_lc.add(name_lc)
        return fields

    def walk_components(self, function, obj):
        for c in self.components:
            function(obj, c)
        for sch in self.sheets:
            sch.sheet.walk_components(function, obj)

    @staticmethod
    def apply_dcm(obj, c):
        dcm = None
        # Look for the DCM specific for the lib
        if c.lib:
            dcm = obj.dcms.get(c.lib)
            if dcm:
                entry = dcm.comps.get(c.name)
                if entry and entry.desc:
                    c.desc = entry.desc
                    if GS.debug_level > 2:
                        logger.debug('Filling desc for {}:{} `{}`'.format(c.lib, c.name, c.desc))

    def load_libs(self, fname):
        KiConf.init(fname)
        # Try to find the library paths
        for k in self.libs.keys():
            alias = KiConf.lib_aliases.get(k)
            if k and alias:
                self.libs[k] = alias.uri
                if GS.debug_level > 1:
                    logger.debug('Using `{}` for library alias `{}`'.format(alias.uri, k))
            else:
                logger.warning(W_MISSLIB + 'Missing library `{}`'.format(k))
        # Create a hash with all the used components
        self.comps_data = {'{}:{}'.format(c.lib, c.name): None for c in self.get_components(exclude_power=False)}
        if GS.debug_level > 1:
            logger.debug("Components before loading: "+str(self.comps_data))
        # Load the libraries and descriptions
        for k, v in self.libs.items():
            if v:
                # Load library
                if os.path.isfile(v):
                    o = SymLib()
                    o.load(v, k, self.comps_data)
                else:
                    logger.warning(W_MISSLIB + 'Missing library `{}` ({})'.format(v, k))
                    o = None
                self.lib_comps[k] = o
                # Load doc-lib
                file = os.path.splitext(v)[0]+'.dcm'
                if os.path.isfile(file):
                    o = DocLib()
                    o.load(file)
                else:
                    o = None
                self.dcms[k] = o
            else:
                # Mark as None if we don't know the file
                self.lib_comps[k] = None
                self.dcms[k] = None
        # Do we have all the components?
        if next((k for k, v in self.comps_data.items() if v is None), None) is not None:
            cache_name = fname.replace('.sch', '-cache.lib')
            if os.path.isfile(cache_name):
                logger.debug("Loading missing components from cache "+cache_name)
                o = SymLib()
                o.load(cache_name, None, self.comps_data)
        if GS.debug_level > 1:
            logger.debug("Components after loading: "+str(self.comps_data))
        # Join the descriptions with the components
        for k in self.libs.keys():
            lib = self.lib_comps[k]
            dcm = self.dcms[k]
            if lib and dcm:
                for name, comp in lib.comps.items():
                    comp.dcm = dcm.comps.get(name)
                    if not comp.dcm and k+':'+name in self.comps_data:
                        logger.warning(W_MISSDCM + 'Missing doc-lib entry for {}:{}'.format(k, name))
        # Transfer the descriptions to the instances of the components
        self.walk_components(self.apply_dcm, self)

    def gen_lib(self, name, cross=False):
        """ Dumps all the used components to one library.
            This is like the KiCad cache. """
        with open(name, 'wt') as f:
            f.write('EESchema-LIBRARY Version 2.4\n')
            f.write('#encoding utf-8\n')
            for k, v in self.comps_data.items():
                if v:
                    v.write(f, k, cross=cross)
                else:
                    logger.warning(W_MISSCMP + 'Missing component `{}`'.format(k))
            f.write('#\n#End Library\n')

    def save(self, fname, dest_dir):
        fname = os.path.join(dest_dir, fname)
        with open(fname, 'wt') as f:
            f.write('EESchema Schematic File Version {}\n'.format(self.version))
            f.write('EELAYER {} {}\n'.format(self.eelayer_n, self.eelayer_m))
            f.write('EELAYER END\n')
            f.write('$Descr {} {} {}\n'.format(self.page_type, self.page_width, self.page_height))
            f.write('encoding utf-8\n')
            f.write('Sheet {} {}\n'.format(self.sheet, self.nsheets))
            for k, v in self.title_block.items():
                f.write('{} "{}"\n'.format(k, v))
            f.write('$EndDescr\n')
            for e in self.all:
                e.write(f)
            f.write('$EndSCHEMATC\n')
        # Save sub-sheets
        for c, sch in enumerate(self.sheets):
            # Fake file name
            file = sch.file.replace('/', '_')
            self.sub_sheets[c].save(file, dest_dir)

    def save_variant(self, dest_dir):
        # Currently imposible
        # if not os.path.exists(dest_dir):
        #    os.makedirs(dest_dir)
        lib_yes = os.path.join(dest_dir, 'y.lib')
        lib_no = os.path.join(dest_dir, 'n.lib')
        self.gen_lib(lib_yes)
        self.gen_lib(lib_no, cross=True)
        fname = os.path.basename(self.fname)
        self.save(fname, dest_dir)
        # SymLibTable to use y/n
        with open(os.path.join(dest_dir, 'sym-lib-table'), 'wt') as f:
            f.write('(sym_lib_table\n')
            f.write(' (lib (name y)(type Legacy)(uri ${KIPRJMOD}/y.lib)(options "")(descr ""))\n')
            f.write(' (lib (name n)(type Legacy)(uri ${KIPRJMOD}/n.lib)(options "")(descr ""))\n')
            f.write(')\n')
        return fname

    def file_names_variant(self, dest_dir):
        """ Returns a list of file names created by save_variant() """
        fnames = [os.path.join(dest_dir, 'y.lib'),
                  os.path.join(dest_dir, 'n.lib'),
                  os.path.join(dest_dir, 'sym-lib-table')]
        # Sub-sheets
        sub_sheets = self.get_files()
        for sch in sub_sheets:
            sch = os.path.basename(sch)
            fnames.append(os.path.join(dest_dir, sch.replace('/', '_')))
        return fnames
