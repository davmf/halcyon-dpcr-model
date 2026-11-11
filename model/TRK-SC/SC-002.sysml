package 'SC-002' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;

    part def HighThroughputInstrument :> Instrument {
        part :>> stations {
            attribute :>> capacity = 4;
        }
        part :>> pneumatics {
            attribute :>> capacity = 2;
        }
        part :>> generators {
            attribute :>> capacity = 2;
        }
        part :>> blocks {
            attribute :>> capacity = 3;
        }
        part :>> imagers {
            attribute :>> capacity = 2;
        }
    }
}
