# MedAI Chatbot - Implementation & Testing Guide

## Quick Start Guide

### Step 1: Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`

### Step 2: Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Step 3: Access the Chatbot

1. Go to `http://localhost:3000`
2. Sign up or log in
3. Click "MedAI Chat" button in the dashboard
4. Start a new chat session
5. Begin the health assessment

---

## Feature Walkthrough

### 1. Creating a Chat Session

**Endpoint**: `POST /api/v1/chat/sessions`

```bash
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "New Health Assessment"}'
```

**Response**:
```json
{
  "id": "session-uuid",
  "title": "New Health Assessment",
  "status": "active",
  "conversation_stage": "profile_collection",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

### 2. Sending Messages

**Endpoint**: `POST /api/v1/chat/messages`

```bash
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid",
    "content": "I am John, 45 years old, male from USA, working as an engineer",
    "message_type": "text"
  }'
```

**Response**:
```json
{
  "user_message": {
    "id": "msg-uuid-1",
    "session_id": "session-uuid",
    "role": "user",
    "content": "I am John, 45 years old, male from USA, working as an engineer",
    "message_type": "text",
    "metadata": {},
    "created_at": "2024-01-15T10:01:00"
  },
  "assistant_message": {
    "id": "msg-uuid-2",
    "session_id": "session-uuid",
    "role": "assistant",
    "content": "Thank you for sharing that information. I've noted: {...}...",
    "message_type": "text",
    "metadata": {"symptom_confidence": 45},
    "created_at": "2024-01-15T10:01:05"
  }
}
```

### 3. Conversation Flow

**Stage 1: Profile Collection**
```
User: "I am John, 45 years old, male, weighing 80kg, 180cm tall"
Assistant: "Thank you for sharing that information. I've noted...
Now, what is your main health concern today?"
```

**Stage 2: Chief Complaint**
```
User: "I've been having chest pain for 3 days"
Assistant: [Emergency alert if detected]
"I understand you're experiencing: chest pain...
To better understand your condition:
1. When did this start?
2. How severe is it on a scale of 1-10?
3. Are there any other symptoms?"
```

**Stage 3: Symptom Exploration**
```
User: "It's severe, 8/10, started 3 days ago after exercise"
Assistant: "Thank you for those details. I have a good understanding...
Now, let's discuss your medical background..."
```

**Stage 4: Medical History**
```
User: "I have diabetes and hypertension, no allergies"
Assistant: "Thank you for that information.
Now let me perform a comprehensive assessment..."
```

**Stage 5-7: Assessment**
```
Assistant: "**ASSESSMENT SUMMARY**
**Risk Level:** HIGH
**Possible Conditions:**
1. Heart Disease (Confidence: HIGH)
2. Acute Coronary Syndrome (Confidence: MODERATE)
..."
```

### 4. Emergency Detection

The chatbot automatically detects emergency keywords:
- "chest pain"
- "difficulty breathing"
- "severe bleeding"
- "loss of consciousness"
- "seizures"
- "suicidal"
- "severe allergic"

**Example**:
```
User: "I can't breathe, chest pain, dizzy"
Assistant: "🚨 **MEDICAL EMERGENCY ALERT** 🚨
Your symptoms may indicate a medical emergency. 
Please contact emergency services immediately or visit the nearest emergency department. 
Call 911 or your local emergency number.
Do not delay. Seek immediate medical attention."
```

### 5. Getting Assessment Summary

**Endpoint**: `GET /api/v1/chat/sessions/{session_id}/assessment`

```bash
curl -X GET http://localhost:8000/api/v1/chat/sessions/session-uuid/assessment \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "session_id": "session-uuid",
  "patient_summary": {
    "name": "John",
    "age": 45,
    "gender": "Male",
    "height": "180cm",
    "weight": "80kg"
  },
  "symptoms_summary": {
    "primary_symptom": "chest pain",
    "duration": "3 days",
    "severity": 8,
    "additional_symptoms": ["dizziness", "shortness of breath"]
  },
  "risk_assessment": {
    "overall_risk_score": "HIGH",
    "age_risk": "MODERATE",
    "lifestyle_risk": "MODERATE"
  },
  "possible_conditions": [
    {
      "condition": "Heart Disease",
      "probability": 85.5,
      "confidence_level": "HIGH",
      "supporting_symptoms": ["chest pain", "shortness of breath"],
      "missing_information": ["ECG results"]
    }
  ],
  "recommendations": {
    "immediate_actions": ["Schedule urgent appointment", "Monitor symptoms"],
    "diagnostic_tests": ["ECG", "Troponin Test"],
    "specialist_recommendation": "Consult a Cardiologist"
  }
}
```

### 6. Exporting Assessment

**Endpoint**: `POST /api/v1/chat/sessions/{session_id}/export`

```bash
curl -X POST http://localhost:8000/api/v1/chat/sessions/session-uuid/export \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"disease_key": "heart_disease"}'
```

**Response**:
```json
{
  "diagnosis_id": "diag-uuid",
  "status": "created",
  "message": "Chat assessment has been converted to diagnosis record...",
  "next_steps": [
    "A doctor will review your assessment",
    "You will receive feedback within 24-48 hours",
    "Additional tests may be recommended"
  ]
}
```

---

## Testing Scenarios

### Scenario 1: Normal Conversation (Happy Path)

**Objective**: Complete full health assessment

**Steps**:
1. Create new session
2. Send profile info: "My name is Sarah, I'm 35 years old, female, 65kg"
3. Send chief complaint: "I've been feeling very tired lately"
4. Send symptom details: "For about 2 weeks, it's affecting my daily work"
5. Send medical history: "I have no major illnesses, no allergies"
6. View assessment
7. Export as diagnosis

**Expected Result**: Assessment generated with possible conditions and recommendations

---

### Scenario 2: Emergency Detection

**Objective**: Test emergency keyword detection

**Steps**:
1. Create new session
2. Send message: "I have severe chest pain and difficulty breathing"

**Expected Result**: 
- Immediate emergency alert displayed
- Message: "🚨 **MEDICAL EMERGENCY ALERT** 🚨"
- Session marked as completed
- No further messages accepted

---

### Scenario 3: Incomplete Information

**Objective**: Test confidence scoring and additional questions

**Steps**:
1. Create new session
2. Send vague profile: "I'm 40"
3. Send vague symptom: "I don't feel well"
4. Observe assistant asking clarifying questions
5. Provide more details incrementally

**Expected Result**: 
- Chatbot asks for more specific information
- Confidence score increases with each detail
- Assessment generation when confidence >= 70%

---

### Scenario 4: Multiple Conditions Detection

**Objective**: Test disease prediction accuracy

**Steps**:
1. Create new session
2. Send profile: "I'm 60 years old, male, smoker"
3. Send symptoms: "Chest pain, shortness of breath, fatigue"
4. Send medical history: "I have diabetes and hypertension"

**Expected Result**:
- Multiple conditions suggested (Heart Disease, Diabetes complications, etc.)
- Probabilities calculated based on age, lifestyle, family history
- Highest probability conditions ranked first

---

### Scenario 5: Export to Diagnosis System

**Objective**: Test integration with diagnosis system

**Steps**:
1. Complete full assessment
2. Click "Export Assessment" button
3. Confirm export

**Expected Result**:
- Diagnosis record created in system
- Record stored in database
- Alert shown with diagnosis ID
- Record available in dashboard diagnosis list

---

## Manual Testing Checklist

### Backend Tests
- [ ] Database tables created (chat_sessions, chat_messages)
- [ ] API endpoints responding correctly
- [ ] Authentication working on all endpoints
- [ ] Session data persisted in database
- [ ] Messages stored correctly
- [ ] Assessment data saved
- [ ] Export creates diagnosis record

### Frontend Tests
- [ ] Chat page loads
- [ ] Can create new session
- [ ] Messages display correctly (user right, assistant left)
- [ ] Message input works
- [ ] Send button disabled during loading
- [ ] Assessment card displays
- [ ] Export button works
- [ ] Delete session works
- [ ] Session list shows all sessions
- [ ] Mobile responsiveness works

### Functional Tests
- [ ] Profile collection extracts information
- [ ] Emergency keywords detected
- [ ] Symptom confidence calculated
- [ ] Risk assessment generated
- [ ] Disease prediction working
- [ ] Recommendations generated
- [ ] Proper conversation stage progression
- [ ] Medical disclaimers displayed

### Integration Tests
- [ ] Backend and frontend communicate
- [ ] Authentication token passed correctly
- [ ] CORS headers configured
- [ ] Errors handled gracefully
- [ ] Loading states displayed
- [ ] Error messages shown to user

---

## Debugging

### Common Issues and Solutions

**Issue**: Chat sessions not saving
```
Check:
1. Database connection: `SELECT * FROM chat_sessions;`
2. User authentication: Verify token is valid
3. API logs: Check for errors in backend
4. Frontend console: Look for JavaScript errors
```

**Issue**: Messages appearing twice
```
Check:
1. Redux dispatch - verify no duplicate dispatches
2. API response - check for duplicate messages
3. Browser cache - clear and reload
```

**Issue**: Emergency detection not working
```
Check:
1. Message contains keyword exactly
2. Case sensitivity - keywords are lowercase
3. detect_emergency() function logic
4. Test with: "chest pain", "difficulty breathing"
```

**Issue**: Assessment not generating
```
Check:
1. Conversation stage progression
2. Required data collected:
   - Patient profile (at least name/age)
   - Chief complaint
   - Symptoms
   - Medical history
3. Symptom confidence score >= 70%
4. Database has disease data
```

---

## Performance Monitoring

### Key Metrics to Track

1. **Response Time**
   - Average message response time: < 1 second
   - Session creation time: < 500ms
   - Assessment generation: < 2 seconds

2. **Error Rate**
   - Target: < 1% error rate
   - Monitor 404s, 500s, validation errors

3. **Database**
   - Monitor chat_sessions table size
   - Monitor chat_messages table size
   - Archive old sessions after 90 days

4. **API Usage**
   - Track calls to /chat/messages
   - Track session creation rates
   - Monitor export usage

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] SSL certificates installed
- [ ] CORS whitelist updated
- [ ] API rate limiting configured
- [ ] Logging configured
- [ ] Error monitoring setup
- [ ] Backups configured
- [ ] Load testing completed
- [ ] Security audit completed

### Deployment Steps

```bash
# 1. Update backend
docker build -t trustmedai-backend:latest backend/

# 2. Update frontend
docker build -t trustmedai-frontend:latest frontend/

# 3. Deploy with Docker Compose
docker-compose -f docker-compose.yml up -d

# 4. Or deploy with Kubernetes
kubectl apply -f k8s/
```

---

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Support

For issues or questions:
1. Check CHATBOT_DOCUMENTATION.md
2. Review error logs
3. Check database for data integrity
4. Contact development team

---

Last Updated: 2024-01-15
Version: 1.0.0
