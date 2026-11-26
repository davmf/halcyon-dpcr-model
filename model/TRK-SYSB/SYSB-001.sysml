package 'SYSB-001' {
    private import 'TRK-SYSB'::*;
    private import StateMachineProfile::*;

    part MasterStateDiagram : StateMachine {
        :>> name = "MasterStateDiagram";

        part :>> top : Region {
            part init : Pseudostate { :>> kind = PseudostateKind::initial; }
            part idle : State { :>> name = "Idle"; }
            part busy : State { :>> name = "Busy"; }
            connection initToIdle : Transition connect init.outgoing to idle.incoming {
                :>> classification = TransitionClassification::primary;
            }
            connection IdleToBusy : Transition connect idle.outgoing to busy.incoming {
                :>> classification = TransitionClassification::primary;
            }
        }
    }
}
