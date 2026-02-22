# CertPrep AI — Multi-Agent Architecture

> Microsoft Agents League 2026 · Battle #2: Reasoning Agents

```mermaid
flowchart TD
    S(["🎓 Student\n(Browser Form)"])

    subgraph INPUT["📥 Block 0 — Input Layer"]
        S -->|"raw form data"| IA["LearnerIntakeAgent\n(intake_agent.py)"]
    end

    subgraph BLOCK1["🧠 Block 1 — Intake & Profiling"]
        IA -->|"RawStudentInput"| G_IN{{"🛡️ Guardrails\nG-01 to G-05"}}
        G_IN -->|"✅ pass"| PA["LearnerProfilingAgent\n(Mock / Azure OpenAI)"]
        G_IN -->|"🚫 BLOCK"| ERR1[/"Error Banner\nUI stops"/]
        PA -->|"LearnerProfile"| G_PF{{"🛡️ Guardrails\nG-06 to G-08"}}
    end

    subgraph BLOCK11["📚 Block 1.1 — Learning Path & Study Plan"]
        G_PF -->|"✅"| LPC["LearningPathCuratorAgent\n30+ MS Learn modules"]
        G_PF -->|"✅"| SPA["StudyPlanAgent\nLargest Remainder Method"]
        LPC -->|"LearningPath"| G_LP{{"🛡️ G-17\nURL trust check"}}
        SPA -->|"StudyPlan + Gantt"| G_SP{{"🛡️ G-09, G-10\nweek bounds, hours"}}
    end

    subgraph BLOCK12["📈 Block 1.2 — Progress Tracking"]
        G_SP --> PRA["ProgressAgent\nReadiness Formula:\n0.55×domain + 0.25×hours + 0.20×practice"]
        G_SP --> G_SN{{"🛡️ G-11 to G-13\nhours≥0, rating[1-5], score[0-100]"}}
        G_SN -->|"ProgressSnapshot"| PRA
        PRA -->|"ReadinessAssessment"| ENG["📧 Engagement Agent\nHTML email + nudges"]
    end

    subgraph BLOCK2["🧪 Block 2 — Knowledge Assessment (HITL)"]
        PRA -->|"readiness data"| HITL{"👤 Human Gate:\nLearner clicks\n'Generate Quiz'"}
        HITL -->|"Yes"| ASA["AssessmentAgent\n30-Q bank, domain-weighted\nLargest Remainder sampling"]
        ASA -->|"AssessmentResult"| G_AS{{"🛡️ G-14, G-15\n≥5 Qs, no duplicates"}}
    end

    subgraph BLOCK3["🏅 Block 3 — Certification Decision"]
        G_AS -->|"✅"| PASS{"Quiz Score ≥ 70%?"}
        PASS -->|"✅ YES"| CRA["CertificationRecommendationAgent\nGO + exam logistics\n+ next-cert path"]
        PASS -->|"❌ NO"| LOOP["Remediation Plan\n← loops back to Block 1.1"]
        LOOP --> LPC
    end

    subgraph OUTPUT["📤 Output Layer"]
        CRA --> UI["🖥️ Streamlit UI\n7 Tabs — GO/NO-GO card\nexam booking checklist"]
        ENG --> EMAIL["📨 SMTP Email\nWeekly summary report"]
        G_LP --> UI
        G_SP --> UI
    end

    %% Styles
    classDef agent    fill:#5C2D91,color:#fff,stroke:#3b1e6e,rx:6
    classDef guard    fill:#DC2626,color:#fff,stroke:#991b1b,rx:4
    classDef decision fill:#D97706,color:#fff,stroke:#92400e
    classDef output   fill:#059669,color:#fff,stroke:#047857,rx:4
    classDef error    fill:#FEE2E2,color:#991b1b,stroke:#DC2626
    classDef hitl     fill:#0F6CBD,color:#fff,stroke:#0a4a8a

    class IA,PA,LPC,SPA,PRA,ENG,ASA,CRA agent
    class G_IN,G_PF,G_LP,G_SP,G_SN,G_AS guard
    class PASS,LOOP decision
    class UI,EMAIL output
    class ERR1 error
    class HITL hitl
    class S hitl
```

---

## Agent Summary

| Block | Agent | Input | Output |
|-------|-------|-------|--------|
| 0 | **LearnerIntakeAgent** | UI form | `RawStudentInput` |
| 1 | **LearnerProfilingAgent** | `RawStudentInput` | `LearnerProfile` |
| 1.1 | **LearningPathCuratorAgent** | `LearnerProfile` | `LearningPath` |
| 1.1 | **StudyPlanAgent** | `LearnerProfile` | `StudyPlan` + Gantt |
| 1.2 | **ProgressAgent** | `ProgressSnapshot` | `ReadinessAssessment` |
| 1.2 | **Engagement Agent** | `ReadinessAssessment` | HTML email |
| 2 | **AssessmentAgent** | `LearnerProfile` | `Assessment` + `AssessmentResult` |
| 3 | **CertificationRecommendationAgent** | `AssessmentResult` | `CertRecommendation` |

## Guardrails Overview

| Rules | Category | Level |
|-------|----------|-------|
| G-01 to G-05 | Input validation | BLOCK / WARN / INFO |
| G-06 to G-08 | Profile integrity | BLOCK / WARN |
| G-09 to G-10 | Study plan bounds | BLOCK / WARN |
| G-11 to G-13 | Progress data validity | BLOCK |
| G-14 to G-15 | Quiz integrity | WARN / BLOCK |
| G-16 to G-17 | Content safety & URL trust | BLOCK / WARN |
