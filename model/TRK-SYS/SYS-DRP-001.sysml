package 'SYS-DRP-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-DRP-001'> 'Droplets per channel' {
        doc /*
         * The instrument shall generate at least 15,000 droplets in
         * each channel of a cartridge before amplification.
         */
        attribute requiredDropletsPerChannel : Real = 15000;
        attribute measuredDropletsPerChannel : Real;
        require constraint {
            measuredDropletsPerChannel >= requiredDropletsPerChannel
        }
    }

    dependency from 'SYS-DRP-001' to 'STK-VAL-001';
}
