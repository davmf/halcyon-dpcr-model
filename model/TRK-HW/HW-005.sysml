package 'HW-005' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def AnalysisComputer :> Resource {
        doc /* Computes Poisson copy numbers from the four channel images. One unit. */
    }
}
