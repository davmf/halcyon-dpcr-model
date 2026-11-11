package 'VER-011' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;
    private import 'TRK-WF'::*;
    private import 'TRK-AL'::*;
    private import 'TRK-SC'::*;
    private import 'TRK-PHY'::*;
    private import 'TRK-SYS'::**;
    private import 'TRK-VER'::*;

    verification verSysCh001 : ModelCheck {
        doc /* Channels per cartridge. */
        objective { verify 'SYS-CH-001'; }
        attribute :>> observed = baseSteady.configuration.cartridge.channelCount;
    }
}
