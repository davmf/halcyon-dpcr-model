package 'SYS-OPS-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-OPS-001'> 'Unattended operation' {
        doc /*
         * The instrument shall run for 8 hours without an operator
         * refilling reagents or emptying waste.
         */
        attribute requiredHours : DurationValue = 8 [h];
        attribute measuredHours : DurationValue;
        require constraint {
            measuredHours >= requiredHours
        }
    }

    dependency from 'SYS-OPS-001' to 'STK-OPS-001';
}
