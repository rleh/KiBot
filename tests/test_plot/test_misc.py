"""
Tests miscellaneous stuff.

- -s all -i
- -s run_erc,update_xml,run_drc -i
- -s all,run_drc
- -s bogus
- An unknown output type
- -s all and_one_of_two_outs
- Missing schematic
- Wrong PCB name
- Missing PCB
- Missing SCH
- Missing config
- Wrong config name
- Guess the PCB and YAML
- Guess the PCB and YAML when more than one is present
- Guess the SCH and YAML
- Guess the SCH and YAML when more than one is present
- --list
- Create example
  - with PCB
  - already exists
  - Copying
- Load plugin

For debug information use:
pytest-3 --log-cli-level debug
"""

import os
import sys
import shutil
import logging
# Look for the 'utils' module from where the script is running
prev_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if prev_dir not in sys.path:
    sys.path.insert(0, prev_dir)
# Utils import
from utils import context
prev_dir = os.path.dirname(prev_dir)
if prev_dir not in sys.path:
    sys.path.insert(0, prev_dir)
from kibot.misc import (EXIT_BAD_ARGS, EXIT_BAD_CONFIG, NO_PCB_FILE, NO_SCH_FILE, EXAMPLE_CFG, WONT_OVERWRITE, CORRUPTED_PCB,
                        PCBDRAW_ERR, NO_PCBNEW_MODULE, NO_YAML_MODULE, INTERNAL_ERROR)


POS_DIR = 'positiondir'
MK_TARGETS = ['position', 'archive', 'interactive_bom', 'run_erc', '3D', 'kibom_internal', 'drill', 'pcb_render',
              'print_front', 'svg_sch_def', 'svg_sch_int', 'pdf_sch_def', 'pdf_sch_int', 'fake_sch', 'update_xml',
              'run_drc']


def test_skip_pre_and_outputs(test_dir):
    prj = 'simple_2layer'
    ctx = context.TestContext(test_dir, 'SkipPreAndPos', prj, 'pre_and_position', POS_DIR)
    ctx.run(extra=['-s', 'all', '-i'])

    ctx.dont_expect_out_file(ctx.get_pos_both_csv_filename())
    assert ctx.search_err('Skipping all pre-flight actions')
    assert ctx.search_err('Skipping all outputs')

    ctx.clean_up()


def test_skip_pre_and_outputs_2(test_dir):
    prj = 'simple_2layer'
    ctx = context.TestContext(test_dir, 'SkipPreAndPos2', prj, 'pre_and_position', POS_DIR)
    ctx.run(extra=['-s', 'run_erc,update_xml,run_drc', '-i'])

    ctx.dont_expect_out_file(ctx.get_pos_both_csv_filename())
    assert ctx.search_err('Skipping .?run_erc')
    assert ctx.search_err('Skipping .?run_drc')
    assert ctx.search_err('Skipping .?update_xml')
    assert ctx.search_err('Skipping all outputs')

    ctx.clean_up()


def test_skip_pre_and_outputs_3(test_dir):
    prj = 'simple_2layer'
    ctx = context.TestContext(test_dir, 'SkipPreAndPos3', prj, 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, extra=['-s', 'all,run_drc'])

    ctx.dont_expect_out_file(ctx.get_pos_both_csv_filename())
    assert ctx.search_err('Use `--skip all`')

    ctx.clean_up()


def test_skip_pre_and_outputs_4(test_dir):
    prj = 'simple_2layer'
    ctx = context.TestContext(test_dir, 'SkipPreAndPos4', prj, 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, extra=['-s', 'bogus'])

    ctx.dont_expect_out_file(ctx.get_pos_both_csv_filename())
    assert ctx.search_err('Unknown preflight .?bogus')

    ctx.clean_up()


def test_skip_pre_and_outputs_5(test_dir):
    prj = 'simple_2layer'
    ctx = context.TestContext(test_dir, 'SkipPreAndPos4', prj, 'pre_skip', POS_DIR)
    ctx.run(extra=['-s', 'run_erc,run_drc'])
    assert ctx.search_err('no need to skip')
    ctx.clean_up()


def test_unknown_out(test_dir):
    prj = 'simple_2layer'
    ctx = context.TestContext(test_dir, 'UnknownOut', prj, 'unknown_out', POS_DIR)
    ctx.run(EXIT_BAD_CONFIG)

    ctx.dont_expect_out_file(ctx.get_pos_both_csv_filename())
    assert ctx.search_err("Unknown output type:? .?bogus")

    ctx.clean_up()


def test_select_output(test_dir):
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'DoASCIISkipCSV', prj, 'pre_and_position', POS_DIR)
    ctx.run(extra=['-s', 'all', 'pos_ascii'])

    ctx.dont_expect_out_file(ctx.get_pos_both_csv_filename())
    ctx.expect_out_file(ctx.get_pos_both_filename())
    assert ctx.search_err('Skipping (.*)position(.*) output')

    ctx.clean_up()


def test_miss_sch(test_dir):
    prj = 'fail-project'
    ctx = context.TestContext(test_dir, 'MissingSCH', prj, 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, extra=['pos_ascii'])

    assert ctx.search_err('No SCH file found')

    ctx.clean_up()


def test_miss_sch_2(test_dir):
    prj = 'fail-project'
    ctx = context.TestContext(test_dir, 'MissingSCH_2', prj, 'pre_and_position', POS_DIR)
    ctx.run(NO_SCH_FILE, no_board_file=True, extra=['-e', 'bogus', 'pos_ascii'])

    assert ctx.search_err('Schematic file not found')

    ctx.clean_up()


def test_miss_pcb(test_dir):
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'MissingPCB', prj, 'pre_and_position', POS_DIR)
    ctx.board_file = 'bogus'
    ctx.run(NO_PCB_FILE, extra=['-s', 'run_erc,update_xml', 'pos_ascii'])

    assert ctx.search_err('Board file not found')

    ctx.clean_up()


def test_miss_pcb_2(test_dir):
    ctx = context.TestContext(test_dir, 'MissingPCB_2', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, no_board_file=True, extra=['-s', 'run_erc,update_xml', 'pos_ascii'])

    assert ctx.search_err('No PCB file found')

    ctx.clean_up()


def test_miss_yaml(test_dir):
    prj = 'bom'
    ctx = context.TestContext(test_dir, 'MissingYaml', prj, 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, no_yaml_file=True)

    assert ctx.search_err('No config file')

    ctx.clean_up()


def test_miss_yaml_2(test_dir):
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'MissingYaml_wrong', prj, 'pre_and_position', POS_DIR)
    ctx.yaml_file = 'bogus'
    ctx.run(EXIT_BAD_ARGS)

    assert ctx.search_err('Plot config file not found: bogus')

    ctx.clean_up()


def test_auto_pcb_and_cfg(test_dir):
    """ Test guessing the PCB and config file.
        Only one them is there. """
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'GuessPCB_cfg', prj, 'pre_and_position', POS_DIR)

    board_file = os.path.basename(ctx.board_file)
    shutil.copy2(ctx.board_file, ctx.get_out_path(board_file))
    yaml_file = os.path.basename(ctx.yaml_file)
    shutil.copy2(ctx.yaml_file, ctx.get_out_path(yaml_file))

    ctx.run(extra=['-s', 'all', '-i', 'pos_ascii'], no_out_dir=True, no_board_file=True, no_yaml_file=True, chdir_out=True)

    ctx.dont_expect_out_file(ctx.get_pos_both_filename())
    ctx.expect_out_file(ctx.get_pos_both_csv_filename())
    assert ctx.search_out('Using PCB file: '+board_file)
    assert ctx.search_out('Using config file: '+yaml_file)

    ctx.clean_up()


def test_auto_pcb_and_cfg_2(test_dir):
    """ Test guessing the PCB and config file.
        Two of them are there. """
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'GuessPCB_cfg_rep', prj, 'pre_and_position', POS_DIR)

    board_file = os.path.basename(ctx.board_file)
    shutil.copy2(ctx.board_file, ctx.get_out_path(board_file))
    shutil.copy2(ctx.board_file, ctx.get_out_path('b_'+board_file))
    yaml_file = os.path.basename(ctx.yaml_file)
    shutil.copy2(ctx.yaml_file, ctx.get_out_path(yaml_file))
    shutil.copy2(ctx.yaml_file, ctx.get_out_path('b_'+yaml_file))

    ctx.run(extra=['-s', 'all', '-i', 'pos_ascii'], no_out_dir=True, no_board_file=True, no_yaml_file=True, chdir_out=True)

    assert ctx.search_err('More than one PCB')
    assert ctx.search_err('More than one config')
    m = ctx.search_err('Using (.*).kicad_pcb')
    assert m
    ctx.board_name = m.group(1)

    ctx.dont_expect_out_file(ctx.get_pos_both_filename())
    ctx.expect_out_file(ctx.get_pos_both_csv_filename())

    ctx.clean_up()


def test_auto_pcb_and_cfg_3(test_dir):
    """ Test guessing the SCH and config file.
        Only one them is there. """
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'GuessSCH_cfg', prj, 'pre_and_position', POS_DIR)

    sch = os.path.basename(ctx.sch_file)
    shutil.copy2(ctx.sch_file, ctx.get_out_path(sch))
    yaml_file = os.path.basename(ctx.yaml_file)
    shutil.copy2(ctx.yaml_file, ctx.get_out_path(yaml_file))

    ctx.run(extra=['-s', 'all', '-i'], no_out_dir=True, no_board_file=True, no_yaml_file=True, chdir_out=True)

    assert ctx.search_out('Using SCH file: '+sch)
    assert ctx.search_out('Using config file: '+yaml_file)

    ctx.clean_up()


def test_auto_pcb_and_cfg_4(test_dir):
    """ Test guessing the SCH and config file.
        Two SCHs and one PCB.
        The SCH with same name as the PCB should be selected. """
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'GuessSCH_cfg_2', prj, 'pre_and_position', POS_DIR)

    sch = os.path.basename(ctx.sch_file)
    shutil.copy2(ctx.sch_file, ctx.get_out_path(sch))
    shutil.copy2(ctx.sch_file, ctx.get_out_path('b_'+sch))
    brd = os.path.basename(ctx.board_file)
    shutil.copy2(ctx.board_file, ctx.get_out_path(brd))
    yaml_file = os.path.basename(ctx.yaml_file)
    shutil.copy2(ctx.yaml_file, ctx.get_out_path(yaml_file))

    ctx.run(extra=['-s', 'all', '-i'], no_out_dir=True, no_board_file=True, no_yaml_file=True, chdir_out=True)

    assert ctx.search_err('Using '+sch)
    assert ctx.search_out('Using config file: '+yaml_file)

    ctx.clean_up()


def test_auto_pcb_and_cfg_5(test_dir):
    """ Test guessing the SCH and config file.
        Two SCHs. """
    prj = '3Rs'
    ctx = context.TestContext(test_dir, 'GuessSCH_cfg_3', prj, 'pre_and_position', POS_DIR)

    sch = os.path.basename(ctx.sch_file)
    shutil.copy2(ctx.sch_file, ctx.get_out_path(sch))
    shutil.copy2(ctx.sch_file, ctx.get_out_path('b_'+sch))
    yaml_file = os.path.basename(ctx.yaml_file)
    shutil.copy2(ctx.yaml_file, ctx.get_out_path(yaml_file))

    ctx.run(extra=['-s', 'all', '-i'], no_out_dir=True, no_board_file=True, no_yaml_file=True, chdir_out=True)

    assert ctx.search_err('Using (b_)?'+sch)
    assert ctx.search_out('Using config file: '+yaml_file)

    ctx.clean_up()


def test_list(test_dir):
    ctx = context.TestContext(test_dir, 'List', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--list'], no_verbose=True, no_out_dir=True)

    assert ctx.search_out('run_erc: True')
    assert ctx.search_out('run_drc: True')
    assert ctx.search_out('update_xml: True')
    assert ctx.search_out(r'Pick and place file.? \(position\) \[position\]')
    assert ctx.search_out(r'Pick and place file.? \(pos_ascii\) \[position\]')

    ctx.clean_up()


def test_help(test_dir):
    ctx = context.TestContext(test_dir, 'Help', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--help'], no_verbose=True, no_out_dir=True, no_yaml_file=True)
    assert ctx.search_out('Usage:')
    assert ctx.search_out('Arguments:')
    assert ctx.search_out('Options:')
    ctx.clean_up()


def test_help_list_outputs(test_dir):
    ctx = context.TestContext(test_dir, 'HelpListOutputs', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--help-list-outputs'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('Supported outputs:')
    assert ctx.search_out('Gerber format')
    ctx.clean_up()


def test_help_output(test_dir):
    ctx = context.TestContext(test_dir, 'HelpOutput', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--help-output', 'gerber'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('Gerber format')
    assert ctx.search_out('Type: .?gerber.?')
    ctx.clean_up()


def test_help_output_unk(test_dir):
    ctx = context.TestContext(test_dir, 'HelpOutputUnk', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, extra=['--help-output', 'bogus'], no_verbose=True, no_out_dir=True, no_yaml_file=True,
            no_board_file=True)
    assert ctx.search_err('Unknown output type')
    ctx.clean_up()


def test_help_filters(test_dir):
    ctx = context.TestContext(test_dir, 'test_help_filters', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--help-filters'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('Generic filter')
    ctx.clean_up()


def test_help_output_plugin_1(test_dir, monkeypatch):
    ctx = context.TestContext(test_dir, 'test_help_output_plugin_1', '3Rs', 'pre_and_position', POS_DIR)
    ctx.home_local_link()
    with monkeypatch.context() as m:
        m.setenv("HOME", os.path.join(ctx.get_board_dir(), '../..'))
        logging.debug('HOME='+os.environ['HOME'])
        ctx.run(extra=['--help-output', 'test'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out(r'\* Undocumented')
    assert ctx.search_out('Description: No description')
    assert ctx.search_out('Type: .?test.?')
    assert ctx.search_out('nothing')
    assert ctx.search_out('chocolate')
    assert ctx.search_out('`not_documented`: Undocumented')
    ctx.clean_up()


def test_help_output_plugin_2(test_dir, monkeypatch):
    ctx = context.TestContext(test_dir, 'test_help_output_plugin_2', '3Rs', 'pre_and_position', POS_DIR)
    ctx.home_local_link()
    with monkeypatch.context() as m:
        m.setenv("HOME", os.path.join(ctx.get_board_dir(), '../..'))
        logging.debug('HOME='+os.environ['HOME'])
        ctx.run(extra=['--help-output', 'test2'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('Test for plugin')
    assert ctx.search_out('Type: .?test2.?')
    assert ctx.search_out('todo')
    assert ctx.search_out('frutilla')
    ctx.clean_up()


def test_help_output_plugin_3(test_dir, monkeypatch):
    ctx = context.TestContext(test_dir, 'test_help_output_plugin_3', '3Rs', 'pre_and_position', POS_DIR)
    ctx.home_local_link()
    with monkeypatch.context() as m:
        m.setenv("HOME", os.path.join(ctx.get_board_dir(), '../..'))
        logging.debug('HOME='+os.environ['HOME'])
        ctx.run(extra=['--help-preflights'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('- pre_test: Undocumented')
    ctx.clean_up()


def test_help_output_plugin_4(test_dir, monkeypatch):
    ctx = context.TestContext(test_dir, 'test_help_output_plugin_4', '3Rs', 'pre_and_position', POS_DIR)
    ctx.home_local_link()
    with monkeypatch.context() as m:
        m.setenv("HOME", os.path.join(ctx.get_board_dir(), '../..'))
        logging.debug('HOME='+os.environ['HOME'])
        ctx.run(extra=['--help-filters'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('- filter_test: Undocumented')
    ctx.clean_up()


def test_help_outputs(test_dir):
    ctx = context.TestContext(test_dir, 'HelpOutputs', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--help-outputs'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('Gerber format')
    assert ctx.search_out('Type: .?gerber.?')
    ctx.clean_up()


def test_help_preflights(test_dir):
    ctx = context.TestContext(test_dir, 'HelpPreflights', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(extra=['--help-preflights'], no_verbose=True, no_out_dir=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_out('Supported preflight options')
    ctx.clean_up()


def test_example_1(test_dir):
    """ Example without board """
    ctx = context.TestContext(test_dir, 'Example1', '3Rs', 'pre_and_position', '')
    ctx.run(extra=['--example'], no_verbose=True, no_yaml_file=True, no_board_file=True)
    assert ctx.expect_out_file(EXAMPLE_CFG)
    ctx.clean_up()


def test_example_2(test_dir):
    """ Example with board """
    ctx = context.TestContext(test_dir, 'Example2', 'good-project', 'pre_and_position', '')
    ctx.run(extra=['--example'], no_verbose=True, no_yaml_file=True)
    assert ctx.expect_out_file(EXAMPLE_CFG)
    ctx.search_in_file(EXAMPLE_CFG, ['layers: all'])
    ctx.clean_up()


def test_example_3(test_dir):
    """ Overwrite error """
    ctx = context.TestContext(test_dir, 'Example3', 'good-project', 'pre_and_position', '')
    ctx.run(extra=['--example'], no_verbose=True, no_yaml_file=True)
    assert ctx.expect_out_file(EXAMPLE_CFG)
    ctx.run(WONT_OVERWRITE, extra=['--example'], no_verbose=True, no_yaml_file=True)
    ctx.clean_up()


def test_example_4(test_dir):
    """ Expand copied layers """
    ctx = context.TestContext(test_dir, 'Example4', 'good-project', 'pre_and_position', '')
    ctx.run(extra=['--example', '-P'], no_verbose=True, no_yaml_file=True)
    assert ctx.expect_out_file(EXAMPLE_CFG)
    ctx.search_in_file(EXAMPLE_CFG, ['GND.Cu', 'pen_width: 35.0'])
    ctx.search_not_in_file(EXAMPLE_CFG, ['F.Adhes'])
    ctx.clean_up()


def test_example_5(test_dir):
    """ Copy setting from PCB """
    ctx = context.TestContext(test_dir, 'Example5', 'good-project', 'pre_and_position', '')
    output_dir = os.path.join(ctx.output_dir, 'pp')
    ctx.run(extra=['--example', '-p', '-d', output_dir], no_verbose=True, no_yaml_file=True, no_out_dir=True)
    file = os.path.join('pp', EXAMPLE_CFG)
    assert ctx.expect_out_file(file)
    ctx.search_in_file(file, ['layers: selected', 'pen_width: 35.0'])
    ctx.clean_up()


def test_example_6(test_dir):
    """ Copy setting but no PCB """
    ctx = context.TestContext(test_dir, 'Example6', 'good-project', 'pre_and_position', '')
    ctx.run(EXIT_BAD_ARGS, extra=['--example', '-p'], no_verbose=True, no_yaml_file=True, no_board_file=True)
    assert ctx.search_err('no PCB specified')
    ctx.clean_up()


def test_example_7(test_dir, monkeypatch):
    """ With dummy plug-ins """
    ctx = context.TestContext(test_dir, 'Example7', '3Rs', 'pre_and_position', '')
    ctx.home_local_link()
    with monkeypatch.context() as m:
        m.setenv("HOME", os.path.join(ctx.get_board_dir(), '../..'))
        ctx.run(extra=['--example'], no_verbose=True, no_yaml_file=True, no_board_file=True)
    assert ctx.expect_out_file(EXAMPLE_CFG)
    ctx.search_in_file(EXAMPLE_CFG, ['# Undocumented:', "comment: 'No description'"])
    ctx.clean_up()


def test_corrupted_pcb(test_dir):
    prj = 'bom_no_xml'
    ctx = context.TestContext(test_dir, 'Corrupted', prj, 'print_pcb', '')
    ctx.run(CORRUPTED_PCB)
    assert ctx.search_err('Error loading PCB file')
    ctx.clean_up()


def test_pcbdraw_fail(test_dir):
    prj = 'bom'
    ctx = context.TestContext(test_dir, 'PcbDrawFail', prj, 'pcbdraw_fail', '')
    ctx.run(PCBDRAW_ERR)
    assert ctx.search_err('Failed to run')
    ctx.clean_up()


# This test was designed for `mcpy`.
# `mcpyrate` can pass it using Python 3.8.6, but seems to have problems on the docker image.
# def test_import_fail(test_dir):
#     ctx = context.TestContext(test_dir, 'test_import_fail', '3Rs', 'pre_and_position', POS_DIR)
#     # Create a read only cache entry that we should delete
#     call(['py3compile', 'kibot/out_any_layer.py'])
#     cache_dir = os.path.join('kibot', '__pycache__')
#     cache_file = glob(os.path.join(cache_dir, 'out_any_layer.*'))[0]
#     os.chmod(cache_file, stat.S_IREAD)
#     os.chmod(cache_dir, stat.S_IREAD | stat.S_IEXEC)
#     try:
#         # mcpyrate: not a problem, for Python 3.8.6
#         ret_code = 0
#         # mcpy:
#         # ret_code = WRONG_INSTALL
#         # Run the command
#         ctx.run(ret_code, extra=['--help-list-outputs'], no_out_dir=True, no_yaml_file=True, no_board_file=True)
#     finally:
#         os.chmod(cache_dir, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
#         os.remove(cache_file)
#     if False:
#         # mcpy
#         assert ctx.search_err('Wrong installation')
#         assert ctx.search_err('Unable to import plug-ins')
#     ctx.clean_up()
#
#
# def test_import_no_fail(test_dir):
#     ctx = context.TestContext(test_dir, 'test_import_no_fail', '3Rs', 'pre_and_position', POS_DIR)
#     # Create a cache entry that we should delete
#     call(['py3compile', 'kibot/out_any_layer.py'])
#     cache_dir = os.path.join('kibot', '__pycache__')
#     cache_file = glob(os.path.join(cache_dir, 'out_any_layer.*'))[0]
#     try:
#         # Run the command
#         ctx.run(extra=['--help-list-outputs'], no_out_dir=True, no_yaml_file=True, no_board_file=True)
#         if False:
#             # mcpy
#             assert not os.path.isfile(cache_file)
#     finally:
#         if os.path.isfile(cache_file):
#             os.remove(cache_file)
#     ctx.clean_up()


def test_wrong_global_redef(test_dir):
    ctx = context.TestContext(test_dir, 'test_wrong_global_redef', '3Rs', 'pre_and_position', POS_DIR)
    ctx.run(EXIT_BAD_ARGS, extra=['--global-redef', 'bogus'])
    assert ctx.search_err('Malformed global-redef option')
    ctx.clean_up()


def test_no_pcbnew(test_dir):
    ctx = context.TestContext(test_dir, 'test_no_pcbnew', 'bom', 'bom', '')
    cmd = [os.path.abspath(os.path.dirname(os.path.abspath(__file__))+'/force_pcbnew_error.py')]
    ctx.do_run(cmd, NO_PCBNEW_MODULE)
    ctx.search_err('Failed to import pcbnew Python module.')
    ctx.search_err('PYTHONPATH')


def test_old_pcbnew(test_dir):
    ctx = context.TestContext(test_dir, 'test_old_pcbnew', 'bom', 'bom', '')
    cmd = [os.path.abspath(os.path.dirname(os.path.abspath(__file__))+'/force_pcbnew_error.py'), 'fake']
    ctx.do_run(cmd)
    ctx.search_err('Unknown KiCad version, please install KiCad 5.1.6 or newer')


def test_no_yaml(test_dir):
    ctx = context.TestContext(test_dir, 'test_no_yaml', 'bom', 'bom', '')
    cmd = [os.path.abspath(os.path.dirname(os.path.abspath(__file__))+'/force_yaml_error.py')]
    ctx.do_run(cmd, NO_YAML_MODULE)
    ctx.search_err('No yaml module for Python, install python3-yaml')


def test_no_colorama(test_dir):
    ctx = context.TestContext(test_dir, 'test_no_colorama', 'bom', 'bom', '')
    cmd = [os.path.abspath(os.path.dirname(os.path.abspath(__file__))+'/force_colorama_error.py')]
    ctx.do_run(cmd, use_a_tty=True)
    ctx.search_err(r'\[31m.\[1mERROR:Testing 1 2 3')


def check_test_v5_sch_deps(ctx, deps, extra=[], in_output=False):
    ndeps = 4
    if in_output:
        ndeps -= 1
    assert len(deps) == ndeps+len(extra), deps
    dir = os.path.dirname(ctx.board_file)
    deps_abs = [os.path.abspath(f) for f in deps]
    for sch in ['test_v5.sch', 'sub-sheet.sch', 'deeper.sch']:
        if in_output:
            assert os.path.abspath(ctx.get_out_path(sch)) in deps_abs
        else:
            assert os.path.abspath(os.path.join(dir, sch)) in deps_abs
    for f in extra:
        assert f in deps
    if not in_output:
        assert os.path.relpath(ctx.yaml_file) in deps


def check_makefile(ctx, mkfile, prj, dbg, txt):
    ctx.expect_out_file('Makefile')
    res = ctx.search_in_file('Makefile', [r'DEBUG\?=(.*)', txt])
    assert res[0][0] == dbg, res
    targets = ctx.read_mk_targets(mkfile)
    all = targets['all']
    phony = targets['.PHONY']
    for target in MK_TARGETS:
        assert target in all
        assert target in phony
        assert target in targets
        logging.debug('- Target `'+target+'` in all, .PHONY and itself OK')
    assert 'kibom_external' not in targets
    yaml = os.path.relpath(ctx.yaml_file)
    board_file = os.path.relpath(ctx.board_file)
    # position target
    deps = targets['position'].split(' ')
    assert len(deps) == 2, deps
    assert ctx.get_out_path(os.path.join(POS_DIR, prj+'-top_pos.csv')) in deps
    assert ctx.get_out_path(os.path.join(POS_DIR, prj+'-bottom_pos.csv')) in deps
    deps = targets[targets['position']].split(' ')
    assert len(deps) == 2
    assert board_file in deps
    assert yaml in deps
    logging.debug('- Target `position` OK')
    # interactive_bom target
    deps = targets['interactive_bom'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(os.path.join('ibom', prj+'-ibom.html')) in deps
    deps = targets[targets['interactive_bom']].split(' ')
    assert len(deps) == 3
    assert board_file in deps
    assert yaml in deps
    assert 'tests/board_samples/kicad_5/bom.xml' in deps
    logging.debug('- Target `interactive_bom` OK')
    # pcb_render target
    deps = targets['pcb_render'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-top$.svg') in deps
    deps = targets[targets['pcb_render']].split(' ')
    assert len(deps) == 3
    assert board_file in deps
    assert yaml in deps
    assert 'tests/data/html_style.css' in deps
    logging.debug('- Target `pcb_render` OK')
    # print_front target
    deps = targets['print_front'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-F_Cu+F_SilkS.pdf') in deps
    deps = targets[targets['print_front']].split(' ')
    assert len(deps) == 2
    assert board_file in deps
    assert yaml in deps
    logging.debug('- Target `print_front` OK')
    # drill target
    deps = targets['drill'].split(' ')
    assert len(deps) == 3, deps
    assert ctx.get_out_path(os.path.join('gerbers', prj+'-drill.drl')) in deps
    assert ctx.get_out_path(os.path.join('gerbers', prj+'-drill_report.txt')) in deps
    assert ctx.get_out_path(os.path.join('gerbers', prj+'-drill_map.pdf')) in deps
    deps = targets[targets['drill']].split(' ')
    assert len(deps) == 2
    assert board_file in deps
    assert yaml in deps
    logging.debug('- Target `drill` OK')
    # svg_sch_def
    deps = targets['svg_sch_def'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'.svg') in deps
    check_test_v5_sch_deps(ctx, targets[targets['svg_sch_def']].split(' '))
    logging.debug('- Target `svg_sch_def` OK')
    # svg_sch_int
    deps = targets['svg_sch_int'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-schematic.svg') in deps
    check_test_v5_sch_deps(ctx, targets[targets['svg_sch_int']].split(' '))
    logging.debug('- Target `svg_sch_int` OK')
    # pdf_sch_def
    deps = targets['pdf_sch_def'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'.pdf') in deps
    check_test_v5_sch_deps(ctx, targets[targets['pdf_sch_def']].split(' '))
    logging.debug('- Target `pdf_sch_def` OK')
    # pdf_sch_int
    deps = targets['pdf_sch_int'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-schematic.pdf') in deps
    check_test_v5_sch_deps(ctx, targets[targets['pdf_sch_int']].split(' '))
    logging.debug('- Target `pdf_sch_int` OK')
    # run_erc target
    deps = targets['run_erc'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-erc.txt') in deps
    check_test_v5_sch_deps(ctx, targets[targets['run_erc']].split(' '))
    logging.debug('- Target `run_erc` OK')
    # run_drc target
    deps = targets['run_drc'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-drc.txt') in deps
    deps = targets[targets['run_drc']].split(' ')
    assert len(deps) == 2
    assert board_file in deps
    assert yaml in deps
    logging.debug('- Target `run_drc` OK')
    # fake_sch target
    deps = targets['fake_sch'].split(' ')
    assert len(deps) == 6, deps
    check_test_v5_sch_deps(ctx, deps, extra=[ctx.get_out_path('n.lib'), ctx.get_out_path('y.lib'),
                                             ctx.get_out_path('sym-lib-table')], in_output=True)
    check_test_v5_sch_deps(ctx, targets[targets['fake_sch']].split(' '))
    logging.debug('- Target `fake_sch` OK')
    # 3D target
    deps = targets['3D'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(os.path.join('3D', prj+'-3D.step')) in deps
    deps = targets[targets['3D']].split(' ')
    assert os.path.relpath(ctx.board_file) in deps
    assert 'tests/data/R_0805_2012Metric.wrl' in deps
    assert yaml in deps
    # We can't check the WRL because it isn't included in the docker image
    logging.debug('- Target `3D` OK')
    # update_xml target
    deps = targets['update_xml'].split(' ')
    assert len(deps) == 1, deps
    assert os.path.abspath(deps[0]) == ctx.board_file.replace('kicad_pcb', 'xml')
    check_test_v5_sch_deps(ctx, targets[targets['update_xml']].split(' '))
    logging.debug('- Target `update_xml` OK')
    # kibom_internal target
    deps = targets['kibom_internal'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(os.path.join('BoM', prj+'-bom.html')) in deps
    check_test_v5_sch_deps(ctx, targets[targets['kibom_internal']].split(' '), [ctx.get_out_path('config.kibom.ini')])
    logging.debug('- Target `kibom_internal` OK')
    # archive target
    deps = targets['archive'].split(' ')
    assert len(deps) == 1, deps
    assert ctx.get_out_path(prj+'-archive.zip') in deps
    deps = targets[targets['archive']].split(' ')
    assert len(deps) == 16, deps
    # - position
    assert ctx.get_out_path(os.path.join(POS_DIR, prj+'-top_pos.csv')) in deps
    assert ctx.get_out_path(os.path.join(POS_DIR, prj+'-bottom_pos.csv')) in deps
    # - interactive_bom
    assert ctx.get_out_path(os.path.join('ibom', prj+'-ibom.html')) in deps
    # - 3D
    assert ctx.get_out_path(os.path.join('3D', prj+'-3D.step')) in deps
    # - drill
    assert ctx.get_out_path(os.path.join('gerbers', prj+'-drill.drl')) in deps
    assert ctx.get_out_path(os.path.join('gerbers', prj+'-drill_report.txt')) in deps
    assert ctx.get_out_path(os.path.join('gerbers', prj+'-drill_map.pdf')) in deps
    # - Other files
    assert ctx.get_out_path('error.txt') in deps
    assert ctx.get_out_path('output.txt') in deps
    assert ctx.get_out_path('Makefile') in deps
    assert ctx.get_out_path('config.kibom.ini') in deps
    assert ctx.get_out_path('positiondir') in deps
    assert ctx.get_out_path('ibom') in deps
    assert ctx.get_out_path('3D') in deps
    assert ctx.get_out_path('gerbers') in deps
    # - Config
    assert yaml in deps
    logging.debug('- Target `archive` OK')
    ctx.search_err(r'\(kibom_external\) \[kibom\] uses a name generated by the external tool')
    ctx.search_err(r'\(ibom_external\) \[ibom\] uses a name generated by the external tool')
    ctx.search_err(r'Wrong character in file name `(.*)/test_v5-top\$.svg')


def test_makefile_1(test_dir):
    prj = 'test_v5'
    ctx = context.TestContext(test_dir, 'test_makefile_1', prj, 'makefile_1', '')
    mkfile = ctx.get_out_path('Makefile')
    ctx.run(extra=['-s', 'all', 'archive'])
    ctx.run(extra=['-m', mkfile])
    check_makefile(ctx, mkfile, prj, '-v', r"^\t\$\(KIBOT_CMD\) -s (.*) -i$")
    ctx.clean_up()


def test_makefile_2(test_dir):
    prj = 'test_v5'
    ctx = context.TestContext(test_dir, 'test_makefile_2', prj, 'makefile_1', '')
    mkfile = ctx.get_out_path('Makefile')
    ctx.run(extra=['-s', 'all', 'archive'])
    ctx.run(extra=['-m', mkfile], no_verbose=True)
    check_makefile(ctx, mkfile, prj, '', r"^\t@\$\(KIBOT_CMD\) -s (.*) -i 2>> \$\(LOGFILE\)$")
    ctx.clean_up()


def test_empty_zip(test_dir):
    prj = 'test_v5'
    ctx = context.TestContext(test_dir, 'test_empty_zip', prj, 'empty_zip', '')
    ctx.run()
    ctx.expect_out_file(prj+'-result.zip')
    ctx.search_err('No files provided, creating an empty archive')
    ctx.clean_up()


def test_compress_fail_deps(test_dir, monkeypatch):
    ctx = context.TestContext(test_dir, 'test_compress_fail_deps', '3Rs', 'compress_fail_deps', 'Test')
    ctx.home_local_link()
    with monkeypatch.context() as m:
        m.setenv("HOME", os.path.join(ctx.get_board_dir(), '../..'))
        ctx.run(INTERNAL_ERROR)
    ctx.search_err(r"Unable to generate `dummy` from 'Test plug-in, dummy' \(do_test\) \[test\]")
    ctx.clean_up()


def test_import_1(test_dir):
    prj = 'test_v5'
    ctx = context.TestContext(test_dir, 'test_import_1', prj, 'import_test_1', '')
    ctx.run(extra=['-i'])
    ctx.search_err(r'Outputs loaded from `tests/yaml_samples/gerber_inner.kibot.yaml`: \[\'gerbers\', \'result\'\]')
    ctx.search_err(r'Outputs loaded from `tests/yaml_samples/ibom.kibot.yaml`: \[\'interactive_bom\'\]')
    ctx.clean_up()
