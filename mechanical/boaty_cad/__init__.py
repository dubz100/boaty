"""Boaty Mk1 mechanical design in CadQuery (BOATY-MDD-001).

params    every dimension, with the requirement it answers
util      shared geometry (sections, threads, knurled knobs)
hull      the six hull segments, dowels
structure crossbeams, box, saddle tray, latches, camera hood, DUPLO deck,
          key
mast      mast step and handle, tube, collar and hoop, flag staff,
          masthead, thumb-screws
pod       thruster pod, prop, rear guard, reference motor
assembly  places every part; one frame for the whole boat
analysis  mass, hydrostatics, stability and the compliance checks
build     exports STEP/STL, results JSON and figures
"""
