package 'SC-005' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;

    part def HighThroughputSteadyStat :> Scenario {
        part :>> configuration : HighThroughputInstrument;
        attribute :>> arrivals : PoissonArrival {
            :>> rate = 12 [1/h];
            :>> statFraction = 0.1;
        }
        attribute :>> warmUpTime = 1 [h];
    }
}
