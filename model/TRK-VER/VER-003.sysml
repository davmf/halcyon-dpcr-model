package 'VER-003' {
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

    verification verSysUtl001 : SimulationVerification {
        doc /* Mean imager utilisation at nominal load. */
        objective { verify 'SYS-UTL-001'; }
        attribute :>> measured = 'SYS-UTL-001'.measuredImagerUtilisation;
        attribute :>> metric = MetricKind::utilisation;
        ref part :>> scenario = baseSteady;
        ref part :>> resource = baseSteady.configuration.imagers;
    }
}
