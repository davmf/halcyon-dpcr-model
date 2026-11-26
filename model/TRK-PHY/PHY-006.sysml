package 'PHY-006' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-PHY'::*;

    calc def ThermalRunTime {
        doc /*
         * Hot start, then cycles of denature hold, anneal hold and two
         * ramps. The ramp rate is the block's rate in kelvin per second.
         */
        in hotStart : DurationValue;
        in cycles : Natural;
        in denatureHold : DurationValue;
        in annealHold : DurationValue;
        in rampDelta : Real;
        in rampRate : Real;
        return : DurationValue = hotStart + cycles * (denatureHold + annealHold + 2 * rampDelta / rampRate);
    }
}
