package 'STK-F-QUALITY' {
    @StrictDocWorkspace::Folder { title = "Quality"; }
    doc /*
     * Validity of reported results.
     */

    public import 'STK-VAL-001'::*;
    public import 'STK-VAL-002'::*;
    public import 'STK-LAB-001'::*;
}
