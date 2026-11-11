package 'VER-010' {
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

    verification verSysLys001 : ModelCheck {
        doc /* Heater maximum set point against the lysis temperature. */
        objective { verify 'SYS-LYS-001'; }
        attribute :>> observed = baseSteady.configuration.stations.heater.maxTemperature;
    }
}
