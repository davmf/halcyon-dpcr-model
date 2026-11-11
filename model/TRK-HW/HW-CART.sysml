package 'HW-CART' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-CART'> Cartridge {
        doc /*
         * Single-use cartridge. Channel geometry and fluid properties are
         * fixed per cartridge type.
         */
        attribute channelCount : Natural = 4;
        attribute channelDiameter : LengthValue = 0.1 [mm];
        attribute primingPathLength : LengthValue = 0.3 [m];
        attribute fluidViscosity : DynamicViscosityValue = 0.002 [Pa*s];
        attribute partitionVolume : VolumeValue = 0.017 [mL];
    }
}
