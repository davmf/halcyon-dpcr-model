package 'SYS-LYS-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-LYS-001'> 'Lysis temperature capability' {
        doc /*
         * The instrument shall heat extraction stations to at least
         * 95 degrees Celsius for lysis.
         */
        attribute requiredLysisTemperature : Real = 95;
        attribute measuredLysisTemperature : Real;
        require constraint {
            measuredLysisTemperature >= requiredLysisTemperature
        }
    }

    dependency from 'SYS-LYS-001' to 'STK-VAL-001';
}
