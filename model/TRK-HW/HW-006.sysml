package 'HW-006' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def WasteStore :> Store {
        doc /* Waste reservoir. Emptied by an operator. */
        attribute :>> initialLevel = 0;
    }
}
