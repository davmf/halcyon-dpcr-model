package 'SC-007' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;
    private import 'TRK-SYS'::*;

    part baseBatch : BaseBatch;

    satisfy 'SYS-TAT-001' by baseBatch.configuration;
}
