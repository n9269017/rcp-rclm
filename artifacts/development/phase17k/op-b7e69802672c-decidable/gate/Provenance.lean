import RcpRclmFormalCoreV4
import Mathlib.Tactic

namespace Phase17Provenance

/- Hashes, score-table construction and physical bindings are checked externally.
   This model checks deterministic present-prefix selection from the entire table.
   It does not attest that a historical process ran or furnish a full root step. -/
structure RankedProgram where
  key : String
  family : Nat
  baseScore : Int
  ties : List Nat
  deriving DecidableEq

structure Context where
  generator : String
  parentPackage : String
  contextHash : String
  transcriptHash : String
  credits : Nat
  offset : Nat
  rows : List RankedProgram
  deriving DecidableEq

structure Proposal where
  generator : String
  parentPackage : String
  contextHash : String
  transcriptHash : String
  choices : List Nat
  verdicts : List Bool
  program : String
  candidatePackage : String
  deriving DecidableEq

structure CandidateView where
  parentPackage : String
  contextHash : String
  program : String
  package : String
  deriving DecidableEq

def rowAt (c : Context) (i : Nat) : RankedProgram :=
  c.rows.getD i { key := "", family := 8, baseScore := 0, ties := [] }

def rejectedCount (c : Context) (seen : List Nat) (family : Nat) : Nat :=
  (seen.filter (fun i => (rowAt c i).family == family)).length

def score (c : Context) (seen : List Nat) (i : Nat) : Int :=
  (rowAt c i).baseScore + 797 * Int.ofNat (rejectedCount c seen (rowAt c i).family)

def tie (c : Context) (seen : List Nat) (i : Nat) : Nat :=
  (rowAt c i).ties.getD (rejectedCount c seen (rowAt c i).family) 0

def beats (c : Context) (seen : List Nat) (i j : Nat) : Bool :=
  decide (score c seen i > score c seen j ∨
    (score c seen i = score c seen j ∧ tie c seen i > tie c seen j) ∨
    (score c seen i = score c seen j ∧ tie c seen i = tie c seen j ∧ i > j))

def choose (c : Context) (seen : List Nat) : Option Nat :=
  if seen.length < 4 then
    match (List.range c.rows.length).filter (fun i => !seen.contains i) with
    | [] => none
    | first :: rest => some (rest.foldl (fun best i => if beats c seen i best then i else best) first)
  else
    ((List.range 32).map (fun i => (c.offset + 17 * i) % 32)).find? (fun i => !seen.contains i)

def follows (c : Context) (seen : List Nat) : List Nat → Bool
  | [] => true
  | i :: rest => (choose c seen == some i) && follows c (seen ++ [i]) rest

def ContextValid (c : Context) : Prop :=
  c.rows.length = 32 ∧ c.credits ≤ 32 ∧ c.offset < 32 ∧
  (c.rows.map (fun r => r.key)).Nodup ∧
  ∀ r ∈ c.rows, r.family < 8 ∧ r.ties.length = 5

def Produced (c : Context) (p : Proposal) : Prop :=
  p.generator = c.generator ∧ p.parentPackage = c.parentPackage ∧
  p.contextHash = c.contextHash ∧ p.transcriptHash = c.transcriptHash ∧
  ContextValid c ∧ follows c [] p.choices = true ∧ p.choices.Nodup ∧
  p.choices.length ≤ c.credits ∧ p.choices ≠ [] ∧
  p.verdicts = List.replicate (p.choices.length - 1) false ++ [true] ∧
  p.program = (rowAt c (p.choices.getD (p.choices.length - 1) 32)).key ∧
  p.candidatePackage ≠ p.parentPackage

def CandidateMatches (c : Context) (p : Proposal) (result : CandidateView) : Prop :=
  Produced c p ∧ result.parentPackage = c.parentPackage ∧
  result.contextHash = c.contextHash ∧ result.program = p.program ∧
  result.package = p.candidatePackage

theorem trace_no_repeat (c : Context) (p : Proposal) (h : Produced c p) :
    p.choices.Nodup := by
  rcases h with ⟨_, _, _, _, _, _, unique, _⟩
  exact unique

open RcpRclmFormalCoreV2 RcpRclmFormalCoreV3

/- Supplies the actual six provenance fields. The remaining compatible kernel and
   physical observation projections are parameters, not discharged premises. -/
def attachProvenance
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView) :
    Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base :=
  { other with
    activeGenerator := fun s => (observe s).generator
    activePackageHash := fun s => (observe s).parentPackage
    generatorBound := fun s g => g = (observe s).generator ∧ ContextValid (observe s)
    proposalProducedBy := fun g s p => g = (observe s).generator ∧ Produced (observe s) p
    proposalBindsCandidate := fun s p candidate => CandidateMatches (observe s) p (candidateView candidate)
    packageHashBound := fun s g hash => g = (observe s).generator ∧
      hash = (observe s).parentPackage ∧ ContextValid (observe s) }

theorem attached_generator_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (valid : ContextValid (observe s)) :
    (attachProvenance other observe candidateView).generatorBound s
      ((attachProvenance other observe candidateView).activeGenerator s) := ⟨rfl, valid⟩

theorem attached_package_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (valid : ContextValid (observe s)) :
    (attachProvenance other observe candidateView).packageHashBound s
      ((attachProvenance other observe candidateView).activeGenerator s)
      ((attachProvenance other observe candidateView).activePackageHash s) := ⟨rfl, rfl, valid⟩

theorem attached_proposal_produced
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (p : Proposal) (produced : Produced (observe s) p) :
    (attachProvenance other observe candidateView).proposalProducedBy
      ((attachProvenance other observe candidateView).activeGenerator s) s p := ⟨rfl, produced⟩

theorem attached_candidate_bound
    {State Update BaseCertificate Protected ResidualIndex Task : Type*}
    [DecidableEq Task]
    {base : RCP.Kernel State Update BaseCertificate Protected ResidualIndex}
    (other : Learned.FrontierKernel (Task := Task) (Generator := String)
      (Proposal := Proposal) (PackageHash := String) base)
    (observe : State → Context) (candidateView : RCP.Candidate State Update → CandidateView)
    (s : State) (p : Proposal) (candidate : RCP.Candidate State Update)
    (matched : CandidateMatches (observe s) p (candidateView candidate)) :
    (attachProvenance other observe candidateView).proposalBindsCandidate s p candidate := matched

end Phase17Provenance

namespace Phase17Provenance
set_option maxRecDepth 16384
set_option maxHeartbeats 4000000
def selectedContext : Context := { generator := "9cd3e747c0e1a93a02ac5bff1d3a07fa7706172ae4a75a0a373629260a675dc5", parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", contextHash := "6668900a9ec4dadb06e51489ea7a3751b801cab7ff9657a80bb44d74337cf2f6", transcriptHash := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", credits := 32, offset := 20, rows := [{ key := "0ccebe71727ce54ff3a19b21fe576e09d43e44f9e2e08ad36dcef047c1f79757", family := 7, baseScore := 19500, ties := [9543860648081008819, 3986821735351615470, 825746532280847598, 17001314346561978364, 13351325592102680237] }, { key := "0e14e91e830ffbf45bf7393807a5aade7d3ee8687c812c947e3cc2531cbf63ac", family := 0, baseScore := 19478, ties := [2478412217797925231, 4952073402234272453, 6410835891427668742, 7585352493249011854, 564345016447607857] }, { key := "1ecfac36f3c68428ba26508bca2f0c8db4a78db705c2389bf06c702fbd5f10b5", family := 4, baseScore := 19453, ties := [6926660447509656195, 15938766398069759487, 10415543623678175031, 13840774463448155652, 15518046404860127241] }, { key := "2cf62e580eb264801c146a82d7946b8ff3876c007ef906f4fa2ae155c2763933", family := 4, baseScore := 19511, ties := [8150133364245794037, 15602764634322946874, 13392954838966468289, 7903206724535872410, 10389729442995148786] }, { key := "2ecde82a7df7ff5575e47e129aa9f6763c0e9ee3000ef68a9e34d3c9597fe4a8", family := 7, baseScore := 19457, ties := [6267249027547442838, 11802557578107583196, 3573854276885852263, 4632763963828844255, 8078852471064255554] }, { key := "3c53b375ed7d796a6ead3f57edff0ca2bec48cd0d82d3f00e94891e20f67cf37", family := 2, baseScore := 19513, ties := [3711246983035555146, 9392402904921580765, 17780474027121794000, 3396803482688375717, 6849742246718093496] }, { key := "3d77cb7cac506bf87708193dfc6e6f77e291a65ef4827f51da60cad2816ac308", family := 1, baseScore := 19477, ties := [2649540343373259679, 6846808915173765847, 17515316580299738942, 17893706698655125100, 7295491786506786006] }, { key := "4022426ee83c2c3f99e3575db0b0dfdb2ee9c21d84c0dcd4bd16beddc79e9f1e", family := 2, baseScore := 19461, ties := [3367686222335547501, 2334632568370419648, 15738148556525812901, 13876416194485205561, 17090631277782618190] }, { key := "4677d24595acdc93eb98a8756accf75cc209e7cb65f3da91fc413998d938bc90", family := 1, baseScore := 19463, ties := [2408805383885846081, 15698376057770116370, 11965904924747752585, 14474548167273289030, 112542496099690264] }, { key := "4a94e6caf0ffc3e0042b150248d3b002375fe03953dbe05505f1eec92e7540f3", family := 5, baseScore := 19421, ties := [18026470090072901573, 8661548565402000749, 4104814434003148999, 12331012964429129284, 17835237858885086118] }, { key := "4e46438f039bc9e03f8418bb954a356470a2b7ab19cf6325098d1a3c84693436", family := 3, baseScore := 19482, ties := [9906582390397776349, 15344037628855689015, 11288843140053017474, 6981166375638331370, 16932492284211806416] }, { key := "5e093ff6378d7f51505e59154e642e54387f7e69536a47f038047309db2f21e4", family := 6, baseScore := 19469, ties := [12442890687401092662, 2810638280771006471, 4340151003288216385, 12539753374090342698, 12694902134990752429] }, { key := "62284df64ad409933f2b7fb08307d037bc75b0af758f5b3f81de191803d00c6d", family := 4, baseScore := 19488, ties := [17395010458261258995, 13841608280534480694, 6864139855934553582, 3515426712982889939, 501085376997440217] }, { key := "634b6e89afa828bd87e36e8862f536c3053b84fa776eb102c3dc8d948d6915e7", family := 3, baseScore := 19480, ties := [7443435974636069586, 17015840504638147347, 14078768256273083565, 923609335749601218, 2117103808860832839] }, { key := "64ce7d9730e3f4d704c430a159c9dbc6d4d405d89f1148508e443202b8d653c3", family := 6, baseScore := 19490, ties := [1825200460390365923, 7798173558651306652, 18374575800109165881, 9980076251569551113, 15175454222141752179] }, { key := "6ad7e6e11c5a715041c0d1e037b0d48ae072191e1433ae35c64e780231ecdc50", family := 1, baseScore := 19406, ties := [2288002094929966476, 9353561645136059924, 4702557895750206816, 5690668765208076663, 2663570918416143959] }, { key := "71c947eeb13f0c166058414f7b64faf6798de23a191e36126957cfaae536a0bd", family := 2, baseScore := 19466, ties := [6200852322706347257, 9820514042028955971, 7274442152615381451, 1379982242784742979, 1660428862859231517] }, { key := "74c67d91d381e32057f708cf07cb671d2575c852b66bd54c78ab0172577e888f", family := 1, baseScore := 19441, ties := [8540966648915212792, 13577434514563920436, 12284559500917620523, 8660986038877652935, 6678563798156207960] }, { key := "7936853f064d99b4c87ad0c017a502799a20b398a9948c9a4b71cae0642095e9", family := 5, baseScore := 19473, ties := [1005189969281360074, 15252314669334195950, 1677355114584468213, 14793242972975010867, 1700405426260283322] }, { key := "7cf429d12e04c55acef236646a2b0a8e5a0b3c13371df064c5d8dad2fbf5bb4f", family := 7, baseScore := 19475, ties := [8546551864574073392, 8090086383034992962, 9974530755710984380, 17559250649144876309, 10637278024437988078] }, { key := "7ec7d557c116962ac4a13ef48d12e24f0cb56c5262bae03a84c40d88cbc54d7d", family := 5, baseScore := 19463, ties := [16683943206201673779, 3943913173367315537, 15356282562439470394, 9003023824975183001, 2079802003204519093] }, { key := "836a08670cdfdcb082f55c64677c8eaca60a62d0005749e54e72eb67f94554c0", family := 0, baseScore := 19516, ties := [6430628686343350880, 3326988897348347730, 7288211664416347152, 17061342938759865996, 7836705224492594673] }, { key := "9862ef65bf4a9113a26f1734ad6ec98e0640eb6656cb1a4334972a2f9be1c6ac", family := 4, baseScore := 19502, ties := [8260079361839178878, 8008380571476166928, 7923025157480009945, 18281990603738430032, 10826349845351107097] }, { key := "a342c721f01211e03af69b331f4a012efb6a1efa012a406078278419e9272cc7", family := 5, baseScore := 19510, ties := [4766866663976868429, 3047071987004524432, 9940253806458247809, 4790087559697392821, 14286961818133190237] }, { key := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", family := 6, baseScore := 19451, ties := [11688903147512217911, 13464938556235774340, 2096340461987256118, 7445147631916617319, 8748932342811588969] }, { key := "b1158ed7d34cfcad68c952f03a56102e7cb06b2c773129984a69e603960622d0", family := 2, baseScore := 19466, ties := [703329657200080849, 5361894098738257560, 15006032774167209900, 9873795357456281678, 10248833694836621885] }, { key := "c1f6e3e15772658a58c60b05772015054da09bb91580e62a49b4d0095f59eb66", family := 7, baseScore := 19494, ties := [7208938742527617328, 13755169071181738946, 2637320062845703835, 13818705467271995722, 7444373634666181866] }, { key := "c55761ed74319ddefeb28f554779813e19bb1f9accb4bc85be93b56f01c657e1", family := 3, baseScore := 19427, ties := [8088889808519105341, 936751310522426649, 6016279536750806828, 7984829587334844554, 14105222320240295221] }, { key := "df564cb25de35976dfcbef5e28404498aafd1fce538d0a8aa0e454cf96b11b59", family := 0, baseScore := 19500, ties := [8836220844570832805, 8448612075404267478, 8484827671774169061, 9590386969351737448, 2545991111721416260] }, { key := "e2654af87c885cf417002f13400f5bef1ac23eae87fd7b9fd479aae38f443d21", family := 0, baseScore := 19465, ties := [16012764203337167111, 7852343854022862808, 5709658358219961421, 6664323027437590972, 3243564184122138769] }, { key := "e7579f5e4f38614a40454dca7ae484ae24ab7ffa0d2a03d8ad282fcb7bead25c", family := 6, baseScore := 19462, ties := [13621612582292769046, 2862715562856875574, 10447682337024963304, 17667135270069867225, 15848566133317293010] }, { key := "f2a5dc234b5f195665d205b53e984e94ad894aa5b27e38b9056b9f03862d236b", family := 3, baseScore := 19468, ties := [8099424813576472301, 1776357734177914557, 1403918482063791230, 5144572711022291504, 2485642695817742413] }] }
def selectedProposal : Proposal := { generator := "9cd3e747c0e1a93a02ac5bff1d3a07fa7706172ae4a75a0a373629260a675dc5", parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", contextHash := "6668900a9ec4dadb06e51489ea7a3751b801cab7ff9657a80bb44d74337cf2f6", transcriptHash := "16aee43b8b4f211f15917980d0d573e90a0d642427724271dd32e61ddeae1c0f", choices := [21, 28, 1, 29, 20, 5, 22, 7, 24], verdicts := [false, false, false, false, false, false, false, false, true], program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", candidatePackage := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e" }
def selectedCandidate : CandidateView := { parentPackage := "6759cc828b5b8cb4af041e32dcba7b136849591e793802ab7f1f1cc2f2bcd535", contextHash := "6668900a9ec4dadb06e51489ea7a3751b801cab7ff9657a80bb44d74337cf2f6", program := "a4f37fb8f2f7d3a90829340f2f02b2f19dbc5dfa5caf7a7633e9092837265c0e", package := "b4036b3e31a6608e30b421c08906b1e58c3e7d61fef6eb6730881c597656434e" }

theorem selected_provenance : Produced selectedContext selectedProposal := by
  unfold Produced ContextValid
  decide

theorem selected_candidate_binding :
    CandidateMatches selectedContext selectedProposal selectedCandidate := by
  unfold CandidateMatches
  refine ⟨selected_provenance, ?_, ?_, ?_, ?_⟩ <;> decide

theorem selected_rejection_prefix :
    selectedProposal.verdicts = List.replicate (selectedProposal.choices.length - 1) false ++ [true] := by decide

end Phase17Provenance
#print axioms Phase17Provenance.trace_no_repeat
#print axioms Phase17Provenance.attached_generator_bound
#print axioms Phase17Provenance.attached_package_bound
#print axioms Phase17Provenance.attached_proposal_produced
#print axioms Phase17Provenance.attached_candidate_bound
#print axioms Phase17Provenance.selected_provenance
#print axioms Phase17Provenance.selected_candidate_binding
#print axioms Phase17Provenance.selected_rejection_prefix
