package 'TRK-PHY' {
    @StrictDocWorkspace::Tracker { title = "Physics"; kind = "design"; prefix = "PHY"; }
    doc /*
     * Step physics as calc defs over part attributes. No external solver.
     * Units are SI. Values are evaluated by the simulation generator.
     */

    public import 'PHY-001'::*;
    public import 'PHY-002'::*;
    public import 'PHY-003'::*;
    public import 'PHY-004'::*;
    public import 'PHY-005'::*;
    public import 'PHY-006'::*;
    public import 'PHY-007'::*;
}
