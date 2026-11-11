package 'VER-TAT-001-HT' {
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

    verification <'VER-TAT-001-HT'> verSysTat001HighThroughput : SimulationVerification {
        doc /* First result of the 24-sample batch, high-throughput configuration. */
        objective { verify 'SYS-TAT-001'; }
        attribute :>> measured = 'SYS-TAT-001'.measuredTimeToFirstResult;
        attribute :>> metric = MetricKind::timeToFirstResult;
        attribute :>> horizon = 3 [h];
        ref part :>> scenario = highThroughputBatch;
    }
}
