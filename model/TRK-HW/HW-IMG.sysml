package 'HW-IMG' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-IMG'> FluorescenceImager :> Resource {
        doc /* Imager with one exposure per channel. Shared between cartridges. */
        attribute channels : Natural = 4;
        attribute timePerChannel : DurationValue = 45 [s];
    }
}
