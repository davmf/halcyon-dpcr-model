package 'TRK-HW' {
    @StrictDocWorkspace::Tracker { title = "Hardware"; kind = "design"; prefix = "HW"; }
    doc /*
     * Physical model of the dPCR-24 analyser (ISA-88 equipment).
     *
     * Identical units are one part with a capacity: the stations, the
     * pneumatic controllers, the droplet generators, the thermal blocks
     * and the imagers. Counts are set in the configuration (allocation
     * package and scenarios package).
     */

    public import 'HW-001'::*;
    public import 'HW-002'::*;
    public import 'HW-003'::*;
    public import 'HW-HTR'::*;
    public import 'HW-004'::*;
    public import 'HW-STN'::*;
    public import 'HW-PNU'::*;
    public import 'HW-CART'::*;
    public import 'HW-DGN'::*;
    public import 'HW-TCB'::*;
    public import 'HW-IMG'::*;
    public import 'HW-005'::*;
    public import 'HW-REA'::*;
    public import 'HW-006'::*;
}
