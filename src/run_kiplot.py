#!/usr/bin/env python3
"""
    @package
    KiPlot - KiCad Python API plotter

    KiPlot is a program which helps you to plot your KiCad PCBs to output
    formats easily, repeatable, and most of all, scriptably. This means you
    can use a Makefile to export your KiCad PCBs just as needed.

"""
import sys
import os
here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(here))
from kiplot.__main__ import main

main()
