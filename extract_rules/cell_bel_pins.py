import argparse

from fpga_interchange.interchange_capnp import Interchange
from fpga_interchange.logical_netlist import Direction

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema_dir', required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--cell_type', required=True)
    args = parser.parse_args()
    interchange = Interchange(args.schema_dir)

    with open(args.device, 'rb') as f:
        device = interchange.read_device_resources(f)

    # Find which cells can be placed on this site
    site_type_cells = set()
    pin_options = {}
    for m in device.yield_cell_bel_mappings():
        if m.cell != args.cell_type:
            continue
        for st, bt in sorted(m.site_types_and_bels):
            print("{}/{}".format(st, bt))
        for pins in (m.common_pins, m.parameter_pins):
            for k, pin_map in sorted(pins.items(), key=lambda x: x[0]):
                print(k)
                if len(k) == 4:
                    print("    param: {}={}".format(k[2], k[3]))
                for b, c in pin_map.items():
                    if c not in pin_options:
                        pin_options[c] = set()
                    pin_options[c].add(b)
    print()
    for c, b in sorted(pin_options.items(), key=lambda x: x[0]):
        print("{} -> {{{}}}".format(c, ", ".join(sorted(b))))

if __name__ == '__main__':
    main()
