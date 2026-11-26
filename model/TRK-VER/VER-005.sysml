package 'VER-005' {
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

    verification verSysTat002 : SimulationVerification {
        doc /* Mean turnaround at nominal load. */
        objective { verify 'SYS-TAT-002'; }
        attribute :>> measured = 'SYS-TAT-002'.measuredMeanTurnaround;
        attribute :>> metric = MetricKind::meanTurnaround;
        attribute :>> horizon = 16 [h];
        ref part :>> scenario = baseSteady;
    }
}
