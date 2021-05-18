import argparse

from fpga_interchange.interchange_capnp import Interchange
from fpga_interchange.logical_netlist import Direction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema_dir', required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--site_type', required=True)
    args = parser.parse_args()
    interchange = Interchange(args.schema_dir)

    with open(args.device, 'rb') as f:
        device = interchange.read_device_resources(f)

    for lut_element in device.device_resource_capnp.lutDefinitions.lutElements:
        if lut_element.site != args.site_type:
            continue
        for lut in lut_element.luts:
            print("LUT size: {}".format(lut.width))
            bel_to_lut = {}
            init_to_lut = [[] for i in range(lut.width)]
            pin_to_lut = {}
            for bel in lut.bels:
                bel_to_lut[bel.name] = bel
                print("     bel: {} [{}:{}]".format(bel.name, bel.highBit, bel.lowBit))
                for i in range(bel.lowBit, bel.highBit + 1):
                    init_to_lut[i].append((bel.name, i - bel.lowBit))
                for i, pin in enumerate(bel.inputPins):
                    if pin not in pin_to_lut:
                        pin_to_lut[pin] = []
                    pin_to_lut[pin].append((lut, i))
            lut_sizes = [0 for i in range(len(lut.bels))]
            def try_placement(i):
                total_bits = sum(2**x for x in lut_sizes)
                if i == len(lut.bels) or total_bits > lut.width:
                    # Leaf
                    print("Trying placement: ")
                    for j, k in enumerate(lut_sizes):
                        if k == 0:
                            continue
                        print("    {}: LUT{}".format(lut.bels[j].name, k))
                else:
                    # Branch
                    for j in range(len(lut.bels[i].inputPins) + 1):
                        lut_sizes[i] = j
                        try_placement(i + 1)
                        lut_sizes[i] = 0
            try_placement(0)
if __name__ == '__main__':
    main()
