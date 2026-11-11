package 'HW-TCB' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-TCB'> ThermalBlock :> BatchResource {
        doc /*
         * Thermal cycler block holding four cartridges. Each batch starts
         * when four cartridges wait, or after the batch timeout.
         */
        attribute :>> batchSize = 4;
        attribute :>> batchTimeout = 10 [min];
        attribute rampRate : Real = 4;
        attribute hotStartTime : DurationValue = 5 [min];
        attribute cycles : Natural = 40;
        attribute denatureHold : DurationValue = 15 [s];
        attribute annealHold : DurationValue = 30 [s];
        attribute rampDelta : Real = 35;
    }
}
