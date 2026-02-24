# 📊 User Flow — CertPrep Multi-Agent System

> Visual flowcharts for all 8 user journeys. Each diagram shows both user actions and the technical events behind them.

---

## Scenario Map

`mermaid
flowchart LR
    Login([🔑 Login Screen])

    Login -->|New learner| S1[S1 — New Learner\nAI-102 from scratch]
    Login -->|Returning user| S2[S2 — Returning Learner\nDP-100 on file]
    Login -->|Azure creds set| S3[S3 — Live Azure\nOpenAI Mode]
    Login -->|Admin login| S4[S4 — Admin\nAudit Dashboard]

    S1 --> S5[S5 — Remediation\nLoop score less than 70%]
    S1 --> S6[S6 — Edit Profile]
    S1 --> S7[S7 — Guardrail BLOCK]
    S1 --> S8[S8 — PII in Background]
`

---

## S1 — New Learner, AI-102 from Scratch

The happy path. Mock mode — no Azure credentials needed. ~5 min end-to-end.

`mermaid
flowchart TD
    A([Open App]) --> B[Click Alex Chen\ndemo card]
    B --> C[Session: logged_in=True\nSQLite upsert_student]
    C --> D[Intake Form\npre-filled via sidebar_prefill]

    D --> G{Guardrails\nG-01 to G-05}
    G -->|BLOCK| ERR1[st.error + st.stop\nUser fixes form]
    G -->|PASS| PROF

    subgraph PROF [Learner Profiling — b1_mock_profiler.py]
        P1[Parse background text\nkeyword rules]
        P2[Assign ExperienceLevel\nBEGINNER]
        P3[Set domain confidence\nall UNKNOWN or WEAK]
        P1 --> P2 --> P3
    end

    PROF --> G2{Guardrails\nG-06 to G-08}
    G2 -->|PASS| FAN

    subgraph FAN [Parallel Fan-Out — ThreadPoolExecutor max_workers=2]
        direction LR
        SP[Thread A\nStudyPlanAgent\nLargest Remainder\nalgorithm]
        LC[Thread B\nLearningPathCurator\nMS Learn module\nmapping + G-17]
    end

    FAN --> DB[(SQLite\nprofile + plan\n+ learning path)]
    DB --> UI

    subgraph UI [6-Tab UI Renders]
        T1[Tab 1 Radar chart\n6 domains]
        T2[Tab 2 Gantt chart\n10 weeks]
        T3[Tab 3 MS Learn\nmodule cards]
        T4[Tab 4 HITL Gate 1\nProgress check-in]
        T5[Tab 5 Mock Quiz\n30 questions]
        T6[Tab 6 Cert\nRecommendation]
    end

    T4 -->|Submit progress| PROG[ProgressAgent\nreadiness formula\n0.55 x confidence\n+0.25 x hours\n+0.20 x practice]
    PROG -->|score 50% or above| T5
    PROG -->|score below 50%| NOTYET[NOT YET banner\nWeak domains highlighted]

    T5 -->|Submit answers| SCORE[Score 30 questions\nweighted by domain]
    SCORE -->|70% or above| T6
    SCORE -->|below 70%| S5([S5 Remediation])

    T6 --> DONE([Ready to book\nNext cert recommendation])
`

---

## S2 — Returning Learner, DP-100

Profile loaded from SQLite — no agent re-runs unless the user edits.

`mermaid
flowchart TD
    A([Login as Priyanka Sharma]) --> B[SQLite read\nlearner_profiles\nstudy_plan\nlearning_path]
    B --> C{Data found?}
    C -->|No| S1([S1 New Learner flow])
    C -->|Yes| D[Restore session state\nis_returning = True]

    D --> E[Show read-only\nProfile Cards x3\nno form, no agent calls]
    E --> F{User action}

    F -->|View tabs| TABS[All 6 tabs render\nfrom session state\nno re-computation]
    F -->|Click Edit| S6([S6 Edit Profile flow])

    TABS --> G{Previous gates completed?}
    G -->|progress_submitted = True| SHOW_PROG[Tab 4 shows\nprevious readiness result]
    G -->|quiz_submitted = True| SHOW_QUIZ[Tab 5 shows score\nTab 6 shows recommendation]
`

---

## S3 — Live Azure OpenAI Mode

One branching point changes everything: use_live toggle in the sidebar.

`mermaid
flowchart TD
    A[Sidebar: Azure OpenAI Config] --> B{Creds filled\nand toggle ON?}
    B -->|No| MOCK[run_mock_profiling\nb1_mock_profiler.py\nrule-based]
    B -->|Yes| LIVE

    subgraph LIVE [LearnerProfilingAgent — b0_intake_agent.py]
        L1[Build system prompt\nwith JSON schema]
        L2[Send RawStudentInput\nto GPT-4o\ntemperature = 0.2]
        L3[Parse JSON response\nLearnerProfile Pydantic]
        L1 --> L2 --> L3
    end

    LIVE -->|Success| MERGE[LearnerProfile]
    LIVE -->|Exception| FB[Fallback to mock\nst.info shown]
    FB --> MERGE
    MOCK --> MERGE

    MERGE --> REST([All downstream agents\nStudyPlan + LearningPath\nProgress + Quiz + Recommendation\nidentical in both modes])
`

---

## S4 — Admin Audit Dashboard

Navigate to /pages/1_Admin_Dashboard.py — credentials: dmin / gents2026.

`mermaid
flowchart LR
    A([Admin login]) --> B[Admin Dashboard]

    B --> R[Student Roster\nSELECT from\nlearner_profiles]
    B --> T[Agent Trace Log\nColour-bordered HTML cards\nper AgentStep]
    B --> G[Guardrail Audit\nRED = BLOCK\nAMBER = WARN]
    B --> M[Mode Badge\nMock or Azure OpenAI]

    T --> T1[Agent name + timestamp\n+ duration_ms]
    T --> T2[input_summary\ntruncated 200 chars]
    T --> T3[output_summary\nkey fields]
    T --> T4[Parallel time in ms]
`

---

## S5 — Remediation Loop (Score < 70%)

Triggered when mock quiz score falls below the pass threshold.

`mermaid
flowchart TD
    Q([Quiz score below 70%]) --> A[CertRecommendationAgent\nremediation branch]

    A --> B[ready_to_book = False\nIdentify weak domains\ne.g. D3 45% and D5 55%]
    B --> C[UI: Not ready banner\nDomain breakdown table\nRemediation plan per domain]

    C --> D{User action}
    D -->|Click Regenerate| E[Reset weak domain\nconfidence to 0.1\npop plan + learning_path]

    E --> F[StudyPlanAgent re-runs\nLargest Remainder\nreallocates more hours\nto weak domains]
    E --> GG[LearningPathCurator re-runs\nSelects hands-on-lab\nvariants for weak domains]

    F --> H[(SQLite overwrite\nversion 2 of plan)]
    GG --> H
    H --> I([All tabs update\nwith new plan])

    D -->|Ignore and reattempt quiz| Q
`

---

## S6 — Edit Profile

`mermaid
flowchart TD
    A([Returning user\nclicks Edit]) --> B[editing_profile = True\nst.rerun]
    B --> C[Intake form shown\npre-populated from stored raw]
    C --> D[User updates fields\ne.g. AI-102 to AZ-204]
    D --> E[Click Save and Regenerate]

    E --> F{Guardrails\nG-01 to G-05}
    F -->|BLOCK| ERR[User fixes field]
    F -->|PASS| G[Full pipeline reruns\nfrom profiling onwards]

    G --> H[New LearnerProfile\nfor AZ-204 domains]
    H --> I[StudyPlan + LearningPath\nregenerated in parallel]
    I --> J[(SQLite overwrite\nnew cert)]
    J --> K[editing_profile cleared\nAll 6 tabs reflect AZ-204]
`

---

## S7 — Guardrail BLOCK Scenarios

`mermaid
flowchart TD
    INPUT([User submits form]) --> G02{G-02\nExam in registry?}
    G02 -->|AZ-999 not found| BLK1[BLOCK\nAZ-999 not in registry\nst.stop]
    G02 -->|Valid| G03

    G03{G-03\nHours in 1 to 80?}
    G03 -->|0 or above 80| BLK2[BLOCK\nHours must be 1 to 80\nst.stop]
    G03 -->|Valid| G16

    G16{G-16\nHarmful keyword\nin text?}
    G16 -->|bomb matched| BLK3[BLOCK\nHarmful content detected\nst.stop]
    G16 -->|Clean| G17

    G17{G-17\nURL trust check\non learning path}
    G17 -->|youtube.com found| WRN[WARN only\nURL removed\nrest of path delivered]
    G17 -->|All learn.microsoft.com| PASS([Pipeline continues])

    WRN --> PASS
`

---

## S8 — PII in Background Text

G-16 runs **before** any profiler agent. PII triggers WARN (pipeline continues). Harmful keywords trigger BLOCK.

`mermaid
flowchart TD
    TXT([background_text submitted]) --> SCAN[G-16 PII scan\nregex patterns]

    SCAN --> SSN{SSN pattern\n123-45-6789?}
    SCAN --> CC{Credit card\n16-digit?}
    SCAN --> EMAIL{Email in bio\nuser at domain?}
    SCAN --> HARM{Harmful keyword\nbomb, harm, etc?}

    SSN -->|Match| W1[WARN banner\nSSN detected\nuser notified]
    CC  -->|Match| W2[WARN banner\nCredit card detected]
    EMAIL -->|Match| W3[WARN banner\nEmail in bio detected]
    HARM -->|Match| BLK[BLOCK\nst.stop\nUser must edit text]

    W1 --> CONT[Pipeline continues\nSSN not forwarded\nto OpenAI in mock mode]
    W2 --> CONT
    W3 --> CONT

    CONT --> LOG[(guardrail_violations\nlogged in SQLite\nvisible in Admin Dashboard)]
`

---

## Pipeline Exit Points

`mermaid
flowchart LR
    subgraph BLOCKS [Pipeline BLOCK — st.stop]
        B1[G-01 to G-05\nInvalid form input]
        B2[G-06 to G-08\nInvalid profiler output]
        B3[G-16 harmful keyword]
    end

    subgraph WARNS [Pipeline WARN — continues]
        W1[G-16 PII\nUser notified, runs on]
        W2[G-09 to G-10\nPlan hours over budget]
        W3[G-17 URL\nBad URL removed]
    end

    subgraph AUTO [Auto-recovery]
        A1[Azure OpenAI error\nsilent fallback to mock]
    end

    BLOCKS --> ERR([Halted — user corrects input])
    WARNS --> CONT([Continues with banner])
    AUTO --> CONT
`
