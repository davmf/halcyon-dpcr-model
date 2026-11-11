package 'STK-OPS-001' {
    private import 'TRK-STK'::*;

    requirement <'STK-OPS-001'> 'Walk-away time' {
        doc /*
         * The laboratory needs to leave the instrument running for
         * at least 8 hours without an operator reloading consumables.
         */
    }
}
