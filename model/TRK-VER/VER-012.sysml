package 'VER-012' {
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

    verification verSysOps001 : ModelCheck {
        doc /* Seconds of master mix at the nominal arrival rate, from the reagent store (SI). */
        objective { verify 'SYS-OPS-001'; }
        attribute :>> observed = baseSteady.configuration.reagentStore.initialLevel / 12 [1/h];
    }
}
