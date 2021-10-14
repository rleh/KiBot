# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Options to better control the rotation filter (#60 and #67):
  - invert_bottom: bottom angles are inverted.
  - skip_top: top components aren't rotated.
  - skip_bottom: bottom components aren't rotated.
- XLSX BoM: option to control the logo scale (#84)
- Import mechanism for filters and variants (#88)
- PDF PCB Print: option `hide_excluded` to hide components marked by the
  `exclude_filter`.
  https://forum.kicad.info/t/fab-drawing-for-only-through-hole-parts/
- Internal BoM: option to avoid merging components with empty fields.
  Is named `merge_both_blank` and defaults to true.
- Internal BoM: when a `Value` field can't be interpreted as a `number+unit`,
  and it contain at least one space, now we try to use the text before the
  space. This helps for cases like "10K 1%".

### Changed
- Internal BoM: now components with different Tolerance, Voltage, Current
  and/or Power fields aren't grouped together.
  These fields are now part of the default `group_fields`. (#79)

### Fixed
- Position files now defaults to use the auxiliar origin as KiCad.
  Can be disabled to use absolute coordinates. (#87)
- Board View: flipped output. (#89)
- Board View: problems with netnames using spaces. (#90)


## [0.11.0] - 2021-04-25
### Added
- `erc_warnings` pre-flight option to consider ERC warnings as errors.
- Pattern expansion in the `dir` option for outputs (#58)
- New filter types:
  - `suparts`: Adds support for KiCost's subparts feature.
  - `field_rename`: Used to rename schematic fields.
  - `var_rename_kicost`: Like `var_rename` but using KiCost mechanism.
- New KiCost variant style.
- `skip_if_no_field` and `invert` options to the regex used in the generic
  filter.
- Board view file format export (#69)
- Experimental mechanism to change 3D models according to the variant.
- Support for width, style and color in "wire notes" (#70)
- Level and comment to columns in the XLSX BoM output.
- Basic KiCost support (**experimental**).
- Basic internal BoM and KiCost integration (**experimental**).

### Changed
- Errors and warnings from KiAuto now are printed as errors and warnings.
- Schematic dependencies are sorted in the generated Makefiles.
- Makefile variables KIBOT, DEBUG and LOGFILE can be defined from outside.
- Reference ranges of two elements no longer represented as ranges.
  Examples: "R1-R2" is now "R1 R2", "R1-R3" remains unchanged.

### Fixed
- Problem when using E/DRC filters and the output dir didn't exist.
- Not all errors during makefile generation were catched (got a stack trace).
- Output dirs created when generating a makefile for a compress target.
- Problems with some SnapEDA libs (extra space in lib termination tag #57)
- The "References" (plural) column is now coloured as "Reference" (singular)

## [0.10.1] - 2021-02-22
### Added
- GitLab CI workaround
- Verbosity level is now passed to KiAuto

## [0.10.0-4] - 2021-02-16
### Fixed
- Problem using Python 3.6 (ZipFile's compresslevel arg needs 3.7)

## [0.10.0-3] - 2021-02-16
### Fixed
- Problem using Python 3.6 (StreamHandler.setStream introduced in 3.7)

## [0.10.0-2] - 2021-02-12
### Fixed
- Missing python3-distutils dependency on Debian package.

## [0.10.0] - 2021-02-12
### Added
- The multipart id to references of multipart components others than part 1.
- Internal BoM:
  - `no_conflict` option to exclude fields from conflict detection.
  - HTML tables can be sorted selecting a column (Java Script).
  - You can consolidate more than one project in one BoM.
- Support for KICAD_CONFIG_HOME defined from inside KiCad.
- Now layers can be selected using the default KiCad names.
- More control over the name of the drill and gerber files.
- More options to customize the excellon output.
- Custom reports for plot outputs (i.e. custom gerber job generation)
- Example configurations for gerber and drill files for:
  - [Elecrow](https://www.elecrow.com/)
  - [FusionPCB](https://www.seeedstudio.io/fusion.html)
  - [JLCPCB](https://jlcpcb.com/)
  - [P-Ban](https://www.p-ban.com/)
  - [PCBWay](https://www.pcbway.com)
- Support for ZIP/TAR/RAR generation.
- Makefile generation.
- KiAuto time-out control.
- Now you can import outputs from another config file.

### Changed
- Now the default output name applies to the DRC and ERC report names.
  This provides more coherent file names.
- Internal BoM: The "Quantity" column no longer includes the DNF/C status.
  This status was moved to a separated column named `Status`.
  You can join both columns if you want.
- Internal BoM: HTML rows are highlighted on hover (not just the cell).
- Now information messages go to stdout (not stderr).
  Debug, warning and error messages still use stderr.
- Now InteractiveHtmlBom can be installed just as a plugin.

### Fixed
- Extra data about drill marks in gerber files.
- Problems using internal names for drill maps in gerb_drill output (#47).
- Problems using layer suffixes containing non-ASCII chars (i.e. UTF-8).
- Problems when using components with more than 10 subparts.


## [0.9.0] - 2021-01-04
### Added
- iBoM output: file name patterns are allowed for the `netlist_file` option.
- File name patterns: %F is the name of the source file without extension, but
  with the path.
- A hint for pip installations without using `--no-compile`.
- Support to field overwrite according to variant.
- Support to generate negative X positions for the bottom layer.
- A filter to rotate footprints in the position file (#28).
- The step output now can download missing 3D models.

### Changed
- Now position files are naturally sorted (R10 after R9, not after R1)
- Position files in CSV format quotes only the columns that could contain an
  space. Just like KiCad does.

### Fixed
- Now we support missing field names in schematic library entries.
- Generic filter `include_only` option worked only when debug enabled.

## [0.8.1] - 2020-12-09
### Added
- Internal BoM HTML: highlight cell when hover.
- Internal BoM HTML: allow to jump to REF of row number using anchors.

### Fixed
- Internal BoM separator wasn't applied when using `use_alt`
- Problems loading plug-ins when using `pip`.

## [0.8.0] - 2020-11-06
### Added
- The KiBoM and internal BoM generators now support configuring the
  separator used for the list of references.
- Help for filters and variants.
- Support for new `pcbnew_do export` options.
- Filters for KiBot warnings.
- Columns in position files can be selected, renamed and sorted as you
  like.

### Fixed
- KiBom variants when using multiple variants and a component uses more
  than one, specifying opposite rules.
- Problems when using the `pdf_pcb_print` output and variants to remove
  a component with ridiculous pads that only has solder paste (no
  copper, nor even solder mask aperture).
- Excellon drill output when using unified output and not using default
  KiCad names.


## [0.7.0] - 2020-09-11
### Added
- Now variants are separated entities. Two flavors implemented: KiBoM
  and IBoM.
- New filters entities. They work in complement with variants.
  All the filtering functionality found in KiBoM and IBoM is supported.
- Most outputs now supports variants. You can:
  - Mark not fitted components with a cross in the schematic
  - Mark not fitted components with a cross in the *.Fab layers of the
    PCB
  - Remove solder paste from not fitted components
  - Remove adhesive glue from not fitted components
  - Exclude components from the BoM (also mark them as DNF and/or DNC
    (Do Not Change))
  - Exclude components from the interactive BoM
  - Remove not fitted components from the STEP file
  - Exclude components from the position (pick & place) file
- Default output file name format and default variant can be specified
  from the command line.

### Fixed
- Virtual components are always excluded from position files.
  Note you can change it using the variants mechanism.

## [0.6.2] - 2020-08-25
### Changed
- Discarded spaces at the beggining and end of user fields when creating the
  internal BoM. They are ususally mistakes that prevents grouping components.

### Fixed
- The variants logic for BoMs when a component resquested to be only added to
  more than one variant.
- Removed warnings about malformed values for DNF components indicating it in
  its value.
- Problems with PcbDraw when generating PNG and JPG outputs. Now we use a more
  reliable conversion methode when available.

## [0.6.1] - 2020-08-20
### Added
- More robust behavior on GUI dependent commands.

### Changed
- Incorporated mcpy, no longer a dependency.

### Fixed
- Problems when using `pip install` without --no-compile.
  At least for user level install.

## [0.6.0] - 2020-08-18
### Added
- Internal BoM generator, based on KiBoM code.
  This generator doesn't need the netlist, works directly from the SCH.
  It features enhanced HTML and XLSX outputs, in addition to the CSV, TSV, TXT
  and XML traditional outputs.
- Support for full KiBoM configuration from the YAML
- Added output to print to an SVG file.
- Added default output file name pattern. Can be applied to all outputs.
- Unified output name:
  - `pdf_pcb_print.output` can be used instead of `pdf_pcb_print.output_name`
  - `gerber.gerber_job_file` option to control the gerber job file name.
  - `output` option to control the file name to all plot output formats.
  - `drill`, `drill.map` and `position` file names can be configured.
  - Output file names supports expansion of various interesting values (base
    name, sheet title, revision, etc.).
- The filters now accept the following aliases (suggested by @leoheck):
  - `filter_msg` -> `filter`
  - `error_number` -> `number`
  - `regexp` -> `regex`

### Changed
- Default file names for:
  - pdf_pcb_print: includes the used layers
  - drill maps: uses drill instead of drl
  - drill: uses drill instead of drl, used in gbr and drl.
  - position: no -pos in CSVs
  - step: adds -3D
  - pdf_sch_print: adds -schematic
  - IBoM: contains the project name.

## [0.5.0] - 2020-07-11
### Changed
- Removed the "plot" option "check_zone_fills". Use the preflight option.
- Drill outputs: map.type and report.filename now should be map and report.
  The old mechanism is currently supported, but deprecated.
- Now the command line usage is more clearly documented, but also more strict.
- The --list option doesn't need a PCB file anymore.
  Note that passing it is now considered an error.
- Now we test the PCB and/or SCH only when we are doing something that needs
  them.

### Added
- The layers entry is much more flexible now.
  Many changes, read the README.md
- PcbDraw output.
- -e/--schematic option to specify any schematic (not just derived from the PCB
  name.
- -x/--example option to generate a complete configuration example.
- --example supports --copy-options to copy the plot options from the PCB file.
- Help for the supported outputs (--help-list-outputs, --help-outputs and
  --help-output)
- Help for the supported preflights (--help-preflights)
- Better YAML validation.
- Added HPGL options:
  - pen_number
  - pen_speed
- Added metric_units to DXF options
- Added KiBoM options
  - number
  - variant
  - conf
  - separator
- Added the following InteractiveHtmlBom options:
  - dark_mode
  - hide_pads
  - show_fabrication
  - hide_silkscreen
  - highlight_pin1
  - no_redraw_on_drag
  - board_rotation
  - checkboxes
  - bom_view
  - layer_view
  - include_tracks
  - include_nets
  - sort_order
  - no_blacklist_virtual
  - blacklist_empty_val
  - netlist_file
  - extra_fields
  - normalize_field_case
  - variant_field
  - variants_whitelist
  - variants_blacklist
  - dnp_field

### Fixed
- The `sketch_plot` option is now implemented.
- 'ignore_unconnected' preflight wasn't working.
- The report of hwo many ERC/DRC errors we found.

## [0.4.0] - 2020-06-17
### Added
- STEP 3D model generation
- Support for unpatched InteractiveHtmlBom

## [0.3.0] - 2020-06-14
### Added
- Better debug information when a BoM fails to be generated.
- Support for compressed YAML files.

### Changed
- Allow operations that doesn't involve a PCB to run if the PCB file is
  missing or corrupted.
- The 'check_zone_fills' option is now independent of 'run_drc'

### Fixed
- Error codes that overlapped.

## [0.2.5] - 2020-06-11
### Added
- Tolerate config files without outputs
- Mechanism to filter ERC/DRC errors

### Fixed
- All pcbnew plot formats generated gerber job files
- Most formats that needed layers didn't complain when ommited

## [0.2.4] - 2020-05-19
### Changed
- Now kicad-automation-scripts 1.3.1 or newer is needed.

### Fixed
- Problems for kibom and print_sch outputs when the PCB name included a path.

## [0.2.3] - 2020-04-23
### Added
- List available targets

## [0.2.2] - 2020-04-20
### Fixed
- KiBoM temporal files, now removed
- pre-flight tasks that didn't honor --out-dir

## [0.2.1] - 2020-04-18
### Fixed
- Problem when the excellon drill target directory didn't exist (now created)

## [0.2.0] - 2020-03-28
### Added
- Documentation for current functionality
- Now the -b and -c options are optional, we guess the values
- Inner layers sanitation, support for the names used in the PCB file
- Better error report
- Print the PCB and SCH in PDF format (we had plot)
- KiBoM and InteractiveHtmlBoM support
- Pre-flight: generation of the BoM in XML format
- Pre-flight: DRC and ERC
- Option to skip pre-flight actions
- Option to select which outputs will be generated
- Progress information
- --version option

### Fixed
- Debian dependencies

## [0.1.1] - 2020-03-13
### Added
- Pick & place position
- Debian package
- Gerber job generation

