package 'TRK-SYS' {
    @StrictDocWorkspace::Tracker { title = "System requirements"; kind = "requirements"; prefix = "SYS"; }
    doc /*
     * System requirements of the dPCR-24 analyser. Each requirement is
     * derived from a stakeholder requirement. Measured attributes are
     * filled by simulation or by model checks in the verification package.
     */

    public import 'SYS-F-THROUGHPUT'::*;
    public import 'SYS-F-TURNAROUND'::*;
    public import 'SYS-F-QUALITY'::*;
    public import 'SYS-F-OPERATIONS'::*;
}
