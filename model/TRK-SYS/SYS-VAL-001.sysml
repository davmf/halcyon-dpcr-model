package 'SYS-VAL-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-VAL-001'> 'Invalid result rate' {
        doc /*
         * The instrument shall report at most 2% invalid results at
         * nominal load, including reflex retests.
         */
        attribute requiredInvalidRate : Real = 0.02;
        attribute measuredInvalidRate : Real;
        require constraint {
            measuredInvalidRate <= requiredInvalidRate
        }
    }

    dependency from 'SYS-VAL-001' to 'STK-VAL-001';
}
