package 'VER-013' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-WF'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;
    private import 'TRK-PHY'::*;
    private import 'TRK-SYS'::**;
    private import 'TRK-VER'::*;

    verification verSysStat001 : ModelCheck {
        doc /* Priority levels used by work items (routine and STAT). */
        objective { verify 'SYS-STAT-001'; }
        attribute :>> observed = 2;
    }
}
