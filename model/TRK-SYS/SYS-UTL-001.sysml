package 'SYS-UTL-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-UTL-001'> 'Imager utilisation' {
        doc /*
         * The instrument shall keep the mean utilisation of the
         * fluorescence imagers at or below 85% at nominal load.
         *
         * .. image:: _assets/utilisation-baseSteady.svg
         *    :alt: Simulated utilisation per resource, baseSteady scenario
         *    :class: image
         */
        attribute requiredImagerUtilisation : Real = 0.85;
        attribute measuredImagerUtilisation : Real;
        require constraint {
            measuredImagerUtilisation <= requiredImagerUtilisation
        }
    }

    dependency from 'SYS-UTL-001' to 'STK-THR-001';
}
