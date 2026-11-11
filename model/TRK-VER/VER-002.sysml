package 'VER-002' {
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

    verification verSysThr001 : SimulationVerification {
        doc /* Completed samples per 8-hour shift at nominal load. */
        objective { verify 'SYS-THR-001'; }
        attribute :>> measured = 'SYS-THR-001'.measuredSamplesPerShift;
        attribute :>> metric = MetricKind::completedPerShift;
        attribute :>> horizon = 8 [h];
        ref part :>> scenario = baseSteady;
    }
}
