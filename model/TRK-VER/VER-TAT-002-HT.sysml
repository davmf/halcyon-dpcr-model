package 'VER-TAT-002-HT' {
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

    verification <'VER-TAT-002-HT'> verSysTat002HighThroughput : SimulationVerification {
        doc /* Mean turnaround at nominal load, high-throughput configuration. */
        objective { verify 'SYS-TAT-002'; }
        attribute :>> measured = 'SYS-TAT-002'.measuredMeanTurnaround;
        attribute :>> metric = MetricKind::meanTurnaround;
        attribute :>> horizon = 16 [h];
        ref part :>> scenario = highThroughput;
    }
}
