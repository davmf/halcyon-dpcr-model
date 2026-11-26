package 'WF-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-PHY'::*;
    private import 'TRK-HW'::*;
    private import 'TRK-WF'::*;

    item def Sample :> WorkItem {
        doc /*
         * One work item. Its result is INVALID when the run ends with no
         * reportable result and no retest is left (see the conventions).
         */
    }
}
