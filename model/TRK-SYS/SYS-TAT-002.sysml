package 'SYS-TAT-002' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-TAT-002'> 'Mean turnaround' {
        doc /*
         * The instrument shall keep the mean turnaround at or below
         * 2.5 hours at nominal load.
         */
        attribute requiredMeanTurnaround : DurationValue = 2.5 [h];
        attribute measuredMeanTurnaround : DurationValue;
        require constraint {
            measuredMeanTurnaround <= requiredMeanTurnaround
        }
    }

    dependency from 'SYS-TAT-002' to 'STK-TAT-002';
}
