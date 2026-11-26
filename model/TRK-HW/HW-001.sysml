package 'HW-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def SampleRack :> Resource {
        doc /* 24 sample positions and a barcode reader. */
        attribute slots : Natural = 24;
    }
}
