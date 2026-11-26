package 'PHY-004' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def DropletCount {
        doc /* Droplets per channel: partition volume / droplet volume. */
        in partitionVolume : VolumeValue;
        in dropletVolume : VolumeValue;
        return : Real = partitionVolume / dropletVolume;
    }
}
