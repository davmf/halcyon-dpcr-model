package 'PHY-005' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def DropletGenerationTime {
        doc /* Volume per channel / (droplet volume * generation frequency). */
        in partitionVolume : VolumeValue;
        in dropletVolume : VolumeValue;
        in frequency : FrequencyValue;
        return : DurationValue = partitionVolume / (dropletVolume * frequency);
    }
}
