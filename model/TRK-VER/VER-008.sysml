package 'VER-008' {
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

    verification verSysVal002 : ModelCheck {
        doc /* Reflex retests configured per invalid run. */
        objective { verify 'SYS-VAL-002'; }
        attribute :>> observed = baseSteady.configuration.maxRetests;
    }
}
