package 'SYS-TAT-003' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-TAT-003'> 'STAT turnaround' {
        doc /*
         * The instrument shall report STAT samples within 2 hours of
         * loading at nominal load.
         */
        attribute requiredMeanStatTurnaround : DurationValue = 2 [h];
        attribute measuredMeanStatTurnaround : DurationValue;
        require constraint {
            measuredMeanStatTurnaround <= requiredMeanStatTurnaround
        }
    }

    dependency from 'SYS-TAT-003' to 'STK-TAT-003';
}
