import os
from subprocess import (check_output, STDOUT, CalledProcessError)
from .misc import (CMD_IBOM, URL_IBOM, BOM_ERROR)
from .kiplot import (GS, check_script)
from .error import KiPlotConfigurationError
from kiplot.macros import macros, document, output_class  # noqa: F401
from . import log

logger = log.get_logger(__name__)


@output_class
class IBoM(BaseOutput):  # noqa: F821
    """ IBoM (Interactive HTML BoM)
        Generates an interactive web page useful to identify the position of the components in the PCB.
        For more information: https://github.com/INTI-CMNB/InteractiveHtmlBom
        This output is what you get from the InteractiveHtmlBom plug-in (pcbnew). """
    def __init__(self, name, type, description):
        super(IBoM, self).__init__(name, type, description)
        self._sch_related = True
        # Options
        with document:
            self.dark_mode = False
            """ Default to dark mode """
            self.hide_pads = False
            """ Hide footprint pads by default """
            self.show_fabrication = False
            """ Show fabrication layer by default """
            self.hide_silkscreen = False
            """ Hide silkscreen by default """
            self.highlight_pin1 = False
            """ Highlight pin1 by default """
            self.no_redraw_on_drag = False
            """ Do not redraw pcb on drag by default """
            self.board_rotation = 0
            """ Board rotation in degrees (-180 to 180). Will be rounded to multiple of 5 """
            self.checkboxes = 'Sourced,Placed'
            """ Comma separated list of checkbox columns """
            self._bom_view = 'left-right'
            """ Default BOM view {bom-only,left-right,top-bottom} """
            self._layer_view = 'FB'
            """ Default layer view {F,FB,B} """
            self.name_format = 'ibom'
            """ Output file name format supports substitutions:
                %f : original pcb file name without extension.
                %p : pcb/project title from pcb metadata.
                %c : company from pcb metadata.
                %r : revision from pcb metadata.
                %d : pcb date from metadata if available, file modification date otherwise.
                %D : bom generation date.
                %T : bom generation time. Extension .html will be added automatically """
            self.include_tracks = False
            """ Include track/zone information in output. F.Cu and B.Cu layers only """
            self.include_nets = False
            """ Include netlist information in output. """
            self.sort_order = 'C,R,L,D,U,Y,X,F,SW,A,~,HS,CNN,J,P,NT,MH'
            """ Default sort order for components. Must contain '~' once """
            self.blacklist = ''
            """ List of comma separated blacklisted components or prefixes with *. E.g. 'X1,MH*' """
            self.no_blacklist_virtual = False
            """ Do not blacklist virtual components """
            self.blacklist_empty_val = False
            """ Blacklist components with empty value """
            self.netlist_file = ''
            """ Path to netlist or xml file """
            self.extra_fields = ''
            """ Comma separated list of extra fields to pull from netlist or xml file """
            self.normalize_field_case = False
            """ Normalize extra field name case. E.g. 'MPN' and 'mpn' will be considered the same field """
            self.variant_field = ''
            """ Name of the extra field that stores board variant for component """
            self.variants_whitelist = ''
            """ List of board variants to include in the BOM """
            self.variants_blacklist = ''
            """ List of board variants to exclude from the BOM """
            self.dnp_field = ''
            """ Name of the extra field that indicates do not populate status. Components with this field not empty will be
                blacklisted """  # pragma: no cover

    @property
    def bom_view(self):
        return self._bom_view

    @bom_view.setter
    def bom_view(self, val):
        valid = ['bom-only', 'left-right', 'top-bottom']
        if val not in valid:
            raise KiPlotConfigurationError("`bom_view` must be any of "+str(valid))
        self._bom_view = val

    @property
    def layer_view(self):
        return self._layer_view

    @layer_view.setter
    def layer_view(self, val):
        valid = ['F', 'FB', 'B']
        if val not in valid:
            raise KiPlotConfigurationError("`layer_view` must be any of "+str(valid))
        self._layer_view = val

    def run(self, output_dir, board):
        check_script(CMD_IBOM, URL_IBOM)
        logger.debug('Doing Interactive BoM')
        # Tell ibom we don't want to use the screen
        os.environ['INTERACTIVE_HTML_BOM_NO_DISPLAY'] = ''
        cmd = [CMD_IBOM, GS.pcb_file, '--dest-dir', output_dir, '--no-browser', ]
        # Convert attributes into options
        for k, v in BaseOutput.get_attrs_gen(self):  # noqa: F821
            if not v:
                continue
            cmd.append(BaseOutput.attr2longopt(k))  # noqa: F821
            if not isinstance(v, bool):  # must be str/(int, float)
                cmd.append(str(v))
        # Run the command
        logger.debug('Running: '+str(cmd))
        try:
            cmd_output = check_output(cmd, stderr=STDOUT)
        except CalledProcessError as e:
            logger.error('Failed to create BoM, error %d', e.returncode)
            if e.output:
                logger.debug('Output from command: '+e.output.decode())
            exit(BOM_ERROR)
        logger.debug('Output from command:\n'+cmd_output.decode()+'\n')