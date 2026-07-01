"""
MedAI Chatbot Service - Healthcare AI Assistant

This module provides the chatbot service for TrustMedAI-Chain, including:
- Patient intake workflow
- Emergency detection
- Symptom analysis
- Risk assessment
- Disease prediction
- Recommendation engine
- LangChain integration for conversation memory
"""

import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession, DiagnosisRecord
from app.schemas import (
    ChatAssessmentResponse,
    MedicalHistoryData,
    PatientProfileData,
    PossibleCondition,
    RecommendationData,
    RiskAssessmentData,
    SymptomData,
)
from app.services.prediction import make_prediction


# Medical Knowledge Base
DISEASE_DATABASE = {
    "heart_disease": {
        "key_symptoms": ["chest pain", "shortness of breath", "fatigue", "dizziness", "nausea"],
        "risk_factors": ["hypertension", "diabetes", "smoking", "obesity", "family history"],
        "diagnostic_tests": ["ECG", "Echocardiogram", "Stress Test", "Coronary Angiography"],
        "specialist": "Cardiologist",
        "emergency_symptoms": ["severe chest pain", "difficulty breathing", "loss of consciousness"],
    },
    "diabetes": {
        "key_symptoms": ["increased thirst", "frequent urination", "fatigue", "blurred vision", "slow healing"],
        "risk_factors": ["obesity", "family history", "age", "sedentary lifestyle", "poor diet"],
        "diagnostic_tests": ["Fasting Blood Sugar", "HbA1c Test", "Oral Glucose Tolerance Test"],
        "specialist": "Endocrinologist",
        "emergency_symptoms": ["severe hyperglycemia", "diabetic ketoacidosis", "hypoglycemic shock"],
    },
    "asthma": {
        "key_symptoms": ["wheezing", "shortness of breath", "chest tightness", "coughing", "difficulty breathing"],
        "risk_factors": ["family history", "allergies", "air pollution", "smoking", "childhood infections"],
        "diagnostic_tests": ["Spirometry", "Peak Flow Test", "Chest X-ray"],
        "specialist": "Pulmonologist",
        "emergency_symptoms": ["severe breathlessness", "inability to speak", "blue lips"],
    },
    "pneumonia": {
        "key_symptoms": ["cough", "fever", "chest pain", "shortness of breath", "fatigue"],
        "risk_factors": ["smoking", "age", "weak immune system", "recent flu", "chronic disease"],
        "diagnostic_tests": ["Chest X-ray", "Blood Tests", "Sputum Culture"],
        "specialist": "Pulmonologist",
        "emergency_symptoms": ["severe breathing difficulty", "sepsis signs", "confusion"],
    },
    "tuberculosis": {
        "key_symptoms": ["persistent cough", "chest pain", "fever", "night sweats", "weight loss"],
        "risk_factors": ["close contact", "HIV", "malnutrition", "smoking", "crowded living"],
        "diagnostic_tests": ["TB Skin Test", "Chest X-ray", "Sputum Test", "TB Blood Test"],
        "specialist": "Pulmonologist/Infectious Disease",
        "emergency_symptoms": ["hemoptysis", "severe respiratory distress"],
    },
    "liver_disease": {
        "key_symptoms": ["jaundice", "abdominal pain", "fatigue", "dark urine", "pale stool"],
        "risk_factors": ["alcohol abuse", "viral hepatitis", "obesity", "family history", "blood transfusions"],
        "diagnostic_tests": ["Liver Function Tests", "Ultrasound", "Liver Biopsy", "CT Scan"],
        "specialist": "Hepatologist",
        "emergency_symptoms": ["severe bleeding", "hepatic encephalopathy", "acute liver failure"],
    },
    "kidney_disease": {
        "key_symptoms": ["decreased urination", "swelling", "fatigue", "chest pain", "nausea"],
        "risk_factors": ["diabetes", "hypertension", "obesity", "family history", "age"],
        "diagnostic_tests": ["Creatinine Test", "BUN Test", "Urine Analysis", "Kidney Ultrasound"],
        "specialist": "Nephrologist",
        "emergency_symptoms": ["acute kidney failure", "severe hyperkalemia", "pulmonary edema"],
    },
    "parkinson_disease": {
        "key_symptoms": ["tremor", "rigidity", "bradykinesia", "postural instability", "sleep problems"],
        "risk_factors": ["age", "family history", "pesticide exposure", "head injury"],
        "diagnostic_tests": ["Clinical Exam", "MRI", "PET Scan", "DAT Scan"],
        "specialist": "Neurologist",
        "emergency_symptoms": ["severe motor dysfunction", "medication complications"],
    },
    "stroke": {
        "key_symptoms": ["sudden numbness", "sudden weakness", "speech difficulty", "vision loss", "dizziness"],
        "risk_factors": ["hypertension", "diabetes", "smoking", "atrial fibrillation", "age"],
        "diagnostic_tests": ["CT Scan", "MRI", "Carotid Ultrasound", "Angiography"],
        "specialist": "Neurologist",
        "emergency_symptoms": ["sudden severe headache", "loss of consciousness", "facial drooping"],
    },
}

EMERGENCY_KEYWORDS = [
    "chest pain",
    "difficulty breathing",
    "severe bleeding",
    "loss of consciousness",
    "seizures",
    "suicidal",
    "severe allergic",
    "can't breathe",
    "severe headache",
    "facial drooping",
    "slurred speech",
    "weakness on one side",
    "sudden vision loss",
]

CONVERSATION_STAGES = {
    "profile_collection": {
        "next": "chief_complaint",
        "questions": [
            "I'm MedAI, your healthcare assistant. To help you better, could you please share your basic information?",
            "What is your full name?",
        ],
    },
    "chief_complaint": {
        "next": "symptom_exploration",
        "questions": [
            "What is your main health concern today?",
            "For example: fever, chest pain, breathing problems, skin issues, etc.",
        ],
    },
    "symptom_exploration": {
        "next": "medical_history",
        "questions": [
            "Let me understand your symptoms better.",
            "When did this symptom start?",
            "How severe is it on a scale of 1-10?",
        ],
    },
    "medical_history": {
        "next": "risk_assessment",
        "questions": [
            "Now let's discuss your medical background.",
            "Do you have any existing health conditions?",
            "Are you allergic to any medications?",
        ],
    },
    "risk_assessment": {
        "next": "assessment",
        "questions": [
            "Let me assess your risk level based on the information provided.",
        ],
    },
    "assessment": {
        "next": "recommendations",
        "questions": [
            "Based on our conversation, here's my assessment:",
        ],
    },
    "recommendations": {
        "next": "follow_up",
        "questions": [
            "Here are my recommendations:",
        ],
    },
    "follow_up": {
        "next": "completed",
        "questions": [
            "Do you have any other concerns or questions?",
        ],
    },
    "completed": {
        "next": None,
        "questions": [
            "Thank you for using MedAI. Please consult a healthcare professional for personalized medical advice.",
        ],
    },
}


def detect_emergency(message: str) -> bool:
    """Detect if message contains emergency symptoms."""
    message_lower = message.lower()
    for keyword in EMERGENCY_KEYWORDS:
        if keyword in message_lower:
            return True
    return False


def extract_patient_info(message: str) -> dict[str, Any]:
    """Extract patient information from message."""
    info = {}

    # Try to extract age
    age_match = re.search(r"(?:i'm|i am|age|years old|year old)\s+(\d+)", message, re.IGNORECASE)
    if age_match:
        info["age"] = int(age_match.group(1))

    # Try to extract name (simple extraction)
    name_patterns = [
        r"(?:my name is|i'm|i am)\s+([A-Za-z\s]+?)(?:\.|,|$)",
    ]
    for pattern in name_patterns:
        name_match = re.search(pattern, message, re.IGNORECASE)
        if name_match:
            info["name"] = name_match.group(1).strip()

    # Try to extract gender
    if re.search(r"\b(?:male|man|boy)\b", message, re.IGNORECASE):
        info["gender"] = "Male"
    elif re.search(r"\b(?:female|woman|girl)\b", message, re.IGNORECASE):
        info["gender"] = "Female"

    return info


def calculate_symptom_confidence(symptoms: list[str]) -> float:
    """Calculate confidence score based on symptom description completeness."""
    if not symptoms:
        return 0.0

    # Assess based on number of symptoms and detail level
    base_score = min(len(symptoms) * 25, 60)

    # Bonus for specific details
    for symptom in symptoms:
        if len(symptom) > 20:  # More detailed symptoms
            base_score += 10

    return min(base_score, 100.0)


def assess_risk_level(patient_data: dict[str, Any]) -> dict[str, str]:
    """Assess risk level based on patient data."""
    risk_scores = {
        "age_risk": "LOW",
        "lifestyle_risk": "LOW",
        "family_history_risk": "LOW",
        "chronic_disease_risk": "LOW",
        "overall_risk_score": "LOW",
        "emergency_risk": "LOW",
    }

    # Age-based risk
    age = patient_data.get("age", 0)
    if age > 65:
        risk_scores["age_risk"] = "HIGH"
    elif age > 50:
        risk_scores["age_risk"] = "MODERATE"

    # Lifestyle risk
    smoking = patient_data.get("smoking_status", "").lower()
    if "yes" in smoking or "regular" in smoking:
        risk_scores["lifestyle_risk"] = "HIGH"
    elif "occasional" in smoking:
        risk_scores["lifestyle_risk"] = "MODERATE"

    # Medical history risk
    medical_history = patient_data.get("existing_diseases", [])
    if medical_history:
        risk_scores["chronic_disease_risk"] = "HIGH" if len(medical_history) > 1 else "MODERATE"

    # Family history risk
    family_history = patient_data.get("family_history", [])
    if family_history:
        risk_scores["family_history_risk"] = "MODERATE" if len(family_history) == 1 else "HIGH"

    # Calculate overall risk
    risk_values = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
    overall_score = sum(risk_values.get(risk_scores[key], 1) for key in risk_scores if key != "overall_risk_score") / 5

    if overall_score >= 2.5:
        risk_scores["overall_risk_score"] = "HIGH"
    elif overall_score >= 1.5:
        risk_scores["overall_risk_score"] = "MODERATE"
    else:
        risk_scores["overall_risk_score"] = "LOW"

    return risk_scores


def predict_conditions(symptoms: list[str], medical_history: list[str], patient_age: int = 30) -> list[PossibleCondition]:
    """Predict possible conditions based on symptoms."""
    possible_conditions = []

    for disease_key, disease_data in DISEASE_DATABASE.items():
        matching_symptoms = [s for s in symptoms if any(key in s.lower() for key in disease_data["key_symptoms"])]

        if matching_symptoms:
            # Calculate probability based on matching symptoms
            probability = min((len(matching_symptoms) / len(disease_data["key_symptoms"])) * 100, 100.0)

            # Adjust based on age
            if disease_key == "stroke" and patient_age > 50:
                probability += 10
            elif disease_key == "asthma" and patient_age < 40:
                probability += 5

            # Adjust based on family history
            if any("family" in h.lower() or disease_key.replace("_", " ") in h.lower() for h in medical_history):
                probability += 15

            missing_info = [q for q in disease_data["key_symptoms"] if q not in [s.lower() for s in symptoms]][:3]

            condition = PossibleCondition(
                condition=disease_key.replace("_", " ").title(),
                probability=min(probability, 100.0),
                confidence_level="HIGH" if probability > 70 else "MODERATE" if probability > 40 else "LOW",
                supporting_symptoms=matching_symptoms[:3],
                missing_information=missing_info,
            )
            possible_conditions.append(condition)

    # Sort by probability
    possible_conditions.sort(key=lambda x: x.probability, reverse=True)

    return possible_conditions[:5]  # Return top 5


def generate_recommendations(
    symptoms: list[str],
    risk_assessment: dict[str, str],
    possible_conditions: list[PossibleCondition],
) -> RecommendationData:
    """Generate health recommendations based on assessment."""
    recommendations = RecommendationData()

    # Immediate actions
    if risk_assessment.get("overall_risk_score") == "HIGH":
        recommendations.immediate_actions = [
            "Schedule an urgent appointment with your healthcare provider",
            "Monitor your symptoms closely",
            "Keep emergency contact information handy",
        ]
    else:
        recommendations.immediate_actions = [
            "Schedule a regular check-up with your doctor",
            "Keep track of your symptoms",
        ]

    # Monitoring advice
    recommendations.monitoring_advice = [
        "Keep a symptom diary noting frequency and severity",
        "Monitor vital signs (blood pressure, temperature, etc.)",
        "Track any triggers that worsen your symptoms",
    ]

    # Lifestyle advice
    recommendations.lifestyle_advice = [
        "Maintain regular sleep schedule (7-9 hours daily)",
        "Manage stress through meditation or relaxation techniques",
        "Avoid smoking and limit alcohol consumption",
        "Stay hydrated and maintain good hygiene",
    ]

    # Diet suggestions
    recommendations.diet_suggestions = [
        "Eat a balanced diet with fruits and vegetables",
        "Reduce processed food intake",
        "Control salt and sugar consumption",
        "Stay hydrated with adequate water intake",
    ]

    # Exercise suggestions
    recommendations.exercise_suggestions = [
        "Start with light exercises (30 minutes daily if possible)",
        "Avoid strenuous activities until evaluated by a doctor",
        "Gentle stretching and walking are beneficial",
    ]

    # Specialist recommendation
    if possible_conditions:
        disease_key = possible_conditions[0].condition.lower().replace(" ", "_")
        if disease_key in DISEASE_DATABASE:
            recommendations.specialist_recommendation = (
                f"Consult a {DISEASE_DATABASE[disease_key]['specialist']} for evaluation"
            )

    # Diagnostic tests
    if possible_conditions:
        disease_key = possible_conditions[0].condition.lower().replace(" ", "_")
        if disease_key in DISEASE_DATABASE:
            recommendations.diagnostic_tests = DISEASE_DATABASE[disease_key]["diagnostic_tests"]

    return recommendations


def create_chat_session(db: Session, user_id: str | None = None, title: str = "New Chat") -> ChatSession:
    """Create a new chat session."""
    session = ChatSession(user_id=user_id, title=title, conversation_stage="profile_collection")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def save_chat_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: dict[str, Any] | None = None,
) -> ChatMessage:
    """Save a chat message."""
    if metadata is None:
        metadata = {}

    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        message_type=message_type,
        metadata_json=metadata,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    message.metadata = message.metadata_json
    return message


def get_chat_history(db: Session, session_id: str, limit: int = 50) -> list[ChatMessage]:
    """Get chat history for a session."""
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).limit(limit).all()


def generate_response(db: Session, session_id: str, user_message: str) -> tuple[str, dict[str, Any]]:
    """
    Generate chatbot response based on user message.
    Returns: (response_text, metadata)
    """
    # Get session
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        return "Session not found", {}

    # Check for emergency
    if detect_emergency(user_message):
        emergency_response = (
            "🚨 **MEDICAL EMERGENCY ALERT** 🚨\n\n"
            "Your symptoms may indicate a medical emergency. "
            "Please contact emergency services immediately or visit the nearest emergency department. "
            "Call 911 or your local emergency number.\n\n"
            "Do not delay. Seek immediate medical attention."
        )
        save_chat_message(db, session_id, "assistant", emergency_response, "alert")
        session.status = "completed"
        db.commit()
        return emergency_response, {"emergency": True}

    # Extract information from message
    extracted_info = extract_patient_info(user_message)
    stage = session.conversation_stage

    # Update session data based on stage
    response_text = ""
    metadata = {}

    if stage == "profile_collection":
        # Collect patient profile
        patient_profile = session.patient_profile or {}
        patient_profile.update(extracted_info)
        session.patient_profile = patient_profile

        response_text = (
            f"Thank you for sharing that information. I've noted: {json.dumps(extracted_info)}.\n\n"
            f"Now, what is your main health concern today? Please describe what brought you here."
        )
        session.conversation_stage = "chief_complaint"

    elif stage == "chief_complaint":
        # Collect chief complaint/symptoms
        symptoms = session.symptoms_data or {}
        symptoms["primary_symptom"] = user_message
        session.symptoms_data = symptoms

        response_text = (
            f"I understand you're experiencing: {user_message}\n\n"
            f"To better understand your condition:\n"
            f"1. When did this start?\n"
            f"2. How severe is it on a scale of 1-10?\n"
            f"3. Are there any other symptoms you've noticed?"
        )
        session.conversation_stage = "symptom_exploration"

    elif stage == "symptom_exploration":
        # Collect detailed symptoms
        symptoms = session.symptoms_data or {}
        symptoms["additional_symptoms"] = [user_message]
        
        # Calculate confidence
        all_symptoms = [symptoms.get("primary_symptom", "")] + [user_message]
        confidence = calculate_symptom_confidence(all_symptoms)
        metadata["symptom_confidence"] = confidence

        session.symptoms_data = symptoms

        if confidence >= 70:
            response_text = (
                f"Thank you for those details. I have a good understanding of your symptoms.\n\n"
                f"Now, let's discuss your medical background:\n"
                f"1. Do you have any existing health conditions?\n"
                f"2. Are you taking any medications?\n"
                f"3. Any allergies to medications?"
            )
            session.conversation_stage = "medical_history"
        else:
            response_text = (
                f"I want to make sure I understand completely. Could you provide more details about:\n"
                f"- When exactly did this start?\n"
                f"- What makes it worse or better?\n"
                f"- Any associated symptoms?"
            )

    elif stage == "medical_history":
        # Collect medical history
        medical_history = session.medical_history or {}
        medical_history["existing_diseases"] = [user_message] if user_message.lower() != "no" else []
        session.medical_history = medical_history

        response_text = (
            f"Thank you for that information.\n\n"
            f"Now let me perform a comprehensive assessment based on everything you've shared."
        )
        session.conversation_stage = "risk_assessment"

    elif stage == "risk_assessment":
        # Perform risk assessment
        patient_data = {
            "age": session.patient_profile.get("age", 30) if session.patient_profile else 30,
            "smoking_status": session.medical_history.get("smoking_status", "") if session.medical_history else "",
            "existing_diseases": session.medical_history.get("existing_diseases", []) if session.medical_history else [],
            "family_history": session.medical_history.get("family_history", []) if session.medical_history else [],
        }

        risk_assessment = assess_risk_level(patient_data)
        session.risk_assessment = risk_assessment

        # Predict conditions
        symptoms_list = []
        if session.symptoms_data:
            if "primary_symptom" in session.symptoms_data:
                symptoms_list.append(session.symptoms_data["primary_symptom"])
            symptoms_list.extend(session.symptoms_data.get("additional_symptoms", []))

        medical_history_list = session.medical_history.get("existing_diseases", []) if session.medical_history else []

        possible_conditions = predict_conditions(
            symptoms_list,
            medical_history_list,
            patient_data.get("age", 30),
        )

        # Convert to JSON-serializable format
        session.possible_conditions = [
            {
                "condition": c.condition,
                "probability": c.probability,
                "confidence_level": c.confidence_level,
                "supporting_symptoms": c.supporting_symptoms,
                "missing_information": c.missing_information,
            }
            for c in possible_conditions
        ]

        # Generate recommendations
        recommendations = generate_recommendations(symptoms_list, risk_assessment, possible_conditions)
        session.recommendations = recommendations.model_dump()

        # Build assessment response
        response_text = (
            f"**ASSESSMENT SUMMARY**\n\n"
            f"**Risk Level:** {risk_assessment.get('overall_risk_score', 'MODERATE')}\n\n"
            f"**Possible Conditions:**\n"
        )

        for i, condition in enumerate(possible_conditions[:5], 1):
            response_text += (
                f"{i}. {condition.condition} "
                f"(Confidence: {condition.confidence_level})\n"
            )

        response_text += (
            f"\n**Recommendations:**\n"
            f"{chr(10).join('- ' + str(action) for action in recommendations.immediate_actions[:2])}\n\n"
            f"**MEDICAL DISCLAIMER:**\n"
            f"This assessment is informational only and not a medical diagnosis. "
            f"Please consult a licensed healthcare professional for medical advice.\n\n"
            f"Would you like more specific information about any of these conditions?"
        )

        session.conversation_stage = "completed"

    db.commit()

    return response_text, metadata


def get_session_assessment(db: Session, session_id: str) -> ChatAssessmentResponse | None:
    """Get complete assessment for a session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session or session.conversation_stage != "completed":
        return None

    # Parse data
    patient_profile = PatientProfileData(**session.patient_profile) if session.patient_profile else PatientProfileData()
    medical_history = MedicalHistoryData(**session.medical_history) if session.medical_history else MedicalHistoryData()
    symptoms_data = SymptomData(**session.symptoms_data) if session.symptoms_data else SymptomData()
    risk_assessment = RiskAssessmentData(**session.risk_assessment) if session.risk_assessment else RiskAssessmentData()
    recommendations = RecommendationData(**session.recommendations) if session.recommendations else RecommendationData()

    # Convert possible conditions
    possible_conditions = []
    if session.possible_conditions:
        for cond in session.possible_conditions:
            if isinstance(cond, dict):
                possible_conditions.append(PossibleCondition(**cond))
            else:
                possible_conditions.append(cond)

    return ChatAssessmentResponse(
        session_id=session_id,
        patient_summary=patient_profile,
        symptoms_summary=symptoms_data,
        risk_assessment=risk_assessment,
        possible_conditions=possible_conditions,
        recommendations=recommendations,
    )
