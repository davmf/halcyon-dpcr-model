package 'PHY-003' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def PrimingTime {
        doc /* Time to fill the priming channel: channel volume / flow rate. */
        in pressure : PressureValue;
        in viscosity : DynamicViscosityValue;
        in length : LengthValue;
        in diameter : LengthValue;
        return : DurationValue = ChannelVolume(diameter, length) / HagenPoiseuilleFlow(pressure, viscosity, length, diameter);
    }
}
