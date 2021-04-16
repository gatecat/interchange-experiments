# Example of embedding executable code in a nextpnr BBA

This is a questionable attempt at embedding executable machine code inside a structure equivalent to the BBA nextpnr uses.

At the moment this is a simple demo where the 'plugin' just squares numbers.

But ultimately, the idea is we can generate optimal, arch-specific site validity checking code when doing the interchange to bba step for much faster validity checks in the nextpnr-fpga_interchange project.



