package 'HW-DGN' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-DGN'> DropletGenerator :> Resource {
        doc /* Flow-focusing junction generator. Capacity is two. */
        attribute junctionWidth : LengthValue = 0.05 [mm];
        attribute dropletVolume : VolumeValue = 0.85e-6 [mL];
        attribute dropletFrequency : FrequencyValue = 120 [Hz];
    }
}
