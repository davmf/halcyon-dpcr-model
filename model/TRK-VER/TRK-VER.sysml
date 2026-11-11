package 'TRK-VER' {
    @StrictDocWorkspace::Tracker { title = "Verification"; kind = "test cases"; prefix = "VER"; }
    doc /*
     * Verification cases. Each SYS requirement has one case. Simulated
     * metrics use SimulationVerification from SimLib. Design checks use
     * ModelCheck, which compares the observed design value with the
     * requirement's measured attribute. The satisfy statements link design
     * elements to each SYS requirement.
     */

    public import 'VER-001'::*;
    public import 'VER-002'::*;
    public import 'VER-003'::*;
    public import 'VER-004'::*;
    public import 'VER-005'::*;
    public import 'VER-006'::*;
    public import 'VER-007'::*;
    public import 'VER-008'::*;
    public import 'VER-009'::*;
    public import 'VER-010'::*;
    public import 'VER-011'::*;
    public import 'VER-012'::*;
    public import 'VER-013'::*;
    public import 'VER-THR-001-HT'::*;
    public import 'VER-UTL-001-HT'::*;
    public import 'VER-TAT-001-HT'::*;
    public import 'VER-TAT-002-HT'::*;
}
