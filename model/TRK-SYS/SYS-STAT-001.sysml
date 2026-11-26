package 'SYS-STAT-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-STAT-001'> 'STAT priority' {
        doc /*
         * The instrument shall grant STAT work items priority over
         * routine work items at the pipetting gantry and the imager.
         */
        attribute requiredPriorityLevels : Natural = 2;
        attribute measuredPriorityLevels : Natural;
        require constraint {
            measuredPriorityLevels >= requiredPriorityLevels
        }
    }

    dependency from 'SYS-STAT-001' to 'STK-STAT-001';
}
