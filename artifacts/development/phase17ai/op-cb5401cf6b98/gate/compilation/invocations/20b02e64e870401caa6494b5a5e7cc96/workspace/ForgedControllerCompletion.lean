import ControllerAuthority
namespace Phase17ControllerAuthorityControl
open Phase17ProducerDomain Phase17ControllerAuthority Phase17ControllerAuthorityExamples
set_option maxRecDepth 32768
set_option maxHeartbeats 16000000
def wrongClaim : Bool := decide (complete policy0 contexts0 evaluators0 "head" "head" state0_1 { completion0_0 with execution := Phase17ProducerDomainExamples.state0_0 } ≠ none)
theorem actual_rejection : wrongClaim = false := by
  unfold wrongClaim
  have invalid : ¬ CompletionValid policy0 contexts0 evaluators0 state0_1
      { completion0_0 with execution := Phase17ProducerDomainExamples.state0_0 } := by
    intro valid
    have run := valid.2.2.2.2.2.2.2.1
    change authorizedReplay Phase17ProducerDomainExamples.grant0 Phase17ProducerDomainExamples.grant0 Phase17ProducerDomainExamples.grant0.binding Phase17ProducerDomainExamples.context0 Phase17ProducerDomainExamples.evaluator0 2
      Phase17ProducerDomainExamples.state0_0 Phase17ProducerDomainExamples.observations0 = some Phase17ProducerDomainExamples.state0_0 at run
    rw [Phase17ProducerDomainExamples.case_first_source] at run
    have different : Phase17ProducerDomainExamples.state0_1 ≠ Phase17ProducerDomainExamples.state0_0 := by decide +kernel
    exact different (Option.some.inj run)
  simp only [complete, invalid, and_false, if_false, ne_eq, not_true_eq_false, decide_false]

example : wrongClaim = true := by
  simp only [actual_rejection, Bool.false_eq_true]
  decide
end Phase17ControllerAuthorityControl
