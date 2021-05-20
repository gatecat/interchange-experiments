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
    return wire2pins
# Site wire pip map
wire2downhill = {}
wire2uphill = {}

def build_pip_map(site, site_type):
    for bel in site_type.bels:
        if bel.category != 'routing':
            continue
        for pin in bel.get_pins(site):
            if pin.direction != Direction.Input:
                continue
            pip = site_type.site_pip(site, bel.name, pin.name)
            src_wire, dst_wire = pip.site_wires()
            if src_wire not in wire2downhill:
                wire2downhill[src_wire] = []
            if dst_wire not in wire2uphill:
                wire2uphill[dst_wire] = []
            wire2downhill[src_wire].append(dst_wire)
            wire2uphill[dst_wire].append(src_wire)

# wire to (input cones, output cones)
wire2cone = {}

def build_cone_map(site, site_type):
    def visit_fwd(wire, cone, visited):
        if wire in visited:
            return
        visited.add(wire)
        if wire not in wire2cone:
            wire2cone[wire] = ([], [])
        wire2cone[wire][1].append(cone)
        for downhill in wire2downhill.get(wire, []):
            visit_fwd(downhill, cone, visited)
    def visit_bwd(wire, cone, visited):
        if wire in visited:
            return
        visited.add(wire)
        if wire not in wire2cone:
            wire2cone[wire] = ([], [])
        wire2cone[wire][0].append(cone)
        for uphill in wire2uphill.get(wire, []):
            visit_bwd(uphill, cone, visited)
    for bel in site_type.bels:
        if bel.category != 'logic':
            continue
        for pin in bel.get_pins(site):
            wires = pin.site_wires()
            if len(wires) == 0:
                continue
            assert len(wires) == 1
            if pin.direction == Direction.Output:
                # track output cone
                visit_fwd(wires[0], (bel.name, pin.name), set())
            elif pin.direction == Direction.Input:
                # track input cone
                visit_bwd(wires[0], (bel.name, pin.name), set())
    # for (wire, (icones, ocones)) in sorted(wire2cone.items(), key = lambda x: x[0]):
    #     if len(ocones) > 1:
    #         print("Wire {} in output cones:".format(wire.name(site_type)))
    #         for (bel, pin) in ocones:
    #             print("    {}.{}".format(bel, pin))
    #     if len(icones) > 1:
    #         print("Wire {} in input cones:".format(wire.name(site_type)))
    #         for (bel, pin) in icones:
    #             print("    {}.{}".format(bel, pin))

def discover_dedicated_paths(site, site_type):
    print("Dedicated paths:")
    for bel in site_type.bels:
        if bel.category != 'logic':
            continue
        for pin in bel.get_pins(site):
            wires = pin.site_wires()
            if len(wires) == 0:
                continue
            assert len(wires) == 1
            if pin.direction == Direction.Input:
                ocone = wire2cone.get(wires[0], ([], []))[1]
                for (out_bel, out_pin) in ocone:
                    print("    {}.{} --> {}.{}".format(out_bel, out_pin, bel.name, pin.name))

def discover_uncontented_wires(site, site_type):
    # Wires only in amo input/output cone are much simpler to deal with
    print("Uncontented wires:")
    for (wire, (icones, ocones)) in sorted(wire2cone.items(), key = lambda x: x[0]):
        if len(ocones) <= 1 and len(icones) <= 1:
            print("    {}".format(wire.name(site_type)))

def discover_contented_pins(device, site, site_type):
    # First discover which bel pins have an uncontented route to an input/output
    uncontented_belpins = set()
    belpin_to_sitepin = {}
    # Remove pins with dedicated access to a top level pin, as they don't count towards contention
    # - we can always use an uncontented path for these
    def filter_cone(cone):
        return [p for p in cone if p not in uncontented_belpins]
    for pin_name in site_type.site_pins.keys():
        site_pin = site_type.site_pin(site, device, pin_name)
        wire = site_pin.site_wires()[0]
        if wire not in wire2cone:
            continue
        icones, ocones = wire2cone[wire]
        if len(icones) == 1 and site_pin.direction == Direction.Input:
            uncontented_belpins.add(icones[0])
        elif len(ocones) == 1 and site_pin.direction == Direction.Output:
            uncontented_belpins.add(ocones[0])
    for pin_name in sorted(site_type.site_pins.keys()):
        site_pin = site_type.site_pin(site, device, pin_name)
        wire = site_pin.site_wires()[0]
        if wire not in wire2cone:
            continue
        icones, ocones = wire2cone[wire]
        icones = filter_cone(icones)
        ocones = filter_cone(ocones)

        for (bel, pin) in icones:
            if (bel, pin) not in belpin_to_sitepin:
                belpin_to_sitepin[(bel, pin)] = []
            belpin_to_sitepin[(bel, pin)].append(pin_name)
        for (bel, pin) in ocones:
            if (bel, pin) not in belpin_to_sitepin:
                belpin_to_sitepin[(bel, pin)] = []
            belpin_to_sitepin[(bel, pin)].append(pin_name)

        if len(icones) > 1 and site_pin.direction == Direction.Input:
            print("Contented input {}:".format(pin_name))
            for (bel, pin) in icones:
                print("    {}.{}".format(bel, pin))
        if len(ocones) > 1 and site_pin.direction == Direction.Output:
            print("Contented output {}:".format(pin_name))
            for (bel, pin) in ocones:
                print("    {}.{}".format(bel, pin))
    return (uncontented_belpins, belpin_to_sitepin)

# Currently we are generating pseudocode, to experiment without a proper codegen yet
def codegen_var(name):
    return name
def codegen_get_pin(bel, pin):
    return ("get_pin(BEL_{}, PORT_{})".format(bel, pin))
def codegen_null():
    return "null"
def codegen_if(cond, t, f=[]):
    return ["if {} then".format(cond)] + \
        ["    {}".format(x) for x in t] + \
        ((["else"] + ["   {}".format(x) for x in f]) if len(f) > 0 else []) + \
        ["endif"]
def codegen_assign(var, val):
    return ["{} ← {}".format(var, val)]
def codegen_eq(x, y):
    return "{} = {}".format(x, y)
def codegen_neq(x, y):
    return "{} ≠ {}".format(x, y)
def codegen_reject():
    return ["reject"]
def codegen_blank():
    return [""]

def label(section):
    return ["{}:".format(section)]

def codegen_accept(section):
    return ["goto {}".format(section)]

def codegen_write(out, x):
    for l in x:
        print(l, file=out)

# The common check-assign pattern in validity checks
def check_assign(wire, value, accept=[]):
    return codegen_if(
        codegen_neq(value, codegen_null()),
        codegen_if(codegen_eq(value, codegen_null()),
            codegen_assign(wire, value) + accept,
            codegen_if(codegen_neq(wire, value),
                codegen_reject(),
                accept,
            )
        )
    )

def codegen_shared(out, wire2pins, site_type):
    code = []
    for wire, pins in sorted(wire2pins.items(), key = lambda x: x[0]):
        if len(pins) <= 1:
            continue
        wire_var = codegen_var("wire_{}".format(wire.name(site_type)))
        code += codegen_assign(wire_var, codegen_null())
        for bel, pin in pins:
            pin_var = codegen_var("pin_{}_{}".format(bel, pin))
            code += codegen_assign(pin_var, codegen_get_pin(bel, pin))
            code += check_assign(wire_var, pin_var)

        code += codegen_blank()
    codegen_write(out, code)

def codegen_ipins(out, uncontented_belpins, wire2cone, belpin_to_sitepin, site, site_type):
    code = []
    sitepin_count = {}
    for site_pins in belpin_to_sitepin.values():
        for sp in site_pins:
            sitepin_count[sp] = sitepin_count.get(sp, 0) + 1
    sitepin_to_var = {}
    for sp, count in sorted(sitepin_count.items(), key=lambda x: x[0]):
        if count < 2:
            continue
        sp_var = codegen_var("sitepin_{}".format(sp))
        code += codegen_assign(sp_var, codegen_null())
        sitepin_to_var[sp] = str(sp_var)

    for bel in site_type.bels:
        if bel.category != 'logic':
            continue
        for pin in bel.get_pins(site):
            wires = pin.site_wires()
            if len(wires) == 0:
                continue
            assert len(wires) == 1
            if pin.direction != Direction.Input:
                continue
            if (bel.name, pin.name) in uncontented_belpins:
                continue
            # Get signal
            pin_var = codegen_var("ipin_{}_{}".format(bel.name, pin.name))
            end_lbl = "{}_{}_done".format(bel.name, pin.name)
            code += codegen_assign(pin_var, codegen_get_pin(bel.name, pin.name))
            # Not connected
            code += codegen_if(codegen_eq(pin_var, codegen_null()), codegen_accept(end_lbl))
            # Dedicated path
            ocone = wire2cone.get(wires[0], ([], []))[1]
            for (out_bel, out_pin) in ocone:
                code += codegen_if(codegen_eq(pin_var, codegen_get_pin(out_bel, out_pin)), codegen_accept(end_lbl))
            # Use a site pin
            # TODO: check conflicts en route and possibly backtrack needed too...
            for sp in belpin_to_sitepin.get((bel.name, pin.name), []):
                sp_var = sitepin_to_var[sp]
                code += codegen_if(codegen_eq(sp_var, codegen_null()),
                           codegen_assign(sp_var, pin_var) + codegen_accept(end_lbl),
                           codegen_if(codegen_eq(sp_var, pin_var),
                               codegen_accept(end_lbl),
                           )
                       )
            code += codegen_reject()
            code += label(end_lbl)
            code += codegen_blank()
    codegen_write(out, code)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema_dir', required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--site_type', required=True)
    parser.add_argument('--codegen')

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
    build_pip_map(site, site_type)
    wire2pins = find_shared_signals(site, site_type)
    build_cone_map(site, site_type)
    discover_uncontented_wires(site, site_type)
    discover_dedicated_paths(site, site_type)
    (uncontented_belpins, belpin_to_sitepin) = discover_contented_pins(device, site, site_type)


    if "codegen" in args:
        with open(args.codegen, "w") as pseudocode:
            print("# Shared wires", file=pseudocode)
            codegen_shared(pseudocode, wire2pins, site_type)
            print("# Input pins", file=pseudocode)
            codegen_ipins(pseudocode, uncontented_belpins, wire2cone, belpin_to_sitepin, site, site_type)
if __name__ == '__main__':
    main()
