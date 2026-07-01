# MedAI Chatbot Integration Documentation

## Overview

MedAI is an advanced Healthcare AI Assistant integrated into the TrustMedAI-Chain platform. It provides intelligent healthcare information, symptom analysis, risk assessment, and personalized recommendations while maintaining strict safety protocols.

## Features

### Core Functionality

1. **Patient Intake Workflow**
   - Systematic collection of patient information
   - Medical history tracking
   - Symptom analysis and classification
   - Risk stratification

2. **Emergency Detection**
   - Real-time detection of emergency keywords
   - Immediate alerts for critical symptoms
   - Emergency escalation procedures

3. **Symptom Analysis**
   - Detailed symptom collection
   - Duration and severity assessment
   - Associated symptoms identification
   - Trigger and relief factor analysis

4. **Risk Assessment**
   - Age-based risk calculation
   - Lifestyle risk analysis
   - Family history risk evaluation
   - Chronic disease risk assessment
   - Overall risk score generation

5. **Disease Prediction**
   - Analysis of 15+ medical conditions
   - Probability scoring
   - Confidence level assessment
   - Supporting symptom identification
   - Missing information detection

6. **Recommendation Engine**
   - Immediate action recommendations
   - Lifestyle modifications
   - Diet suggestions
   - Exercise recommendations
   - Specialist referrals
   - Diagnostic test suggestions

### Supported Conditions

**Cardiology:**
- Heart Disease
- Hypertension
- Arrhythmia
- Heart Failure

**Endocrinology:**
- Type 1 Diabetes
- Type 2 Diabetes
- Prediabetes

**Neurology:**
- Parkinson's Disease
- Alzheimer's Disease
- Stroke Risk

**Respiratory:**
- Asthma
- COPD
- Pneumonia
- COVID-19

**Infectious Diseases:**
- Tuberculosis
- Pneumonia
- Influenza

**Other:**
- Liver Disease
- Kidney Disease
- Various other conditions

## Technical Architecture

### Backend Components

#### Database Models (SQLAlchemy ORM)
- **ChatSession**: Stores conversation sessions
  - Session metadata
  - Patient profile data
  - Medical history
  - Symptoms data
  - Risk assessment
  - Possible conditions
  - Recommendations
  - Conversation stage tracking

- **ChatMessage**: Stores individual messages
  - Message role (user/assistant)
  - Message content
  - Message type (text, structured_data, assessment, etc.)
  - Metadata and additional context
  - Timestamps

#### Schemas (Pydantic)
- `PatientProfileData`: Basic patient information
- `MedicalHistoryData`: Medical background
- `SymptomData`: Symptom details
- `RiskAssessmentData`: Risk scores
- `PossibleCondition`: Disease prediction
- `RecommendationData`: Health recommendations
- `ChatMessageRequest/Response`: Message handling
- `ChatSessionResponse`: Session info
- `ChatAssessmentResponse`: Complete assessment output

#### Services
- **chatbot.py**: Core chatbot logic
  - Disease database and knowledge base
  - Emergency detection
  - Patient information extraction
  - Symptom confidence scoring
  - Risk level assessment
  - Disease prediction algorithm
  - Recommendation generation
  - Session management

#### API Endpoints

```
POST /api/v1/chat/sessions
- Create new chat session
- Parameters: title (optional)
- Returns: ChatSessionResponse

GET /api/v1/chat/sessions
- List all user sessions
- Returns: List[ChatSessionResponse]

GET /api/v1/chat/sessions/{session_id}
- Get specific session details
- Returns: ChatSessionResponse

POST /api/v1/chat/messages
- Send message and get response
- Body: ChatMessageRequest
- Returns: {user_message, assistant_message}

GET /api/v1/chat/sessions/{session_id}/messages
- Get chat history
- Returns: List[ChatMessageResponse]

GET /api/v1/chat/sessions/{session_id}/assessment
- Get assessment summary
- Returns: ChatAssessmentResponse

POST /api/v1/chat/sessions/{session_id}/export
- Export session as diagnosis record
- Parameters: disease_key (optional)
- Returns: Export confirmation

DELETE /api/v1/chat/sessions/{session_id}
- Delete chat session
- Returns: Success status
```

### Frontend Components

#### Redux Store
- **chatSlice.ts**: State management for chat
  - Sessions list
  - Current session ID
  - Messages
  - Loading states
  - Error handling
  - Composition state

#### API Service
- **chatAPI.ts**: API client for all chatbot endpoints
  - Session management
  - Message sending
  - Assessment retrieval
  - Session export

#### Components
- **ChatWindow.tsx**: Main chat interface
  - Message display and input
  - Assessment visualization
  - Export functionality
  - Delete session
  - Auto-scroll

- **ChatPage.tsx**: Chat page layout
  - Session sidebar
  - Mobile-responsive design
  - Session creation
  - Session selection
  - Loading states

#### Pages
- **ChatPage.tsx**: Full-page chat interface
  - Responsive layout
  - Session management UI
  - Chat window integration

#### Routes
- `/chat`: Main chat interface (protected)
  - Requires authentication
  - Accessible to all authenticated users

## Conversation Workflow

### Stage 1: Profile Collection
- Collect: Name, Age, Gender, Height, Weight, Blood Group, Country, Occupation
- Extracts information from natural language
- Validates and stores in session

### Stage 2: Chief Complaint
- Ask: "What is your main health concern?"
- Store primary symptom
- Move to symptom exploration

### Stage 3: Symptom Exploration
- Collect: Duration, Severity (1-10), Additional Symptoms, Triggers, Relief Factors
- Calculate symptom confidence score
- Proceed when confidence >= 70%

### Stage 4: Medical History
- Collect: Existing Diseases, Surgeries, Allergies, Medications, Family History
- Store medical background
- Prepare for risk assessment

### Stage 5: Risk Assessment
- Calculate: Age Risk, Lifestyle Risk, Family History Risk, Chronic Disease Risk
- Generate overall risk score
- Feed into prediction algorithm

### Stage 6: Disease Prediction
- Analyze symptoms against disease database
- Calculate probability for each condition
- Generate confidence levels
- Identify missing information

### Stage 7: Recommendations
- Generate immediate actions
- Provide lifestyle modifications
- Suggest monitoring advice
- Recommend diagnostic tests
- Suggest specialist consultations

### Stage 8: Completion
- Display comprehensive assessment
- Allow export as diagnosis record
- Provide follow-up options

## Safety and Compliance

### Emergency Detection
Automatically detects and escalates:
- Chest pain
- Difficulty breathing
- Severe bleeding
- Stroke symptoms
- Loss of consciousness
- Seizures
- Suicidal thoughts
- Severe allergic reactions

### Disclaimers
- Never claims definitive diagnoses
- Always indicates this is informational only
- Encourages consultation with healthcare professionals
- Includes medical disclaimers in all outputs

### Data Privacy
- Session data stored in database
- Encrypted communication with backend
- User authentication required
- RBAC (Role-Based Access Control) enforced

## Database Schema

### ChatSession Table
```sql
CREATE TABLE chat_sessions (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) FOREIGN KEY,
  title VARCHAR(255),
  status VARCHAR(50),
  patient_profile JSON,
  medical_history JSON,
  symptoms_data JSON,
  risk_assessment JSON,
  possible_conditions JSON,
  recommendations JSON,
  conversation_stage VARCHAR(50),
  created_at DATETIME,
  updated_at DATETIME
);
```

### ChatMessage Table
```sql
CREATE TABLE chat_messages (
  id VARCHAR(36) PRIMARY KEY,
  session_id VARCHAR(36) FOREIGN KEY,
  role VARCHAR(20),
  content TEXT,
  message_type VARCHAR(50),
  metadata JSON,
  created_at DATETIME
);
```

## Integration Points

### With Existing Services
1. **Prediction Service**: Can export chat assessments as diagnosis records
2. **Blockchain Service**: Hash records when exporting assessments
3. **Trust Service**: Incorporate trust scores in recommendations
4. **XAI Service**: Provide explanations for predictions

### With Frontend Dashboard
1. Button in dashboard header navigates to chat
2. Authenticated users can access chat anytime
3. Chat history preserved across sessions
4. Assessments exportable to diagnosis system

## Deployment

### Docker Support
The chatbot service runs within the existing backend container. No additional containers needed.

### Environment Variables
No additional environment variables required. Uses existing database connection.

### Database Migration
New tables (chat_sessions, chat_messages) created on startup via SQLAlchemy.

## Usage Examples

### Starting a Chat
```typescript
const session = await chatAPI.createSession('New Health Assessment');
dispatch(addSession(session));
```

### Sending a Message
```typescript
const response = await chatAPI.sendMessage(sessionId, 'I have been experiencing chest pain');
```

### Getting Assessment
```typescript
const assessment = await chatAPI.getAssessment(sessionId);
```

### Exporting Assessment
```typescript
const result = await chatAPI.exportSession(sessionId, 'heart_disease');
```

## Testing

### Manual Testing Checklist
- [ ] Create new chat session
- [ ] Send text messages
- [ ] Verify emergency detection
- [ ] Test assessment generation
- [ ] Export assessment to diagnosis record
- [ ] Delete chat session
- [ ] List chat sessions
- [ ] Test on mobile responsiveness
- [ ] Verify authentication requirement
- [ ] Test error handling

### Test Scenarios
1. **Happy Path**: Normal conversation through all stages
2. **Emergency**: Trigger emergency detection
3. **Partial Info**: Incomplete symptom information
4. **Export**: Export assessment as diagnosis
5. **Error Cases**: Network errors, invalid inputs

## Performance Considerations

- Messages stored in database for persistence
- Pagination support for history (limit parameter)
- Async operations for API calls
- Redux state management for UI performance
- Lazy loading of sessions

## Future Enhancements

1. **LangChain Integration**: Full conversational memory with LangChain
2. **Multi-language Support**: Support for multiple languages
3. **Voice Input**: Voice-to-text for accessibility
4. **Advanced NLP**: Better entity extraction and intent recognition
5. **Integration with Real Models**: Use actual ML models for prediction
6. **Telehealth Integration**: Direct doctor consultation booking
7. **Analytics Dashboard**: Track chatbot usage and effectiveness
8. **ML-based Response Generation**: Use transformers for more natural responses

## Troubleshooting

### Common Issues

**Issue**: Chat messages not appearing
- Check database connection
- Verify user authentication
- Check browser console for errors

**Issue**: Emergency detection not working
- Verify emergency keywords in message
- Check case sensitivity
- Review detect_emergency() function

**Issue**: Assessment not generating
- Verify conversation stage progression
- Check symptom confidence score
- Review prediction algorithm

**Issue**: Export failing
- Verify session data completeness
- Check database permissions
- Review diagnosis record creation

## Support and Maintenance

- Monitor database size of chat tables
- Periodically archive old sessions
- Update disease database as needed
- Review and update emergency keywords
- Monitor error logs for issues

---

For more information, refer to the main project README.md or contact the development team.
