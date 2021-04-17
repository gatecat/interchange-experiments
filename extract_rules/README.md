`extract_rules` is an experiment to look for common patterns in SLICE routing validity checking.

Typical things that need to be dealt with are:
 1. control sets e.g. clock, set/reset, enables shared between flipflops
 2. input contention e.g. Xilinx 'X' input shared between mux select and flipflop data
 3. output contention e.g. Xilinx 'MUX' outputs can be used for many different signals
 4. dedicated paths that must be used

in (2) and (3) dedicated paths like LUT->FF can often be an alternative to using a contented input/output and this must be considered.

(1) might be complicated in some cases by site pips (e.g. constants) between the shared wire and the pin.

The kind of stuff we want to automagically analyse is similar to https://github.com/daveshah1/nextpnr-xilinx/blob/xilinx-upstream/xilinx/arch_place.cc#L44-L298