package 'HW-PNU' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-PNU'> PneumaticController :> Resource {
        doc /* Pressure controller that drives all on-cartridge flow. */
        attribute setPressure : PressureValue = 20000 [Pa];
    }
}
