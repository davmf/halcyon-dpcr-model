package 'SYS-THR-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-THR-001'> 'Shift throughput' {
        doc /*
         * The instrument shall complete at least 96 samples in an
         * 8-hour shift at nominal load.
         *
         * .. image:: _assets/scenario-comparison.svg
         *    :alt: Simulated throughput per shift against the 96 threshold
         *    :class: image
         */
        attribute requiredSamplesPerShift : Real = 96;
        attribute measuredSamplesPerShift : Real;
        require constraint {
            measuredSamplesPerShift >= requiredSamplesPerShift
        }
    }

    dependency from 'SYS-THR-001' to 'STK-THR-001';
}
