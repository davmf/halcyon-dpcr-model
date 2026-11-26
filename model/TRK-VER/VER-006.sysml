package 'VER-006' {
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

    verification verSysTat003 : SimulationVerification {
        doc /* Mean turnaround of STAT samples at nominal load. */
        objective { verify 'SYS-TAT-003'; }
        attribute :>> measured = 'SYS-TAT-003'.measuredMeanStatTurnaround;
        attribute :>> metric = MetricKind::meanStatTurnaround;
        attribute :>> horizon = 16 [h];
        ref part :>> scenario = baseSteady;
    }
}
