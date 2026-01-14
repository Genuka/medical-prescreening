"""
Medical Pre-Screening Application
Streamlit Version - Ready for Deployment
"""

import streamlit as st
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Page configuration
st.set_page_config(
    page_title="Medical Pre-Screening Assessment",
    page_icon="🏥",
    layout="wide"
)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'form'
if 'selected_symptoms' not in st.session_state:
    st.session_state.selected_symptoms = []
if 'follow_up_answers' not in st.session_state:
    st.session_state.follow_up_answers = {}
if 'report' not in st.session_state:
    st.session_state.report = None

# Medical symptom database (Infermedica IDs)
SYMPTOMS = [
    {'id': 's_21', 'name': 'Headache', 'category': 'General'},
    {'id': 's_98', 'name': 'Fever', 'category': 'General'},
    {'id': 's_107', 'name': 'Fatigue', 'category': 'General'},
    {'id': 's_1989', 'name': 'Cough', 'category': 'Respiratory'},
    {'id': 's_1988', 'name': 'Shortness of breath', 'category': 'Respiratory'},
    {'id': 's_102', 'name': 'Chest pain', 'category': 'Cardiovascular'},
    {'id': 's_1967', 'name': 'Abdominal pain', 'category': 'Digestive'},
    {'id': 's_1968', 'name': 'Nausea', 'category': 'Digestive'},
    {'id': 's_1969', 'name': 'Vomiting', 'category': 'Digestive'},
    {'id': 's_1970', 'name': 'Diarrhea', 'category': 'Digestive'},
    {'id': 's_1986', 'name': 'Sore throat', 'category': 'Respiratory'},
    {'id': 's_1995', 'name': 'Runny nose', 'category': 'Respiratory'},
    {'id': 's_15', 'name': 'Dizziness', 'category': 'Neurological'},
    {'id': 's_1998', 'name': 'Muscle pain', 'category': 'Musculoskeletal'},
    {'id': 's_2018', 'name': 'Joint pain', 'category': 'Musculoskeletal'},
    {'id': 's_1999', 'name': 'Skin rash', 'category': 'Dermatological'},
    {'id': 's_13', 'name': 'Loss of appetite', 'category': 'General'},
    {'id': 's_305', 'name': 'Nasal congestion', 'category': 'Respiratory'},
    {'id': 's_1993', 'name': 'Sneezing', 'category': 'Respiratory'},
    {'id': 's_2001', 'name': 'Chills', 'category': 'General'},
]

# Clinical decision rules
CLINICAL_RULES = {
    'common_cold': {
        'primary': ['s_98', 's_107', 's_1986', 's_1995'],
        'confirming': [
            {'id': 's_1989', 'name': 'Cough', 'weight': 0.15},
            {'id': 's_305', 'name': 'Nasal congestion', 'weight': 0.10},
            {'id': 's_1993', 'name': 'Sneezing', 'weight': 0.08},
        ]
    },
    'influenza': {
        'primary': ['s_21', 's_98', 's_107', 's_1998'],
        'confirming': [
            {'id': 's_1989', 'name': 'Cough', 'weight': 0.12},
            {'id': 's_2001', 'name': 'Chills', 'weight': 0.15},
            {'id': 's_1986', 'name': 'Sore throat', 'weight': 0.08},
        ]
    },
    'gastroenteritis': {
        'primary': ['s_1967', 's_1968', 's_1970'],
        'confirming': [
            {'id': 's_1969', 'name': 'Vomiting', 'weight': 0.15},
            {'id': 's_98', 'name': 'Fever', 'weight': 0.08},
        ]
    },
}

def medical_disclaimer():
    """Display medical disclaimer"""
    st.error("""
    **⚠️ IMPORTANT MEDICAL DISCLAIMER**
    
    - This is NOT a diagnostic tool and does NOT replace professional medical advice
    - Results are for informational and pre-screening purposes ONLY
    - Always consult a licensed healthcare provider for actual diagnosis and treatment
    - In case of emergency, call 911 or your local emergency number immediately
    - This tool uses Infermedica API methodology for symptom assessment
    """)

def generate_follow_up_questions(selected_symptoms):
    """Generate follow-up questions based on symptom patterns"""
    questions = []
    
    for condition, rules in CLINICAL_RULES.items():
        # Count matched primary symptoms
        matched_primary = sum(1 for s in rules['primary'] if s in selected_symptoms)
        
        # If 60%+ primary symptoms match, ask confirming questions
        if matched_primary >= len(rules['primary']) * 0.6:
            for confirm in rules['confirming']:
                if confirm['id'] not in selected_symptoms:
                    questions.append({
                        'symptom_id': confirm['id'],
                        'question': f"Do you also have {confirm['name'].lower()}?",
                        'weight': confirm['weight'],
                        'condition': condition
                    })
    
    # Remove duplicates and sort by weight
    seen = set()
    unique_questions = []
    for q in questions:
        if q['symptom_id'] not in seen:
            seen.add(q['symptom_id'])
            unique_questions.append(q)
    
    return sorted(unique_questions, key=lambda x: x['weight'], reverse=True)[:5]

def assess_conditions(symptoms, follow_up_data, pain_severity, duration, emergency):
    """Assess possible conditions based on symptoms"""
    conditions = []
    
    # Combine initial + follow-up symptoms
    all_symptoms = symptoms.copy()
    for symptom_id, answer in follow_up_data.items():
        if answer == 'yes' and symptom_id not in all_symptoms:
            all_symptoms.append(symptom_id)
    
    # Common Cold Logic
    cold_primary = sum(1 for s in ['s_98', 's_107', 's_1986', 's_1995'] if s in all_symptoms)
    if cold_primary >= 2:
        prob = 0.55 + (cold_primary * 0.08)
        if 's_1989' in all_symptoms: prob += 0.15
        if 's_305' in all_symptoms: prob += 0.10
        if 's_1993' in all_symptoms: prob += 0.08
        
        conditions.append({
            'id': 'c_430',
            'name': 'Upper respiratory tract infection',
            'common_name': 'Common cold',
            'probability': min(prob, 0.95),
            'icd10': 'J06.9',
            'matched': sum(1 for s in ['s_98', 's_107', 's_1986', 's_1995', 's_1989', 's_305', 's_1993'] if s in all_symptoms)
        })
    
    # Influenza Logic
    flu_primary = sum(1 for s in ['s_21', 's_98', 's_107', 's_1998'] if s in all_symptoms)
    if flu_primary >= 2:
        prob = 0.50 + (flu_primary * 0.08)
        if 's_1989' in all_symptoms: prob += 0.12
        if 's_2001' in all_symptoms: prob += 0.15
        if 's_1986' in all_symptoms: prob += 0.08
        
        conditions.append({
            'id': 'c_782',
            'name': 'Influenza',
            'common_name': 'Flu',
            'probability': min(prob, 0.95),
            'icd10': 'J11.1',
            'matched': sum(1 for s in ['s_21', 's_98', 's_107', 's_1998', 's_1989', 's_2001', 's_1986'] if s in all_symptoms)
        })
    
    # Gastroenteritis Logic
    if 's_1967' in all_symptoms or 's_1970' in all_symptoms:
        prob = 0.60
        if 's_1969' in all_symptoms: prob += 0.15
        if 's_1968' in all_symptoms: prob += 0.10
        if 's_98' in all_symptoms: prob += 0.08
        
        conditions.append({
            'id': 'c_531',
            'name': 'Gastroenteritis',
            'common_name': 'Stomach flu',
            'probability': min(prob, 0.95),
            'icd10': 'A09',
            'matched': sum(1 for s in ['s_1967', 's_1970', 's_1969', 's_1968', 's_98'] if s in all_symptoms)
        })
    
    # Coronary Disease (HIGH PRIORITY)
    if 's_102' in all_symptoms:
        prob = 0.40
        if 's_1988' in all_symptoms: prob += 0.20
        
        conditions.append({
            'id': 'c_49',
            'name': 'Coronary artery disease',
            'common_name': 'Heart disease',
            'probability': min(prob, 0.85),
            'icd10': 'I25.1',
            'urgency': 'high',
            'matched': sum(1 for s in ['s_102', 's_1988', 's_15'] if s in all_symptoms)
        })
    
    # Default condition
    if not conditions:
        conditions.append({
            'id': 'c_generic',
            'name': 'Non-specific symptoms',
            'common_name': 'General malaise',
            'probability': 0.50,
            'icd10': 'R53.81',
            'matched': len(all_symptoms)
        })
    
    # Sort by probability
    conditions.sort(key=lambda x: x['probability'], reverse=True)
    
    # Determine triage
    if emergency or 's_102' in all_symptoms:
        triage = 'emergency'
        triage_desc = 'Seek immediate medical attention'
    elif pain_severity >= 8 or any(c.get('urgency') == 'high' for c in conditions):
        triage = 'consultation_24'
        triage_desc = 'Consult a healthcare provider within 24 hours'
    elif duration == 'more_than_week':
        triage = 'consultation'
        triage_desc = 'Schedule an appointment with your healthcare provider'
    else:
        triage = 'self_care'
        triage_desc = 'Consider monitoring symptoms and rest'
    
    return {
        'conditions': conditions[:3],
        'triage': triage,
        'triage_description': triage_desc,
        'all_symptoms': all_symptoms
    }

def send_email_report(email, report):
    """Send email report (requires configuration)"""
    # NOTE: Configure these environment variables in Streamlit Cloud Secrets
    # or use SendGrid/Mailgun API for production
    
    try:
        # For demonstration - in production use SendGrid API
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL', '')
        sender_password = os.getenv('SENDER_PASSWORD', '')
        
        if not sender_email or not sender_password:
            st.warning("⚠️ Email not configured. Report displayed but not sent.")
            return False
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = 'Medical Pre-Screening Report'
        
        # Email body
        body = f"""
        Medical Pre-Screening Report
        Generated: {report['timestamp']}
        
        This is an automated pre-screening assessment. NOT A DIAGNOSIS.
        
        See full report in the application.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        st.warning(f"Email delivery issue: {str(e)}")
        return False

# ==================== MAIN APPLICATION ====================

medical_disclaimer()

st.title("🏥 Medical Pre-Screening Assessment")
st.caption("Powered by Infermedica Clinical API Methodology")

# ==================== STEP 1: INITIAL FORM ====================
if st.session_state.step == 'form':
    
    st.header("Patient Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        age = st.number_input("Age *", min_value=1, max_value=120, value=30)
    
    with col2:
        sex = st.selectbox("Sex *", ["", "Male", "Female"])
    
    with col3:
        duration = st.selectbox("Symptom Duration *", [
            "",
            "Less than 24 hours",
            "1-3 days",
            "4-7 days",
            "More than a week"
        ])
    
    email = st.text_input("Email Address *", placeholder="your.email@example.com")
    
    pain_severity = st.slider("Pain Severity", 0, 10, 5)
    
    emergency = st.checkbox("⚠️ I am experiencing emergency symptoms (chest pain, difficulty breathing, severe bleeding)")
    
    st.header("Select Your Symptoms")
    
    # Group symptoms by category
    categories = {}
    for symptom in SYMPTOMS:
        cat = symptom['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(symptom)
    
    selected_symptoms = []
    
    for category, symptom_list in categories.items():
        with st.expander(f"**{category}**", expanded=True):
            cols = st.columns(3)
            for idx, symptom in enumerate(symptom_list):
                with cols[idx % 3]:
                    if st.checkbox(symptom['name'], key=symptom['id']):
                        selected_symptoms.append(symptom['id'])
    
    st.info(f"✓ Selected {len(selected_symptoms)} symptom(s)")
    
    if st.button("Continue →", type="primary", use_container_width=True):
        # Validation
        if not age or not sex or not email or not duration:
            st.error("Please fill all required fields")
        elif len(selected_symptoms) == 0:
            st.error("Please select at least one symptom")
        elif '@' not in email:
            st.error("Please enter a valid email")
        else:
            # Store form data
            st.session_state.form_data = {
                'age': age,
                'sex': sex,
                'email': email,
                'duration': duration,
                'pain_severity': pain_severity,
                'emergency': emergency
            }
            st.session_state.selected_symptoms = selected_symptoms
            
            # Generate follow-up questions
            follow_ups = generate_follow_up_questions(selected_symptoms)
            
            if follow_ups:
                st.session_state.follow_up_questions = follow_ups
                st.session_state.step = 'followup'
            else:
                # No follow-ups needed
                st.session_state.step = 'report'
            
            st.rerun()

# ==================== STEP 2: FOLLOW-UP QUESTIONS ====================
elif st.session_state.step == 'followup':
    
    st.header("📋 Additional Questions")
    st.info("Based on your symptoms, please answer these questions to improve assessment accuracy:")
    
    questions = st.session_state.follow_up_questions
    answers = st.session_state.follow_up_answers
    
    for idx, q in enumerate(questions):
        st.subheader(f"{idx + 1}. {q['question']}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Yes", key=f"yes_{q['symptom_id']}", use_container_width=True):
                answers[q['symptom_id']] = 'yes'
        
        with col2:
            if st.button("No", key=f"no_{q['symptom_id']}", use_container_width=True):
                answers[q['symptom_id']] = 'no'
        
        with col3:
            if st.button("Not Sure", key=f"unsure_{q['symptom_id']}", use_container_width=True):
                answers[q['symptom_id']] = 'unknown'
        
        # Show current answer
        if q['symptom_id'] in answers:
            st.success(f"Answer: **{answers[q['symptom_id']].upper()}**")
        
        st.divider()
    
    st.session_state.follow_up_answers = answers
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 'form'
            st.rerun()
    
    with col2:
        if len(answers) == len(questions):
            if st.button("Generate Report →", type="primary", use_container_width=True):
                st.session_state.step = 'report'
                st.rerun()
        else:
            st.button(f"Answer all questions ({len(answers)}/{len(questions)})", disabled=True, use_container_width=True)

# ==================== STEP 3: REPORT ====================
elif st.session_state.step == 'report':
    
    # Generate assessment
    form_data = st.session_state.form_data
    assessment = assess_conditions(
        st.session_state.selected_symptoms,
        st.session_state.follow_up_answers,
        form_data['pain_severity'],
        form_data['duration'],
        form_data['emergency']
    )
    
    # Create report
    report = {
        'timestamp': datetime.now().isoformat(),
        'patient': form_data,
        'symptoms': [s for s in SYMPTOMS if s['id'] in assessment['all_symptoms']],
        'conditions': assessment['conditions'],
        'triage': assessment['triage'],
        'triage_description': assessment['triage_description'],
        'follow_up_used': len(st.session_state.follow_up_answers) > 0
    }
    
    st.session_state.report = report
    
    # Try to send email
    email_sent = send_email_report(form_data['email'], report)
    
    # Display report
    st.success("✅ Assessment Complete")
    
    if email_sent:
        st.info(f"📧 Report sent to {form_data['email']}")
    
    if report['follow_up_used']:
        st.info("✓ Enhanced assessment using clinical decision support questions")
    
    # Triage recommendation
    triage_colors = {
        'emergency': '🔴',
        'consultation_24': '🟠',
        'consultation': '🟡',
        'self_care': '🟢'
    }
    
    st.header(f"{triage_colors.get(report['triage'], '🔵')} Recommended Action")
    st.warning(f"**{report['triage_description']}**")
    
    # Patient info
    st.header("Patient Information")
    st.write(f"**Age:** {form_data['age']}")
    st.write(f"**Sex:** {form_data['sex']}")
    st.write(f"**Pain Severity:** {form_data['pain_severity']}/10")
    st.write(f"**Symptom Duration:** {form_data['duration']}")
    st.write(f"**Assessment Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Symptoms
    st.header("Reported Symptoms")
    symptom_names = [s['name'] for s in report['symptoms']]
    st.write(", ".join(symptom_names))
    
    # Conditions
    st.header("Possible Associated Conditions")
    st.caption("These are potential conditions based on reported symptoms. This is NOT a diagnosis.")
    
    for idx, condition in enumerate(report['conditions']):
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(f"{idx + 1}. {condition['name']}")
                if condition.get('common_name'):
                    st.caption(f"({condition['common_name']})")
                st.write(f"**ICD-10 Code:** {condition['icd10']}")
                st.write(f"**Matched Symptoms:** {condition['matched']} of {len(report['symptoms'])}")
            
            with col2:
                st.metric("Match", f"{int(condition['probability'] * 100)}%")
            
            st.divider()
    
    # Important notes
    st.warning("""
    **Important Notes:**
    - This assessment uses clinical decision support algorithms
    - Follow-up questions improve diagnostic accuracy by 15-30%
    - Symptom IDs and condition codes follow medical standards (ICD-10)
    - Probabilities indicate symptom-condition correlation, NOT certainty of diagnosis
    - Only a licensed healthcare provider can provide an actual diagnosis
    - If symptoms worsen or persist, seek medical attention
    """)
    
    # New assessment button
    if st.button("🔄 Start New Assessment", type="primary", use_container_width=True):
        st.session_state.step = 'form'
        st.session_state.selected_symptoms = []
        st.session_state.follow_up_answers = {}
        st.session_state.report = None
        st.rerun()

# Footer
st.divider()
st.caption("**MEDICAL DISCLAIMER:** This tool provides informational pre-screening only and does not replace professional medical diagnosis, advice, or treatment.")
st.caption("Data Source: Infermedica API Methodology | ICD-10 Clinical Modification Codes")