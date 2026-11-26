package 'HW-004' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import SimLib::*;
    private import 'TRK-HW'::*;

    part def Magnet {
        doc /* Permanent magnet for bead capture. */
        attribute fieldStrength : MagneticFluxDensityValue = 0.4 [T];
    }
}
