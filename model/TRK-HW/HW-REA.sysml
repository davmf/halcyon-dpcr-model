package 'HW-REA' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-REA'> ReagentStore :> Store {
        doc /* Master mix reagent cartridges. Refilled from the reorder level. */
        attribute :>> initialLevel = 100;
        attribute :>> reorderLevel = 20;
        attribute :>> refillSize = 96;
        attribute :>> refillDuration = 15 [min];
    }
}
