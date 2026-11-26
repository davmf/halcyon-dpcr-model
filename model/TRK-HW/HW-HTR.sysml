package 'HW-HTR' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def <'HW-HTR'> Heater {
        doc /* Block heater of an extraction station. */
        attribute maxTemperature : Real = 100;
    }
}
