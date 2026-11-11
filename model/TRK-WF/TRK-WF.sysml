package 'TRK-WF' {
    @StrictDocWorkspace::Tracker { title = "Workflow"; kind = "design"; prefix = "WF"; }
    doc /*
     * ISA-88 procedural model for one sample. The procedure has five unit
     * procedures (intake, extraction, partitioning, amplification,
     * readout). Each unit procedure has operations, and each operation has
     * phases, which are Steps. Equipment is bound in the allocation
     * package. A partition fails both droplet checks with probability
     * pLowDroplets squared. The readout draws that outcome, and a failed run
     * goes to a retest step (retest = true). An aborted cartridge also goes
     * to a retest step.
     */

    public import 'WF-001'::*;
    public import 'WF-PROC'::*;
}
