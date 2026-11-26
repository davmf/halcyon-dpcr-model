package 'SYS-VAL-002' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-VAL-002'> 'Reflex retest' {
        doc /*
         * The instrument shall retest each invalid run once with a
         * new cartridge without operator action.
         */
        attribute requiredRetests : Natural = 1;
        attribute measuredRetests : Natural;
        require constraint {
            measuredRetests >= requiredRetests
        }
    }

    dependency from 'SYS-VAL-002' to 'STK-VAL-002';
}
