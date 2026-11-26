package 'SC-003' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;

    part def BaseBatch :> Scenario {
        part :>> configuration : BaseInstrument;
        attribute :>> arrivals : BatchArrival {
            :>> count = 24;
            :>> time = 0 [s];
        }
    }
}
