package 'PHY-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def ChannelVolume {
        doc /* Volume of a cylindrical channel: pi d^2 L / 4. */
        in diameter : LengthValue;
        in length : LengthValue;
        return : VolumeValue = 3.14159265 * diameter * diameter * length / 4;
    }
}
