package 'TRK-STK' {
    @StrictDocWorkspace::Tracker { title = "Stakeholder requirements"; kind = "requirements"; prefix = "STK"; }
    doc /*
     * Needs of the laboratory manager and the client laboratories that
     * send swab samples. Derived system requirements are in the system
     * requirements package.
     */

    public import 'STK-F-THROUGHPUT'::*;
    public import 'STK-F-TURNAROUND'::*;
    public import 'STK-F-QUALITY'::*;
    public import 'STK-F-PRIORITY'::*;
}
