package 'PHY-002' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def HagenPoiseuilleFlow {
        doc /* Volume flow rate of laminar flow: pi d^4 dP / (128 mu L). */
        in pressure : PressureValue;
        in viscosity : DynamicViscosityValue;
        in length : LengthValue;
        in diameter : LengthValue;
        return : VolumeFlowRateValue = 3.14159265 * diameter * diameter * diameter * diameter * pressure / (128 * viscosity * length);
    }
}
