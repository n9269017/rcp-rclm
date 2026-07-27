import RcpRclmFormalCoreV4.Autonomous.Infinite

namespace RcpRclmFormalCoreV4
namespace Autonomous

open RcpRclmFormalCoreV2
open RcpRclmFormalCoreV3

/-- Executable-contract name for the second finite frontier. -/
abbrev RecursiveProductivityFrontier (Task : Type*) := Finset Task

/-- Host-route data forbidden from the Phase 14 search input. -/
structure ForbiddenRouteHints where
  nextSuccessfulTransitionIndexPresent : Bool
  requiredSuccessfulComponentSetPresent : Bool
  acceptedProgramBytesPresent : Bool
  expectedCandidateHashPresent : Bool
  expectedNewCapabilityPresent : Bool
  expectedFinalModelIdentityPresent : Bool
  hostSelectedObjectivePresent : Bool

/-- All route-level answers are absent. -/
def ForbiddenRouteHints.clear (hints : ForbiddenRouteHints) : Prop :=
  hints.nextSuccessfulTransitionIndexPresent = false ∧
  hints.requiredSuccessfulComponentSetPresent = false ∧
  hints.acceptedProgramBytesPresent = false ∧
  hints.expectedCandidateHashPresent = false ∧
  hints.expectedNewCapabilityPresent = false ∧
  hints.expectedFinalModelIdentityPresent = false ∧
  hints.hostSelectedObjectivePresent = false

/-- Phase 14 name for a complete Gate E accepted step. -/
abbrev ScheduleFreeAcceptedStep := @AutonomousAcceptedStep

/-- Phase 14 name for deterministic relative search completeness. -/
abbrev RelativeSearchCompleteness := @bounded_search_complete

/-- Phase 14 name for proof-carrying bounded exhaustion. -/
abbrev CertifiedSearchExhaustion := @SearchExhaustionCertificate

end Autonomous
end RcpRclmFormalCoreV4
