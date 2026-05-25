Docs/design/wom Knowledge Continuity Layer
WOM Knowledge Continuity Layer
1. Purpose

この設計メモは、WOM: Weekly Operation Model における Knowledge Continuity Layer の目的・構造・運用方法を定義する。

WOM Knowledge Continuity Layer は、WOM のコード、モデル定義、設計判断、検証結果、未解決論点を継続的に保持し、人間と AI が共同で WOM を理解・利用・拡張できるようにするための知識継続レイヤーである。

WOM の本体が経済活動の PSI、すなわち Production / Purchase、Ship / Sales、Inventory を扱うのに対して、Knowledge Continuity Layer は WOM 自身の成長に必要な 知識の PSI を扱う。

P: Produce Knowledge
新しい仮説、設計案、検討結果、実装アイデアを生成する。
S: Supply Knowledge
次の会話、設計作業、実装作業、テスト作業へ必要な知識を供給する。
I: Inventory Knowledge
検証済み事実、設計原則、意思決定ログ、ビジネスルール、テスト結果を保持する。

このレイヤーの目的は、単に過去の chatlog を保存することではない。過去の検討内容を、次の設計判断・実装判断・検証判断に再利用できる形で保持することである。

2. Background

WOM は、グローバル・サプライチェーンの週次オペレーションを、PSI 数量編・金額編・能力制約・コスト構造・シナリオ比較として表現する計画シミュレータである。

WOM の開発では、長期間にわたり以下のような重要な知識が蓄積されている。

Lot を主語にする設計思想
Demand Anchored Lot / MEO: Minimum Economic Object の概念
Node / Flow / PSI list / Capacity / Costing / Scenario の定義
with Capacity PSI Planning Engine の実装方針
Forward PUSH / Backward PULL / Capacity aware allocation の整理
Costing Model / Price Simulation / 2 phase costing の位置づけ
Event Flow Tracing / Management Cockpit / Scenario Planning の構想
WOM を Custom GAI と連携させるための seed prompt / knowledge continuity の構想

これらの知識が開発者個人の記憶や散在する chatlog の中だけに留まると、将来の AI 支援開発や第三者による拡張が困難になる。

したがって、WOM には、コードと同じくらい重要な知識管理構造が必要である。

3. Definition

WOM Knowledge Continuity Layer とは、WOM の計画モデル、設計判断、実装ルール、検証結果を継続的に保持・更新し、人間と AI が共同で WOM を理解・利用・拡張できるようにする知識継続レイヤーである。

これは、単なる FAQ、操作マニュアル、README、または chatlog summary ではない。

Knowledge Continuity Layer は、以下を明示的に管理する。

WOM の正規定義
採用済みの設計判断
検証済み事実
実装済み仕様
未検証仮説
未解決論点
廃止・変更された考え方
次回作業を開始するための入口
対応するコード、テスト、runner、CSV、docs への接続
4. Positioning in WOM Architecture

WOM は、以下の三層を持つべきである。

WOM Code Layer
  Planning Engine / GUI / Tests / Runners / CSV / SQL / Reports


WOM Model Definition Layer
  Lot / MEO / Node / Flow / PSI / Capacity / Costing / Scenario


WOM Knowledge Continuity Layer
  Canonical Definition / Decision Log / Facts & Findings /
  Business Rules / Hypothesis Register / Open Issues / Test Anchor

WOM Code Layer は「動くもの」である。

WOM Model Definition Layer は「何をモデル化しているか」を定義する。

WOM Knowledge Continuity Layer は「なぜその設計になったか」「何が決定済みか」「どこから再開すべきか」を保持する。

この三層が揃うことで、WOM は GitHub 上の Python プロジェクトから、AI と人間が継続的に読み、理解し、改良できる成長型の計画モデルへ進化する。

5. Design Principles
5.1 Knowledge is not only memory

継続学習とは、すべてを記憶することではない。

WOM に必要なのは、検証状態付きの知識台帳である。

知識は、次のように分類されるべきである。

Type	Meaning	Example
fact	検証済み事実	pytest の成功結果、runner の実行結果
finding	分析・検証から得られた発見	LOT_SIZE 依存性の挙動
decision	採用済み設計判断	Lot を WOM の主語とする
rule	実装・業務上のルール	capacity 超過時は blocked lot として扱う
hypothesis	未検証仮説	Knowledge PSI の拡張モデル
issue	未解決論点	Backward capacity allocation の優先順位
deprecated	廃止・置換された考え方	古い CSV-only 前提の仕様
prompt	次回作業の入口	Codex request / next session prompt
5.2 Do not mix facts and hypotheses

WOM の知識管理では、fact と hypothesis を混同してはならない。

AI は、未検証の仮説をもっともらしい事実として表現してしまう危険がある。そのため、各 knowledge item には必ず検証状態を持たせる。

5.3 Every important decision should have an anchor

重要な設計判断は、以下のいずれかに接続されるべきである。

ソースコード
テストコード
runner
CSV / SQL schema
design doc
chatlog summary
issue / pull request
実行ログ

これを Test Anchor / Code Anchor / Doc Anchor と呼ぶ。

5.4 Knowledge should have lifecycle

知識は固定的なメモではなく、ライフサイクルを持つ。

Raw Chat
  -> Candidate Knowledge
  -> Hypothesis
  -> Finding
  -> Decision / Rule / Validated Fact
  -> Canonical Knowledge
  -> Deprecated / Revised / Contradicted

このライフサイクルにより、WOM は単に過去を保存するだけでなく、知識を更新し、必要に応じて廃止できる。

5.5 Natural growth requires immune system

WOM が AI と人間の共同作業で自然増殖的に成長するためには、免疫系が必要である。

免疫系とは、WOM の設計思想を壊さずに拡張するための品質保証構造である。

具体的には、以下を指す。

Canonical Definition
Decision Log
Fact / Hypothesis / Decision の分離
Test Anchor
Deprecation Rule
Contribution Protocol

これにより、WOM は野生化するのではなく、進化できる。

6. Knowledge Layers

WOM Knowledge Continuity Layer は、以下の階層構造を持つ。

Global Canonical Knowledge
  数学、科学、経済、管理会計、サプライチェーン一般知識


Domain Knowledge
  Supply Chain Planning、PSI、S&OP、TOC、管理会計、物流、製造業知識


WOM Project Knowledge
  WOM 固有の設計原則、モデル定義、実装ルール、検証結果


Session Working Knowledge
  現在の会話で発生した仮説、メモ、設計案、修正案

WOM の repo 内で主に管理する対象は、WOM Project Knowledge と Session Working Knowledge である。

7. Core Knowledge Categories
7.1 Canonical Definition

WOM 内で正規定義として扱う概念を管理する。

対象例:

WOM: Weekly Operation Model
PSI: Production / Purchase, Ship / Sales, Inventory
Lot
MEO: Minimum Economic Object
Demand Anchored Lot
Node
Flow / Edge
Supply Point
Capacity
Buffer Stock
Cost Profile
Price Simulation
Scenario
Event Trace
Management Fact

Canonical Definition は、他の文書や AI 応答が参照すべき上位定義である。

7.2 Decision Log

採用済みの設計判断を管理する。

例:

id: DEC-2026-05-23-001
title: Define WOM Knowledge Continuity Layer as explicit architecture
status: adopted
decision: >
  WOM will maintain a Knowledge Continuity Layer to preserve design principles,
  validated facts, business rules, open issues, and next-entry prompts.
rationale: >
  WOM development depends on long-term accumulated knowledge. Chatlogs alone
  are insufficient for AI-assisted continuation and third-party extension.
impact:
  - Enables Custom GAI style support
  - Reduces context reconstruction cost
  - Supports AI/human collaborative development
anchors:
  docs:
    - docs/design/wom_knowledge_continuity_layer.md
7.3 Facts & Findings

検証済みの実行結果、観察結果、検証から得た発見を管理する。

例:

id: FACT-2026-05-10-001
type: fact
claim: Forward PUSH with Capacity planner test passed with 4 tests.
evidence:
  - command: python -m pytest tests/test_forward_push_with_capacity_planner.py
  - result: 4 passed
confidence: high
scope: with-capacity forward push planner
status: validated
7.4 Business Rules

WOM の planning engine や costing model に反映すべき業務・モデル・実装ルールを管理する。

例:

id: RULE-CAP-001
title: Capacity constrained accepted and blocked lots
rule: >
  When requested lots exceed available capacity, accepted lots are allocated
  up to capacity and excess lots are recorded as blocked lots.
status: adopted
related_modules:
  - pysi/planning/forward_push_with_capacity_planner.py
related_tests:
  - tests/test_forward_push_with_capacity_planner.py
7.5 Hypothesis Register

未検証だが重要な仮説を管理する。

例:

id: HYP-2026-05-23-001
title: WOM can grow naturally through AI-assisted knowledge PSI
hypothesis: >
  If WOM maintains explicit canonical definitions, decisions, facts, rules,
  open issues, and test anchors, AI and humans can extend WOM continuously
  with less dependency on the original developer.
status: candidate
validation_method:
  - Create initial Knowledge Continuity docs
  - Use them in future AI-assisted development sessions
  - Compare context reconstruction time and design consistency
7.6 Open Issues

未解決論点、保留理由、次の検討入口を管理する。

例:

id: ISSUE-CAP-BWD-001
title: Backward capacity-aware demand allocation rule
status: open
question: >
  How should demand lots be prioritized when backward allocation faces
  limited upstream capacity?
next_entry_prompt: >
  Start from docs/design/backward_capacity_aware_demand_allocation.md
  and define priority rules for accepted, delayed, and blocked lots.
7.7 Test Anchor

重要な知識と実装検証を接続する。

対象:

pytest
smoke runner
sample CSV
output report
GUI operation scenario
before / after snapshot
cost waterfall output

例:

id: TEST-CAP-FWD-001
title: Forward push with capacity planner pytest
command: python -m pytest tests/test_forward_push_with_capacity_planner.py
expected_result: all tests pass
validates:
  - RULE-CAP-001
  - DEC-CAP-FWD-001
8. Proposed Repository Layout

初期段階では、Markdown 中心の軽量運用で開始する。

docs/
  design/
    wom_knowledge_continuity_layer.md
    wom_canonical_definitions.md
    wom_decision_log.md
    wom_facts_and_findings.md
    wom_business_rules.md
    wom_hypothesis_register.md
    wom_open_issues.md
    wom_test_anchors.md
    wom_next_entry_prompts.md

将来的には、以下のように YAML / JSON / SQLite / PostgreSQL へ移行可能である。

knowledge/
  canonical_definitions/
  decisions/
  facts/
  findings/
  rules/
  hypotheses/
  issues/
  test_anchors/
  prompts/

MVP では、まず docs/design/ 配下に Markdown を置くことで十分である。

9. Knowledge Item Schema

将来的な構造化管理を見据え、各 knowledge item は以下の項目を持つことを推奨する。

id: string
title: string
type: fact | finding | hypothesis | decision | rule | issue | prompt | deprecated
claim: string
status: candidate | adopted | validated | rejected | deprecated | revised
confidence: low | medium | high
source:
  type: chatlog | code | test | doc | issue | pr | user_input | execution_log
  reference: string
evidence:
  - string
scope:
  - string
valid_from: YYYY-MM-DD
valid_until: YYYY-MM-DD | null
owner: string
review_status: unreviewed | reviewed | approved
related_items:
  - id
contradictions:
  - id
anchors:
  docs:
    - path
  code:
    - path
  tests:
    - path
  runners:
    - path
  data:
    - path
last_updated: YYYY-MM-DD
next_action: string

Markdown 運用では、これを表形式または YAML fenced block として記録する。

10. Operating Workflow
10.1 Session Start Protocol

AI との新しい検討セッションを開始するときは、以下を確認する。

今回のテーマ
関連する canonical definition
関連する decision log
関連する facts & findings
関連する business rules
未解決論点
前回定義された next entry prompt
今回の成果物候補

例:

今回のテーマは with Capacity PUSH Forward Planning の blocked lot handling です。
関連資料として以下を参照してください。


- docs/design/wom_canonical_definitions.md
- docs/design/wom_business_rules.md
- docs/design/wom_test_anchors.md


今回のゴールは、blocked_lot_ids の型処理を安全化し、既存テストを壊さない最小 patch を作成することです。
10.2 Session End Protocol

セッション終了時には、以下を保存する。

何を検討したか
何を決定したか
何が検証済みか
何が未検証か
どのコード・テスト・docs に接続したか
次回どこから再開するか

例:

Session Summary:
- Forward PUSH with Capacity planner の blocked lot handling を確認した。
- blocked_lots が dict と string の両方を取り得るため、_lot_id helper を導入する方針とした。


Decision:
- blocked_lot_ids 生成時は _lot_id(lot) を経由する。


Facts:
- 既存 pytest は 4 passed。


Open Issue:
- Backward capacity-aware allocation の優先順位ルールは未定義。


Next Entry Prompt:
- backward_capacity_aware_demand_allocation.md を起点に、accepted / delayed / blocked lot の定義を整理する。
11. WOM Custom GAI Role Definition

WOM Custom GAI は、単なる WOM 操作説明チャットボットではない。

WOM Custom GAI は、以下の役割を持つ。

Role	Description
WOM Navigator	ユーザーを適切な docs / code / scenario / test へ案内する
WOM Design Reviewer	設計案が WOM の canonical definition と矛盾しないか確認する
WOM Code Extension Advisor	既存コード構造に沿って最小 patch / skeleton / Codex request を作る
WOM Scenario Modeling Partner	業務シナリオを WOM の Node / Flow / Lot / PSI / Capacity へ変換する
WOM Knowledge Archivist	検討結果を Decision / Fact / Rule / Issue として整理する
WOM Decision Log Keeper	採用済み判断とその根拠を保持する
WOM Test / Validation Guide	実装変更に対応する pytest / runner / smoke test を提案する

この役割定義により、WOM Custom GAI は、WOM の利用・機能拡張・教育・検証を支援する常駐型の知識パートナーとなる。

12. Contribution Protocol

AI または人間が WOM を拡張する場合、以下の作法を守る。

12.1 Before change
変更対象の canonical definition を確認する。
既存 decision log と矛盾しないか確認する。
関連する business rule を確認する。
既存 tests / runners を確認する。
12.2 During change
変更範囲を最小化する。
既存思想を壊さない。
新しい概念を導入する場合は、canonical definition 候補として記録する。
実装判断を decision log 候補として記録する。
12.3 After change
実行結果を facts & findings に記録する。
新しい rule が生まれた場合は business rules に追加する。
未解決点を open issues に残す。
次回作業の入口を next entry prompt として記録する。
13. Minimum Viable Implementation

初期実装では、以下の 5 ファイルを整備すればよい。

docs/design/wom_knowledge_continuity_layer.md
docs/design/wom_canonical_definitions.md
docs/design/wom_decision_log.md
docs/design/wom_facts_and_findings.md
docs/design/wom_open_issues.md

次の段階で、以下を追加する。

docs/design/wom_business_rules.md
docs/design/wom_hypothesis_register.md
docs/design/wom_test_anchors.md
docs/design/wom_next_entry_prompts.md

さらに将来的には、以下へ拡張する。

Markdown から YAML / JSON への構造化
SQLite / PostgreSQL による knowledge item 管理
RAG index の作成
Custom GPT / Custom GAI seed prompt との連携
GitHub issue / PR / test result との接続
GUI 上の WOM Navigator への統合
14. Initial Knowledge Items
14.1 Canonical Direction
id: CANON-WOM-KCL-001
type: canonical_definition
title: WOM Knowledge Continuity Layer
definition: >
  A knowledge continuity layer that preserves WOM design principles,
  model definitions, implementation rules, validation results, and open issues
  so that humans and AIs can continuously understand, use, and extend WOM.
status: adopted
14.2 Initial Decision
id: DEC-WOM-KCL-001
type: decision
title: Manage WOM growth through explicit knowledge continuity
decision: >
  WOM will maintain explicit knowledge artifacts such as canonical definitions,
  decision logs, facts and findings, business rules, hypothesis registers,
  open issues, test anchors, and next-entry prompts.
status: adopted
rationale: >
  WOM depends on long-running accumulated design knowledge. Without explicit
  continuity, AI-assisted development may lose context, confuse hypotheses
  with facts, or diverge from the original model philosophy.
14.3 Initial Hypothesis
id: HYP-WOM-KCL-001
type: hypothesis
title: WOM can naturally grow through AI-assisted knowledge PSI
hypothesis: >
  If WOM maintains explicit knowledge PSI, then future users and AIs can create
  new WOM scenarios, extend functionality, and preserve design consistency
  without relying solely on the original developer's memory.
status: candidate
validation_method: >
  Use this layer in future development sessions and observe whether context
  reconstruction time decreases and design consistency improves.
14.4 Initial Open Issue
id: ISSUE-WOM-KCL-001
type: issue
title: Decide storage format for structured knowledge items
status: open
question: >
  Should WOM knowledge items remain as Markdown sections, or should they be
  migrated to YAML / JSON / SQLite for better retrieval and validation?
initial_direction: >
  Start with Markdown in docs/design. Move to YAML or SQLite only after the
  categories stabilize.
15. Risks and Controls
Risk	Description	Control
Knowledge bloat	すべてを保存しすぎて読めなくなる	保存対象を decision / fact / rule / issue に絞る
False certainty	仮説を事実として扱う	type / status / confidence を必須化する
Design drift	AI や人間が勝手に WOM 思想を変更する	canonical definition と decision log を参照する
Broken traceability	docs と code / tests が接続しない	anchor を記録する
Outdated knowledge	古い仕様が残り続ける	deprecated / revised status を使う
Over-engineering	初期から DB 化しすぎる	まず Markdown MVP で開始する
16. Next Actions
docs/design/wom_canonical_definitions.md を作成する。
docs/design/wom_decision_log.md を作成する。
docs/design/wom_facts_and_findings.md を作成する。
docs/design/wom_open_issues.md を作成する。
直近の with Capacity PSI Engine の検討内容を initial knowledge items として登録する。
次回以降の AI セッション開始時に、この Knowledge Continuity Layer を参照する運用を試す。
17. Summary

WOM Knowledge Continuity Layer は、WOM を継続学習型の知的プラットフォームへ進化させるための基盤である。

WOM の成長には、コードだけでなく、設計判断、検証済み事実、業務ルール、未解決論点、次回作業の入口が必要である。

このレイヤーが整備されることで、WOM は開発者個人の記憶に依存する段階から、人間と AI が共同で継続的に学習・利用・拡張できる段階へ移行できる。

WOM 本体が経済活動の PSI を扱うように、WOM Knowledge Continuity Layer は WOM 自身の知識 PSI を扱う。

この意味で、WOM は自分自身の成長プロセスをモデル化するための、内蔵された知識サプライチェーンを持つことになる。