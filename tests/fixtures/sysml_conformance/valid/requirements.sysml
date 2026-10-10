package FixtureRequirements {
    private import ScalarValues::*;

    requirement <'FIX-001'> 'Flow rate' {
        doc /* The pump shall deliver at least 2 units per second. */
        attribute requiredFlowRate : Real = 2;
        attribute measuredFlowRate : Real;
        require constraint { measuredFlowRate >= requiredFlowRate }
    }
}
