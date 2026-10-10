package FixtureParts {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import FixtureRequirements::*;

    part def Pump {
        attribute flowRate : Real = 2.5;
        attribute setPressure : PressureValue = 50000 [Pa];
    }

    part pump : Pump;

    satisfy 'FIX-001' by pump;
}
