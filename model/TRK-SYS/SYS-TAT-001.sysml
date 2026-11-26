package 'SYS-TAT-001' {
    private import ScalarValues::*;
    private import ISQ::*;
    private import SI::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-TAT-001'> 'Time to first result' {
        doc /*
         * The instrument shall report the first result of a batch
         * within 90 minutes of batch loading.
         *
         * .. image:: _assets/first-result-comparison.svg
         *    :alt: Time to first result for a batch of 24 against the 90 minute threshold
         *    :class: image
         */
        attribute requiredTimeToFirstResult : DurationValue = 90 [min];
        attribute measuredTimeToFirstResult : DurationValue;
        require constraint {
            measuredTimeToFirstResult <= requiredTimeToFirstResult
        }
    }

    dependency from 'SYS-TAT-001' to 'STK-TAT-001';
}
