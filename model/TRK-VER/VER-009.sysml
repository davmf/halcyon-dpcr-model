package 'VER-009' {
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

    verification verSysDrp001 : ModelCheck {
        doc /* Droplets per channel from partition volume and droplet volume. */
        objective { verify 'SYS-DRP-001'; }
        attribute :>> observed = DropletCount(partitionVolume = baseSteady.configuration.cartridge.partitionVolume, dropletVolume = baseSteady.configuration.generators.dropletVolume);
    }
}
