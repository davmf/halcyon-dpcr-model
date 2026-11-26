package 'VER-004' {
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

    verification verSysTat001 : SimulationVerification {
        doc /* First result of the 24-sample batch loaded at shift start. */
        objective { verify 'SYS-TAT-001'; }
        attribute :>> measured = 'SYS-TAT-001'.measuredTimeToFirstResult;
        attribute :>> metric = MetricKind::timeToFirstResult;
        attribute :>> horizon = 3 [h];
        ref part :>> scenario = baseBatch;
    }
}
