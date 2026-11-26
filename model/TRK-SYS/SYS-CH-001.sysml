package 'SYS-CH-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-CH-001'> 'Channels per cartridge' {
        doc /*
         * The instrument shall partition each sample into four
         * channels, one per target of the multiplex panel.
         */
        attribute requiredChannels : Natural = 4;
        attribute measuredChannels : Natural;
        require constraint {
            measuredChannels == requiredChannels
        }
    }

    dependency from 'SYS-CH-001' to 'STK-LAB-001';
}
