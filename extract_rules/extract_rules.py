import argparse

from fpga_interchange.interchange_capnp import Interchange
from fpga_interchange.logical_netlist import Direction


# Find signals shared between multiple bels
def find_shared_signals(site, site_type):
    wire2pins = dict()
    for bel in site_type.bels:
        if bel.category != 'logic':
            continue
        for pin in bel.get_pins(site):
            if pin.direction != Direction.Input:
                continue
            wires = pin.site_wires()
            if len(wires) == 0:
                continue
            assert len(wires) == 1
            if wires[0] not in wire2pins:
                wire2pins[wires[0]] = []
            wire2pins[wires[0]].append((bel.name, pin.name))
    for wire, pins in sorted(wire2pins.items(), key = lambda x: x[0]):
        if len(pins) <= 1:
            continue
        print("Wire {}:".format(wire.name(site_type)))
        for (bel, pin) in pins:
            print("    {}.{}".format(bel, pin))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema_dir', required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--site_type', required=True)
    args = parser.parse_args()
    interchange = Interchange(args.schema_dir)

    with open(args.device, 'rb') as f:
        device = interchange.read_device_resources(f)

    site_type_idx = device.site_type_name_to_index[args.site_type]
    site_type = device.get_site_type(site_type_idx)
    # find a specimen site of the correct type
    site = None
    for site_types in device.site_name_to_site.values():
        for site_value in site_types.values():
            if site_value.site_type_index == site_type_idx:
                site = site_value
                break
    find_shared_signals(site, site_type)

if __name__ == '__main__':
    main()
