import os
import operator
from datetime import datetime
from pcbnew import (IU_PER_MM, IU_PER_MILS)
from kiplot.optionable import BaseOptions
from kiplot.macros import macros, document, output_class  # noqa: F401
from kiplot.out_base import BaseOutput


class PositionOptions(BaseOptions):
    def __init__(self):
        super().__init__()
        with document:
            self.format = 'ASCII'
            """ [ASCII,CSV] format for the position file """
            self.separate_files_for_front_and_back = True
            """ generate two separated files, one for the top and another for the bottom """
            self.only_smd = True
            """ only include the surface mount components """
            self.units = 'millimeters'
            """ [millimeters,inches] units used for the positions """  # pragma: no cover

    def _do_position_plot_ascii(self, board, output_dir, columns, modulesStr, maxSizes):
        name = os.path.splitext(os.path.basename(board.GetFileName()))[0]
        topf = None
        botf = None
        bothf = None
        if self.separate_files_for_front_and_back:
            topf = open(os.path.join(output_dir, "{}-top.pos".format(name)), 'w')
            botf = open(os.path.join(output_dir, "{}-bottom.pos".format(name)), 'w')
        else:
            bothf = open(os.path.join(output_dir, "{}-both.pos").format(name), 'w')

        files = [f for f in [topf, botf, bothf] if f is not None]
        for f in files:
            f.write('### Module positions - created on {} ###\n'.format(datetime.now().strftime("%a %d %b %Y %X %Z")))
            f.write('### Printed by KiPlot\n')
            unit = {'millimeters': 'mm', 'inches': 'in'}[self.units]
            f.write('## Unit = {}, Angle = deg.\n'.format(unit))

        if topf is not None:
            topf.write('## Side : top\n')
        if botf is not None:
            botf.write('## Side : bottom\n')
        if bothf is not None:
            bothf.write('## Side : both\n')

        for f in files:
            f.write('# ')
            for idx, col in enumerate(columns):
                if idx > 0:
                    f.write("   ")
                f.write("{0: <{width}}".format(col, width=maxSizes[idx]))
            f.write('\n')

        # Account for the "# " at the start of the comment column
        maxSizes[0] = maxSizes[0] + 2

        for m in modulesStr:
            fle = bothf
            if fle is None:
                if m[-1] == "top":
                    fle = topf
                else:
                    fle = botf
            for idx, col in enumerate(m):
                if idx > 0:
                    fle.write("   ")
                fle.write("{0: <{width}}".format(col, width=maxSizes[idx]))
            fle.write("\n")

        for f in files:
            f.write("## End\n")

        if topf is not None:
            topf.close()
        if botf is not None:
            botf.close()
        if bothf is not None:
            bothf.close()

    def _do_position_plot_csv(self, board, output_dir, columns, modulesStr):
        name = os.path.splitext(os.path.basename(board.GetFileName()))[0]
        topf = None
        botf = None
        bothf = None
        if self.separate_files_for_front_and_back:
            topf = open(os.path.join(output_dir, "{}-top-pos.csv".format(name)), 'w')
            botf = open(os.path.join(output_dir, "{}-bottom-pos.csv".format(name)), 'w')
        else:
            bothf = open(os.path.join(output_dir, "{}-both-pos.csv").format(name), 'w')

        files = [f for f in [topf, botf, bothf] if f is not None]

        for f in files:
            f.write(",".join(columns))
            f.write("\n")

        for m in modulesStr:
            fle = bothf
            if fle is None:
                if m[-1] == "top":
                    fle = topf
                else:
                    fle = botf
            fle.write(",".join('"{}"'.format(e) for e in m))
            fle.write("\n")

        if topf is not None:
            topf.close()
        if botf is not None:
            botf.close()
        if bothf is not None:
            bothf.close()

    def run(self, output_dir, board):
        columns = ["Ref", "Val", "Package", "PosX", "PosY", "Rot", "Side"]
        colcount = len(columns)
        # Note: the parser already checked the units are milimeters or inches
        conv = 1.0
        if self.units == 'millimeters':
            conv = 1.0 / IU_PER_MM
        else:  # self.units == 'inches':
            conv = 0.001 / IU_PER_MILS
        # Format all strings
        modules = []
        for m in sorted(board.GetModules(), key=operator.methodcaller('GetReference')):
            if (self.only_smd and m.GetAttributes() == 1) or not self.only_smd:
                center = m.GetCenter()
                # See PLACE_FILE_EXPORTER::GenPositionData() in
                # export_footprints_placefile.cpp for C++ version of this.
                modules.append([
                    "{}".format(m.GetReference()),
                    "{}".format(m.GetValue()),
                    "{}".format(m.GetFPID().GetLibItemName()),
                    "{:.4f}".format(center.x * conv),
                    "{:.4f}".format(-center.y * conv),
                    "{:.4f}".format(m.GetOrientationDegrees()),
                    "{}".format("bottom" if m.IsFlipped() else "top")
                ])

        # Find max width for all columns
        maxlengths = [0] * colcount
        for row in range(len(modules)):
            for col in range(colcount):
                maxlengths[col] = max(maxlengths[col], len(modules[row][col]))

        # Note: the parser already checked the format is ASCII or CSV
        if self.format == 'ASCII':
            self._do_position_plot_ascii(board, output_dir, columns, modules, maxlengths)
        else:  # if self.format == 'CSV':
            self._do_position_plot_csv(board, output_dir, columns, modules)


@output_class
class Position(BaseOutput):
    """ Pick & place
        Generates the file with position information for the PCB components, used by the pick and place machine.
        This output is what you get from the 'File/Fabrication output/Footprint poistion (.pos) file' menu in pcbnew. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = PositionOptions
            """ [dict] Options for the `position` output """  # pragma: no cover
