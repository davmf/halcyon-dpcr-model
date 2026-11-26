package 'TRK-SC' {
    @StrictDocWorkspace::Tracker { title = "Scenarios"; kind = "design"; prefix = "SC"; }
    doc /*
     * Configurations and scenarios of the analyser.
     *
     * Base: two thermal blocks, one imager, one batch of 24 at shift start.
     * SteadyStat: base configuration, Poisson arrivals at 12 per hour, 10%
     * STAT. HighThroughput: three thermal blocks, two imagers, same arrivals
     * as SteadyStat. HighThroughputBatch: the same units with the base batch.
     */

    public import 'SC-001'::*;
    public import 'SC-002'::*;
    public import 'SC-003'::*;
    public import 'SC-004'::*;
    public import 'SC-005'::*;
    public import 'SC-006'::*;
    public import 'SC-007'::*;
    public import 'SC-008'::*;
    public import 'SC-009'::*;
    public import 'SC-010'::*;
}
