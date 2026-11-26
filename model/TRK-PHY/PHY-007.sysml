package 'PHY-007' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def ImagingTime {
        doc /* Imaging all channels of one cartridge, one after another. */
        in channels : Natural;
        in timePerChannel : DurationValue;
        return : DurationValue = channels * timePerChannel;
    }
}
