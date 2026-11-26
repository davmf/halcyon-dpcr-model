package 'VER-UTL-001-HT' {
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

    verification <'VER-UTL-001-HT'> verSysUtl001HighThroughput : SimulationVerification {
        doc /* Mean imager utilisation, high-throughput configuration (two imagers). */
        objective { verify 'SYS-UTL-001'; }
        attribute :>> measured = 'SYS-UTL-001'.measuredImagerUtilisation;
        attribute :>> metric = MetricKind::utilisation;
        ref part :>> scenario = highThroughput;
        ref part :>> resource = highThroughput.configuration.imagers;
    }
}
