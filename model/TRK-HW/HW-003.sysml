package 'HW-003' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def PipettingGantry :> Resource {
        doc /* Pipettes sample, wash, elution and master mix. Shared. */
        attribute tipCount : Natural = 8;
    }
}
