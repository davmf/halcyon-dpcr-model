package 'SC-006' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;

    part def HighThroughputBatch :> Scenario {
        part :>> configuration : HighThroughputInstrument;
        attribute :>> arrivals : BatchArrival {
            :>> count = 24;
            :>> time = 0 [s];
        }
    }
}
