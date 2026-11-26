package 'VER-007' {
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

    verification verSysVal001 : SimulationVerification {
        doc /* Invalid results after reflex retesting at nominal load. */
        objective { verify 'SYS-VAL-001'; }
        attribute :>> measured = 'SYS-VAL-001'.measuredInvalidRate;
        attribute :>> metric = MetricKind::invalidRate;
        attribute :>> horizon = 16 [h];
        ref part :>> scenario = baseSteady;
    }
}
