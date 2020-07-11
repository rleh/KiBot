import os
import re
from tempfile import NamedTemporaryFile
from subprocess import check_output, STDOUT, CalledProcessError
from kiplot.misc import PCBDRAW, PCBDRAW_ERR
from kiplot.error import KiPlotConfigurationError
from kiplot.gs import GS
from kiplot.optionable import BaseOptions, Optionable
from kiplot.out_base import BaseOutput
from kiplot.macros import macros, document, output_class  # noqa: F401
from . import log

logger = log.get_logger(__name__)


class PcbDrawStyle(Optionable):
    _color_re = re.compile(r"#[A-Fa-f0-9]{6}$")

    def __init__(self):
        super().__init__()
        with document:
            self.copper = "#417e5a"
            """ color for the copper zones (covered by solder mask) """
            self.board = "#4ca06c"
            """ color for the board without copper (covered by solder mask) """
            self.silk = "#f0f0f0"
            """ color for the silk screen """
            self.pads = "#b5ae30"
            """ color for the exposed pads (metal finish) """
            self.outline = "#000000"
            """ color for the outline """
            self.clad = "#9c6b28"
            """ color for the PCB core (not covered by solder mask) """
            self.vcut = "#bf2600"
            """ color for the V-CUTS """
            self.highlight_on_top = False
            """ highlight over the component (not under) """
            self.highlight_style = "stroke:none;fill:#ff0000;opacity:0.5;"
            """ SVG code for the highlight style """
            self.highlight_padding = 1.5
            """ [0,1000] how much the highlight extends around the component [mm] """  # pragma: no cover

    def validate_color(self, name):
        color = getattr(self, name)
        if not self._color_re.match(color):
            raise KiPlotConfigurationError('Invalid color for `{}` use `#rrggbb` with hex digits'.format(name))

    def config(self, tree):
        super().config(tree)
        self.validate_color('board')
        self.validate_color('copper')
        self.validate_color('board')
        self.validate_color('silk')
        self.validate_color('pads')
        self.validate_color('outline')
        self.validate_color('clad')
        self.validate_color('vcut')
        # Not implemented but required
        self.highlight_offset = 0

    def to_dict(self):
        return {k.replace('_', '-'): v for k, v in self.get_attrs_gen()}


class PcbDrawRemap(Optionable):
    """ This class accepts a free form dict.
        No validation is done. """
    def __init__(self):
        super().__init__()

    def config(self, tree):
        self._tree = tree


class PcbDrawOptions(BaseOptions):
    def __init__(self):
        super().__init__()
        with document:
            self.style = PcbDrawStyle
            """ [string|dict] PCB style (colors). An internal name, the name of a JSON file or the style options """
            self.libs = Optionable
            """ [list(string)] list of libraries """
            self.placeholder = False
            """ show placeholder for missing components """
            self.remap = PcbDrawRemap
            """ [dict|None] replacements for PCB references using components (lib:component) """
            self.no_drillholes = False
            """ do not make holes transparent """
            self.bottom = False
            """ render the bottom side of the board (default is top side) """
            self.mirror = False
            """ mirror the board """
            self.highlight = Optionable
            """ [list(string)] list of components to highlight """
            self.show_components = Optionable
            """ [string|list(string)] [none,all] list of components to draw, can be also a string for none or all.
                The default is none """
            self.vcuts = False
            """ render V-CUTS on the Cmts.User layer """
            self.warnings = 'visible'
            """ [visible,all,none] using visible only the warnings about components in the visible side are generated """
            self.dpi = 300
            """ [10,1200] dots per inch (resolution) of the generated image """
            self.format = 'svg'
            """ [svg,png,jpg] output format. Only used if no `output` is specified """
            self.output = '%f-%i.%x'
            """ name for the generated file """  # pragma: no cover

    def config(self, tree):
        super().config(tree)
        # Libs
        if isinstance(self.libs, type):
            self.libs = None
        else:
            self.libs = ','.join(self.libs)
        # Highlight
        if isinstance(self.highlight, type):
            self.highlight = None
        else:
            self.highlight = ','.join(self.highlight)
        # Filter
        if isinstance(self.show_components, type):
            self.show_components = ''
        elif isinstance(self.show_components, str):
            if self.show_components == 'none':
                self.show_components = ''
            else:
                self.show_components = None
        else:
            self.show_components = ','.join(self.show_components)
        # Remap
        if isinstance(self.remap, type):
            self.remap = None
        elif isinstance(self.remap, PcbDrawRemap):
            self.remap = self.remap._tree
        # Style
        if isinstance(self.style, type):
            self.style = None
        elif isinstance(self.style, PcbDrawStyle):
            self.style = self.style.to_dict()

    def _create_remap(self):
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('{\n')
            first = True
            for k, v in self.remap.items():
                if first:
                    first = False
                else:
                    f.write(',\n')
                f.write('  "{}": "{}"'.format(k, v))
            f.write('\n}\n')
            f.close()
            return f.name

    def _create_style(self):
        with NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('{\n')
            first = True
            for k, v in self.style.items():
                if first:
                    first = False
                else:
                    f.write(',\n')
                if isinstance(v, str):
                    f.write('  "{}": "{}"'.format(k, v))
                elif isinstance(v, bool):
                    f.write('  "{}": {}'.format(k, str(v).lower()))
                else:
                    f.write('  "{}": {}'.format(k, v))
            f.write('\n}\n')
            f.close()
            return f.name

    def run(self, output_dir, board):
        # Output file name
        output = self.expand_filename(self.output, 'bottom' if self.bottom else 'top', self.format)
        output = os.path.abspath(os.path.join(output_dir, output))
        # Base command with overwrite
        cmd = [PCBDRAW]
        # Add user options
        tmp_style = None
        if self.style:
            if isinstance(self.style, str):
                cmd.extend(['-s', self.style])
            else:
                tmp_style = self._create_style()
                cmd.extend(['-s', tmp_style])
        if self.libs:
            cmd.extend(['-l', self.libs])
        if self.placeholder:
            cmd.append('--placeholder')
        if self.no_drillholes:
            cmd.append('--no-drillholes')
        if self.bottom:
            cmd.append('-b')
        if self.mirror:
            cmd.append('--mirror')
        if self.highlight:
            cmd.extend(['-a', self.highlight])
        if self.show_components is not None:
            cmd.extend(['-f', self.show_components])
        if self.vcuts:
            cmd.append('-v')
        if self.warnings == 'all':
            cmd.append('--warn-back')
        elif self.warnings == 'none':
            cmd.append('--silent')
        if self.dpi:
            cmd.extend(['--dpi', str(self.dpi)])
        if self.remap:
            tmp_remap = self._create_remap()
            cmd.extend(['-m', tmp_remap])
        else:
            tmp_remap = None
        # The board & output
        cmd.append(GS.pcb_file)
        cmd.append(output)
        # Execute and inform is successful
        logger.debug('Executing: '+str(cmd))
        try:
            cmd_output = check_output(cmd, stderr=STDOUT)
        except CalledProcessError as e:
            logger.error('Failed to run %s, error %d', PCBDRAW, e.returncode)
            if e.output:
                logger.debug('Output from command: '+e.output.decode())
            exit(PCBDRAW_ERR)
        finally:
            if tmp_remap:
                os.remove(tmp_remap)
            if tmp_style:
                os.remove(tmp_style)
        logger.debug('Output from command:\n'+cmd_output.decode())


@output_class
class PcbDraw(BaseOutput):
    """ PcbDraw - Beautiful 2D PCB render
        Exports the PCB as a 2D model (SVG, PNG or JPG).
        Uses configurable colors.
        Can also render the components if the 2D models are available """
    def __init__(self):
        super().__init__()
        with document:
            self.options = PcbDrawOptions
            """ [dict] Options for the `pcbdraw` output """  # pragma: no cover
