package 'TRK-AL' {
    @StrictDocWorkspace::Tracker { title = "Allocation"; kind = "design"; prefix = "AL"; }
    doc /*
     * Configuration of the analyser (ISA-88 process cell). The abstract
     * Instrument owns the physical units, the sample procedure and every
     * allocation of a step to equipment. Concrete configurations (scenarios
     * package) set the capacity of each unit.
     *
     * An allocation seizes the unit for the duration of the step. A step
     * with several allocations seizes all of them. An allocation to a
     * Store draws the step's consumes amount when the step starts.
     */

    public import 'AL-INS'::*;
}
