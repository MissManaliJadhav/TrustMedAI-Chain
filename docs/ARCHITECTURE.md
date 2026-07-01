# MedAI Chatbot Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT BROWSER                          │
│                     (http://localhost:3000)                     │
└──────────────────────────┬──────────────────────────────────────┘
                          │
                    HTTP/HTTPS
                          │
┌─────────────────────────┴──────────────────────────────────────┐
│                    FRONTEND APPLICATION                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ React + TypeScript + Vite                               │ │
│  │                                                          │ │
│  │  ┌─────────────────┐      ┌──────────────────┐         │ │
│  │  │  ChatPage.tsx   │─────→│ ChatWindow.tsx   │         │ │
│  │  │                 │      │                  │         │ │
│  │  │  - Session List │      │  - Messages      │         │ │
│  │  │  - Responsive   │      │  - Input Field   │         │ │
│  │  │  - Mobile Ready │      │  - Assessment    │         │ │
│  │  └─────────────────┘      └──────────────────┘         │ │
│  │           │                        │                   │ │
│  └───────────┼────────────────────────┼───────────────────┘ │
│              │                        │                     │ │
│  ┌───────────┴────────────────────────┴───────────────────┐ │ │
│  │        Redux State Management (chatSlice)             │ │ │
│  │  - Sessions, Messages, Loading, Error States          │ │ │
│  └───────────┬────────────────────────┬───────────────────┘ │ │
│              │                        │                     │ │
│  ┌───────────┴────────────────────────┴───────────────────┐ │ │
│  │         chatAPI Service                               │ │ │
│  │  - Session Management                                 │ │ │
│  │  - Message Sending                                    │ │ │
│  │  - Assessment Retrieval                               │ │ │
│  │  - Export Functionality                               │ │ │
│  └───────────┬─────────────────────────────────────────────┘ │ │
└──────────────┼────────────────────────────────────────────────┘
               │
          RESTful API
          + Auth Token
               │
┌──────────────┴────────────────────────────────────────────────┐
│                   BACKEND APPLICATION                         │
│         (http://localhost:8000/api/v1)                        │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            FastAPI Routes (chatbot.py)              │   │
│  │                                                      │   │
│  │  POST   /chat/sessions                              │   │
│  │  GET    /chat/sessions                              │   │
│  │  GET    /chat/sessions/{id}                         │   │
│  │  POST   /chat/messages                              │   │
│  │  GET    /chat/sessions/{id}/messages                │   │
│  │  GET    /chat/sessions/{id}/assessment              │   │
│  │  POST   /chat/sessions/{id}/export                  │   │
│  │  DELETE /chat/sessions/{id}                         │   │
│  │                                                      │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                             │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │      Chatbot Service Layer (chatbot.py)             │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ Disease Database (15+ conditions)           │   │   │
│  │  │ - Heart Disease, Diabetes, Asthma, etc.    │   │   │
│  │  │ - Symptoms, Risk Factors, Tests            │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ Conversation Engine                         │   │   │
│  │  │ - Profile Collection                        │   │   │
│  │  │ - Chief Complaint → Symptom Exploration     │   │   │
│  │  │ - Medical History → Risk Assessment         │   │   │
│  │  │ - Disease Prediction → Recommendations      │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │ Algorithms                                  │   │   │
│  │  │ - Emergency Detection                       │   │   │
│  │  │ - Natural Language Processing               │   │   │
│  │  │ - Risk Scoring                              │   │   │
│  │  │ - Disease Prediction                        │   │   │
│  │  │ - Recommendation Generation                 │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                             │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ Pydantic Schemas (Request/Response Validation)      │   │
│  │ - PatientProfileData                                │   │
│  │ - SymptomData                                       │   │
│  │ - RiskAssessmentData                                │   │
│  │ - ChatMessageRequest/Response                       │   │
│  │ - ChatAssessmentResponse                            │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                             │
└─────────────────┼─────────────────────────────────────────────┘
                  │
              Database Access
                  │
┌─────────────────┴─────────────────────────────────────────────┐
│                    DATABASE LAYER                             │
│              (PostgreSQL via SQLAlchemy ORM)                  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ChatSession Table                                    │   │
│  │ ├─ id (UUID)                                         │   │
│  │ ├─ user_id (Foreign Key)                             │   │
│  │ ├─ title                                             │   │
│  │ ├─ status                                            │   │
│  │ ├─ patient_profile (JSON)                            │   │
│  │ ├─ medical_history (JSON)                            │   │
│  │ ├─ symptoms_data (JSON)                              │   │
│  │ ├─ risk_assessment (JSON)                            │   │
│  │ ├─ possible_conditions (JSON)                        │   │
│  │ ├─ recommendations (JSON)                            │   │
│  │ ├─ conversation_stage                                │   │
│  │ ├─ created_at                                        │   │
│  │ └─ updated_at                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ChatMessage Table                                    │   │
│  │ ├─ id (UUID)                                         │   │
│  │ ├─ session_id (Foreign Key)                          │   │
│  │ ├─ role (user/assistant)                             │   │
│  │ ├─ content (Text)                                    │   │
│  │ ├─ message_type                                      │   │
│  │ ├─ metadata (JSON)                                   │   │
│  │ └─ created_at                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
User Input
    │
    ↓
┌─────────────────────────┐
│   React Component       │
│   (ChatWindow.tsx)      │
└────────┬────────────────┘
         │
         ↓ Redux Dispatch
┌─────────────────────────┐
│   Redux Store           │
│   (chatSlice)           │
└────────┬────────────────┘
         │
         ↓ API Call (chatAPI.ts)
┌─────────────────────────┐
│   HTTP Request          │
│   (POST /chat/messages) │
└────────┬────────────────┘
         │
         ↓ Received @ Backend
┌─────────────────────────┐
│   FastAPI Endpoint      │
│   (chatbot.py routes)   │
└────────┬────────────────┘
         │
         ↓ Save User Message
┌─────────────────────────┐
│   Database              │
│   (ChatMessage)         │
└────────┬────────────────┘
         │
         ↓ Chatbot Processing
┌─────────────────────────┐
│   Service Layer         │
│   (chatbot.py service)  │
│   - NLP                 │
│   - Risk Assessment     │
│   - Disease Prediction  │
│   - Recommendations     │
└────────┬────────────────┘
         │
         ↓ Generate Response
┌─────────────────────────┐
│   Assistant Message     │
└────────┬────────────────┘
         │
         ↓ Save Assistant Message
┌─────────────────────────┐
│   Database              │
│   (ChatMessage)         │
└────────┬────────────────┘
         │
         ↓ HTTP Response
┌─────────────────────────┐
│   JSON Response         │
│   (user_msg, asst_msg)  │
└────────┬────────────────┘
         │
         ↓ Received @ Frontend
┌─────────────────────────┐
│   Redux Store           │
│   (Dispatch Message)    │
└────────┬────────────────┘
         │
         ↓ Update UI
┌─────────────────────────┐
│   Chat Messages         │
│   Auto-scroll           │
│   Assessment Display    │
└────────┬────────────────┘
         │
         ↓
User Sees Response
```

---

## Conversation Stage Flow

```
START
  │
  ├─→ [PROFILE_COLLECTION]
  │   ├─ Ask: Name, Age, Gender, Height, Weight
  │   ├─ Extract: Using NLP
  │   └─→ Next: chief_complaint
  │
  ├─→ [CHIEF_COMPLAINT]
  │   ├─ Ask: "What is your main health concern?"
  │   ├─ Store: Primary symptom
  │   └─→ Next: symptom_exploration
  │
  ├─→ [SYMPTOM_EXPLORATION]
  │   ├─ Collect: Duration, Severity, Associated Symptoms
  │   ├─ Calculate: Confidence Score
  │   ├─ Decision: Confidence >= 70%?
  │   │   ├─ Yes: Continue
  │   │   └─ No: Ask more questions
  │   └─→ Next: medical_history
  │
  ├─→ [MEDICAL_HISTORY]
  │   ├─ Collect: Diseases, Surgeries, Allergies, Medications
  │   ├─ Store: Complete history
  │   └─→ Next: risk_assessment
  │
  ├─→ [RISK_ASSESSMENT]
  │   ├─ Calculate: Age Risk
  │   ├─ Calculate: Lifestyle Risk
  │   ├─ Calculate: Family History Risk
  │   ├─ Calculate: Chronic Disease Risk
  │   ├─ Generate: Overall Risk Score
  │   └─→ Next: disease_prediction
  │
  ├─→ [DISEASE_PREDICTION]
  │   ├─ Analyze: Symptoms vs Disease Database
  │   ├─ Calculate: Probability for each condition
  │   ├─ Rank: By probability (top 5)
  │   ├─ Assess: Confidence levels
  │   └─→ Next: recommendations
  │
  ├─→ [RECOMMENDATIONS]
  │   ├─ Generate: Immediate Actions
  │   ├─ Generate: Lifestyle Recommendations
  │   ├─ Generate: Diet Suggestions
  │   ├─ Generate: Specialist Recommendations
  │   ├─ Generate: Diagnostic Tests
  │   └─→ Next: completed
  │
  └─→ [COMPLETED]
      ├─ Display: Complete Assessment
      ├─ Show: Export Options
      └─ Allow: Download/Export

END
```

---

## Component Hierarchy

```
App
├── Router
│   ├── LandingPage
│   ├── LoginPage
│   ├── SignupPage
│   ├── DashboardPage
│   │   ├── Header
│   │   └── [MedAI Chat Button] → /chat
│   │
│   └── ChatPage (Protected)
│       ├── Sidebar (Desktop)
│       │   ├── Session List
│       │   │   └── ListItem (Session)
│       │   └── New Chat Button
│       │
│       ├── Drawer (Mobile)
│       │   └── Session List
│       │
│       └── Main Content
│           └── ChatWindow
│               ├── Messages Container
│               │   ├── Message (User)
│               │   ├── Message (Assistant)
│               │   └── Spinner (Loading)
│               │
│               ├── Assessment Card
│               │   ├── Risk Level
│               │   ├── Conditions
│               │   ├── Recommendations
│               │   └── Export Button
│               │
│               └── Message Input
│                   ├── TextField
│                   ├── Send Button
│                   └── Delete Button
```

---

## API Endpoint Mapping

```
PUBLIC ENDPOINTS (No Auth)
  GET  /health

AUTHENTICATED ENDPOINTS (Requires JWT Token)

Chat Session Management:
  POST   /chat/sessions
         Body: {title: string}
         Returns: ChatSessionResponse
  
  GET    /chat/sessions
         Returns: List[ChatSessionResponse]
  
  GET    /chat/sessions/{session_id}
         Returns: ChatSessionResponse
  
  DELETE /chat/sessions/{session_id}
         Returns: {status, message}

Chat Messages:
  POST   /chat/messages
         Body: ChatMessageRequest
         Returns: {user_message, assistant_message}
  
  GET    /chat/sessions/{session_id}/messages
         Returns: List[ChatMessageResponse]

Assessment:
  GET    /chat/sessions/{session_id}/assessment
         Returns: ChatAssessmentResponse
  
  POST   /chat/sessions/{session_id}/export
         Body: {disease_key: string}
         Returns: {diagnosis_id, status, message}
```

---

## Technology Stack

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **State Management**: Redux Toolkit
- **Styling**: Tailwind CSS + Material UI
- **HTTP Client**: Axios
- **Routing**: React Router DOM

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Authentication**: JWT
- **Validation**: Pydantic
- **Server**: Uvicorn

### Database
- **Primary**: PostgreSQL
- **ORM**: SQLAlchemy (Python)
- **Migrations**: Handled by SQLAlchemy

### Deployment
- **Containerization**: Docker
- **Orchestration**: Docker Compose / Kubernetes
- **CI/CD**: GitHub Actions

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION                           │
│                  (JWT Token-based)                          │
└──────────┬──────────────────────────┬──────────────────────┘
           │                          │
    ┌──────┴────┐             ┌──────┴────┐
    │  Frontend │             │ Backend   │
    │  (Token)  │             │ (Verify)  │
    └──────┬────┘             └──────┬────┘
           │                         │
           └─────────────────────────┘
              Authorization Header

┌─────────────────────────────────────────────────────────────┐
│              AUTHORIZATION (RBAC)                           │
│            (Role-Based Access Control)                      │
│  - PATIENT: Can only access own sessions                    │
│  - DOCTOR: Can access patient sessions for review           │
│  - ADMIN: Full access                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                DATA SECURITY                                │
│  - HTTPS/TLS in production                                  │
│  - SQL Injection Prevention (ORM)                           │
│  - XSS Prevention (React escaping)                          │
│  - Input Validation (Pydantic)                              │
│  - No sensitive data in logs                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              MEDICAL SAFETY                                 │
│  - Emergency Detection & Escalation                         │
│  - Medical Disclaimers                                      │
│  - No Diagnosis Claims                                      │
│  - Professional Consultation Encouraged                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ↓              ↓              ↓
    ┌────────┐   ┌────────┐   ┌────────────┐
    │Frontend│   │Backend │   │ Database   │
    │Docker  │   │Docker  │   │PostgreSQL  │
    │Port    │   │Port    │   │Port        │
    │3000    │   │8000    │   │5432        │
    └────────┘   └────────┘   └────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
            Docker Compose / K8s
                Orchestration
```

---

This architecture provides a scalable, secure, and maintainable healthcare chatbot system integrated into the TrustMedAI-Chain platform.
