package 'HW-002' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def Shuttle :> Resource {
        doc /* XY transport of cartridges between units. One move at a time. */
        attribute strokeLength : LengthValue = 0.6 [m];
    }
}
