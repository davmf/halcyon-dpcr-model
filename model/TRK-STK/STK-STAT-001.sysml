package 'STK-STAT-001' {
    private import 'TRK-STK'::*;

    requirement <'STK-STAT-001'> 'STAT handling' {
        doc /*
         * The laboratory needs STAT samples to take precedence over
         * routine samples at shared equipment.
         */
    }
}
