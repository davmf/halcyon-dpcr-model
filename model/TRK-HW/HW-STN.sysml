package 'HW-STN' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-STN'> ExtractionStation :> Resource {
        doc /* One station with heater and magnet. Capacity is four. */
        part heater : Heater;
        part magnet : Magnet;
    }
}
