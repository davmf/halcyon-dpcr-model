package 'SC-008' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;
    private import 'TRK-SYS'::*;

    part baseSteady : BaseSteadyStat;

    satisfy 'SYS-THR-001' by baseSteady.configuration;
    satisfy 'SYS-THR-001' by baseSteady.configuration.cartridge;
    satisfy 'SYS-UTL-001' by baseSteady.configuration.imagers;
    satisfy 'SYS-TAT-002' by baseSteady.configuration;
    satisfy 'SYS-TAT-003' by baseSteady.configuration;
    satisfy 'SYS-VAL-001' by baseSteady.configuration.cartridge;
    satisfy 'SYS-VAL-002' by baseSteady.configuration;
    satisfy 'SYS-DRP-001' by baseSteady.configuration.generators;
    satisfy 'SYS-DRP-001' by baseSteady.configuration.cartridge;
    satisfy 'SYS-LYS-001' by baseSteady.configuration.stations.heater;
    satisfy 'SYS-CH-001' by baseSteady.configuration.cartridge;
    satisfy 'SYS-OPS-001' by baseSteady.configuration.reagentStore;
    satisfy 'SYS-STAT-001' by baseSteady.configuration;
}
