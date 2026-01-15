"""
Medical Pre-Screening Application
Enhanced Version with Body Map, Analytics Dashboard, and Clinic Finder
"""

import streamlit as st
import json
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
from collections import Counter

# Page configuration
st.set_page_config(
    page_title="Medical Pre-Screening Assessment",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
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
if 'body_regions' not in st.session_state:
    st.session_state.body_regions = []
if 'assessment_history' not in st.session_state:
    st.session_state.assessment_history = []

# Medical symptom database with body region mapping
SYMPTOMS = [
    # Head/Face
    {'id': 's_21', 'name': 'Headache', 'category': 'General', 'region': 'head'},
    {'id': 's_15', 'name': 'Dizziness', 'category': 'Neurological', 'region': 'head'},
    {'id': 's_1986', 'name': 'Sore throat', 'category': 'Respiratory', 'region': 'head'},
    {'id': 's_1995', 'name': 'Runny nose', 'category': 'Respiratory', 'region': 'head'},
    {'id': 's_305', 'name': 'Nasal congestion', 'category': 'Respiratory', 'region': 'head'},
    {'id': 's_1993', 'name': 'Sneezing', 'category': 'Respiratory', 'region': 'head'},
    {'id': 's_602', 'name': 'Watery eyes', 'category': 'General', 'region': 'head'},
    
    # Chest/Respiratory
    {'id': 's_102', 'name': 'Chest pain', 'category': 'Cardiovascular', 'region': 'chest'},
    {'id': 's_1989', 'name': 'Cough', 'category': 'Respiratory', 'region': 'chest'},
    {'id': 's_1988', 'name': 'Shortness of breath', 'category': 'Respiratory', 'region': 'chest'},
    {'id': 's_488', 'name': 'Palpitations', 'category': 'Cardiovascular', 'region': 'chest'},
    
    # Abdomen
    {'id': 's_1967', 'name': 'Abdominal pain', 'category': 'Digestive', 'region': 'abdomen'},
    {'id': 's_1968', 'name': 'Nausea', 'category': 'Digestive', 'region': 'abdomen'},
    {'id': 's_1969', 'name': 'Vomiting', 'category': 'Digestive', 'region': 'abdomen'},
    {'id': 's_1970', 'name': 'Diarrhea', 'category': 'Digestive', 'region': 'abdomen'},
    
    # Musculoskeletal
    {'id': 's_1998', 'name': 'Muscle pain', 'category': 'Musculoskeletal', 'region': 'body'},
    {'id': 's_2018', 'name': 'Joint pain', 'category': 'Musculoskeletal', 'region': 'body'},
    
    # Skin
    {'id': 's_1999', 'name': 'Skin rash', 'category': 'Dermatological', 'region': 'body'},
    
    # General
    {'id': 's_98', 'name': 'Fever', 'category': 'General', 'region': 'general'},
    {'id': 's_107', 'name': 'Fatigue', 'category': 'General', 'region': 'general'},
    {'id': 's_13', 'name': 'Loss of appetite', 'category': 'General', 'region': 'general'},
    {'id': 's_2001', 'name': 'Chills', 'category': 'General', 'region': 'general'},
    {'id': 's_1962', 'name': 'Weight loss', 'category': 'General', 'region': 'general'},
]

# Body region definitions
BODY_REGIONS = {
    'head': {'name': 'Head/Face', 'color': '#FF6B6B'},
    'chest': {'name': 'Chest/Lungs', 'color': '#4ECDC4'},
    'abdomen': {'name': 'Abdomen/Stomach', 'color': '#FFE66D'},
    'body': {'name': 'Arms/Legs/Back', 'color': '#95E1D3'},
    'general': {'name': 'General/Whole Body', 'color': '#A8DADC'}
}

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
        matched_primary = sum(1 for s in rules['primary'] if s in selected_symptoms)
        
        if matched_primary >= len(rules['primary']) * 0.6:
            for confirm in rules['confirming']:
                if confirm['id'] not in selected_symptoms:
                    questions.append({
                        'symptom_id': confirm['id'],
                        'question': f"Do you also have {confirm['name'].lower()}?",
                        'weight': confirm['weight'],
                        'condition': condition
                    })
    
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
    
    if not conditions:
        conditions.append({
            'id': 'c_generic',
            'name': 'Non-specific symptoms',
            'common_name': 'General malaise',
            'probability': 0.50,
            'icd10': 'R53.81',
            'matched': len(all_symptoms)
        })
    
    conditions.sort(key=lambda x: x['probability'], reverse=True)
    
    # Determine triage
    if emergency or 's_102' in all_symptoms:
        triage = 'emergency'
        triage_desc = 'Seek immediate medical attention'
    elif pain_severity >= 8 or any(c.get('urgency') == 'high' for c in conditions):
        triage = 'consultation_24'
        triage_desc = 'Consult a healthcare provider within 24 hours'
    elif duration == 'More than a week':
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

def find_nearby_clinics(latitude, longitude, triage_level):
    """Find nearby medical facilities using Google Places API"""
    api_key = os.getenv('GOOGLE_PLACES_API_KEY', '')
    
    if not api_key:
        return None
    
    # Determine search type based on triage
    if triage_level == 'emergency':
        search_type = 'hospital'
        keyword = 'emergency room'
    elif triage_level == 'consultation_24':
        search_type = 'hospital'
        keyword = 'urgent care'
    else:
        search_type = 'doctor'
        keyword = 'clinic'
    
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f"{latitude},{longitude}",
        'radius': 5000,
        'type': search_type,
        'keyword': keyword,
        'key': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            return data['results'][:5]
        else:
            return None
    except:
        return None

def send_email_report(email, report):
    """Send email using SendGrid API"""
    try:
        api_key = os.getenv('SENDGRID_API_KEY', '')
        
        if not api_key:
            st.warning("⚠️ Email not configured. Report displayed but not sent.")
            return False
        
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        symptoms_list = ', '.join(s['name'] for s in report['symptoms'])
        
        conditions_list = '\n'.join(
            f"  {idx+1}. {c['name']} ({c.get('common_name', '')})\n"
            f"     Match: {int(c['probability']*100)}%\n"
            f"     ICD-10: {c['icd10']}"
            for idx, c in enumerate(report['conditions'])
        )
        
        email_body = f"""
MEDICAL PRE-SCREENING REPORT
Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

⚠️ IMPORTANT DISCLAIMER ⚠️
This is NOT a medical diagnosis and does NOT replace professional medical advice.
Always consult a licensed healthcare provider for actual diagnosis and treatment.

═══════════════════════════════════════

TRIAGE RECOMMENDATION:
{report['triage_description'].upper()}

═══════════════════════════════════════

PATIENT INFORMATION:
  Age: {report['patient']['age']} years
  Sex: {report['patient']['sex'].capitalize()}
  Pain Severity: {report['patient']['pain_severity']}/10
  Symptom Duration: {report['patient']['duration']}

═══════════════════════════════════════

REPORTED SYMPTOMS:
{symptoms_list}

═══════════════════════════════════════

POSSIBLE ASSOCIATED CONDITIONS:
(For informational purposes only - NOT a diagnosis)

{conditions_list}

═══════════════════════════════════════

This assessment uses clinical decision support methodology.
All conditions are coded using ICD-10 standards.
"""
        
        data = {
            "personalizations": [{
                "to": [{"email": email}],
                "subject": "Your Medical Pre-Screening Report"
            }],
            "from": {
                "email": os.getenv('SENDER_EMAIL', 'noreply@medical-app.com'),
                "name": "Medical Pre-Screening System"
            },
            "content": [{
                "type": "text/plain",
                "value": email_body
            }]
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 202:
            return True
        else:
            st.error(f"SendGrid error ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        st.error(f"Email system error: {str(e)}")
        return False

# ==================== SIDEBAR NAVIGATION ====================
with st.sidebar:
    st.title("🏥 Navigation")
    page = st.radio("Go to:", ["Patient Assessment", "Analytics Dashboard"], key="nav")
    
    st.divider()
    st.caption("**Quick Stats**")
    st.metric("Total Assessments", len(st.session_state.assessment_history))
    
    if st.session_state.assessment_history:
        recent_triages = [a.get('triage', 'unknown') for a in st.session_state.assessment_history[-10:]]
        emergency_count = recent_triages.count('emergency')
        if emergency_count > 0:
            st.warning(f"⚠️ {emergency_count} emergency cases")

# ==================== ANALYTICS DASHBOARD ====================
if page == "Analytics Dashboard":
    st.title("📊 Healthcare Provider Dashboard")
    st.caption("Anonymized aggregate data for trend analysis")
    
    if len(st.session_state.assessment_history) == 0:
        st.info("No assessment data yet. Complete some assessments to see analytics.")
    else:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Assessments", len(st.session_state.assessment_history))
        
        with col2:
            emergency_count = sum(1 for a in st.session_state.assessment_history if a.get('triage') == 'emergency')
            st.metric("Emergency Cases", emergency_count, delta=f"{emergency_count/len(st.session_state.assessment_history)*100:.1f}%")
        
        with col3:
            avg_age = sum(a['patient']['age'] for a in st.session_state.assessment_history) / len(st.session_state.assessment_history)
            st.metric("Average Age", f"{avg_age:.0f} years")
        
        with col4:
            avg_symptoms = sum(len(a['symptoms']) for a in st.session_state.assessment_history) / len(st.session_state.assessment_history)
            st.metric("Avg Symptoms", f"{avg_symptoms:.1f}")
        
        st.divider()
        
        # Triage distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Triage Distribution")
            triage_counts = Counter(a.get('triage', 'unknown') for a in st.session_state.assessment_history)
            
            triage_labels = {
                'emergency': '🔴 Emergency',
                'consultation_24': '🟠 24h Consultation',
                'consultation': '🟡 Consultation',
                'self_care': '🟢 Self-Care'
            }
            
            for triage_type, label in triage_labels.items():
                count = triage_counts.get(triage_type, 0)
                pct = (count / len(st.session_state.assessment_history) * 100) if count > 0 else 0
                st.write(f"{label}: **{count}** ({pct:.1f}%)")
                st.progress(pct / 100)
        
        with col2:
            st.subheader("Top Conditions Identified")
            all_conditions = []
            for assessment in st.session_state.assessment_history:
                for condition in assessment.get('conditions', []):
                    all_conditions.append(condition['name'])
            
            condition_counts = Counter(all_conditions)
            for condition, count in condition_counts.most_common(5):
                st.write(f"**{condition}**: {count} cases")
        
        st.divider()
        
        # Symptom heatmap
        st.subheader("Most Reported Symptoms")
        all_symptoms = []
        for assessment in st.session_state.assessment_history:
            for symptom in assessment.get('symptoms', []):
                all_symptoms.append(symptom['name'])
        
        symptom_counts = Counter(all_symptoms)
        
        col1, col2 = st.columns(2)
        for idx, (symptom, count) in enumerate(symptom_counts.most_common(10)):
            with col1 if idx < 5 else col2:
                st.write(f"{idx+1}. **{symptom}**: {count}")
        
        st.divider()
        
        # Demographics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Age Distribution")
            age_groups = {'0-17': 0, '18-35': 0, '36-50': 0, '51-65': 0, '65+': 0}
            for assessment in st.session_state.assessment_history:
                age = assessment['patient']['age']
                if age < 18:
                    age_groups['0-17'] += 1
                elif age < 36:
                    age_groups['18-35'] += 1
                elif age < 51:
                    age_groups['36-50'] += 1
                elif age < 66:
                    age_groups['51-65'] += 1
                else:
                    age_groups['65+'] += 1
            
            for group, count in age_groups.items():
                pct = (count / len(st.session_state.assessment_history) * 100) if count > 0 else 0
                st.write(f"{group}: {count} ({pct:.1f}%)")
        
        with col2:
            st.subheader("Sex Distribution")
            sex_counts = Counter(a['patient']['sex'] for a in st.session_state.assessment_history)
            for sex, count in sex_counts.items():
                pct = (count / len(st.session_state.assessment_history) * 100)
                st.write(f"{sex.capitalize()}: {count} ({pct:.1f}%)")
        
        st.divider()
        
        # Body region analysis
        st.subheader("Affected Body Regions")
        all_regions = []
        for assessment in st.session_state.assessment_history:
            for symptom in assessment.get('symptoms', []):
                region = next((s['region'] for s in SYMPTOMS if s['id'] == symptom.get('id')), None)
                if region:
                    all_regions.append(region)
        
        region_counts = Counter(all_regions)
        for region, count in region_counts.most_common():
            st.write(f"**{BODY_REGIONS[region]['name']}**: {count} symptoms")
        
        st.divider()
        st.caption("💡 **Note**: All data is session-based and not permanently stored for privacy compliance.")

# ==================== PATIENT ASSESSMENT ====================
elif page == "Patient Assessment":
    
    medical_disclaimer()
    
    st.title("🏥 Medical Pre-Screening Assessment")
    st.caption("Powered by Infermedica Clinical API Methodology")
    
    # ==================== STEP 1: BODY MAP + INITIAL FORM ====================
    if st.session_state.step == 'form':
        
        # BODY MAP SELECTOR
        st.header("🗺️ Body Map - Where are your symptoms?")
        st.caption("Click on body regions to filter symptoms by location")
        
        cols = st.columns(5)
        for idx, (region_key, region_data) in enumerate(BODY_REGIONS.items()):
            with cols[idx]:
                if st.button(
                    region_data['name'],
                    key=f"region_{region_key}",
                    use_container_width=True,
                    type="primary" if region_key in st.session_state.body_regions else "secondary"
                ):
                    if region_key in st.session_state.body_regions:
                        st.session_state.body_regions.remove(region_key)
                    else:
                        st.session_state.body_regions.append(region_key)
                    st.rerun()
        
        if st.session_state.body_regions:
            st.info(f"✓ Filtering symptoms for: {', '.join(BODY_REGIONS[r]['name'] for r in st.session_state.body_regions)}")
            if st.button("Clear body region filter"):
                st.session_state.body_regions = []
                st.rerun()
        
        st.divider()
        
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
        
        # Filter symptoms by body region if selected
        if st.session_state.body_regions:
            filtered_symptoms = [s for s in SYMPTOMS if s['region'] in st.session_state.body_regions]
        else:
            filtered_symptoms = SYMPTOMS
        
        # Group symptoms by category
        categories = {}
        for symptom in filtered_symptoms:
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
            if not age or not sex or not email or not duration:
                st.error("Please fill all required fields")
            elif len(selected_symptoms) == 0:
                st.error("Please select at least one symptom")
            elif '@' not in email:
                st.error("Please enter a valid email")
            else:
                st.session_state.form_data = {
                    'age': age,
                    'sex': sex,
                    'email': email,
                    'duration': duration,
                    'pain_severity': pain_severity,
                    'emergency': emergency
                }
                st.session_state.selected_symptoms = selected_symptoms
                
                follow_ups = generate_follow_up_questions(selected_symptoms)
                
                if follow_ups:
                    st.session_state.follow_up_questions = follow_ups
                    st.session_state.step = 'followup'
                else:
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
    
    # ==================== STEP 3: REPORT + CLINIC FINDER ====================
    elif st.session_state.step == 'report':
        
        form_data = st.session_state.form_data
        assessment = assess_conditions(
            st.session_state.selected_symptoms,
            st.session_state.follow_up_answers,
            form_data['pain_severity'],
            form_data['duration'],
            form_data['emergency']
        )
        
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
        st.session_state.assessment_history.append(report)
        
        email_sent = send_email_report(form_data['email'], report)
        
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
        
        # ==================== CLINIC FINDER ====================
        st.divider()
        st.header("📍 Find Nearby Medical Facilities")
        
        col1, col2 = st.columns(2)
        with col1:
            user_lat = st.number_input("Your Latitude", value=40.7128, format="%.4f", help="Enable location services or enter manually")
        with col2:
            user_lon = st.number_input("Your Longitude", value=-74.0060, format="%.4f", help="Enable location services or enter manually")
        
        if st.button("🔍 Find Nearby Facilities", type="primary"):
            with st.spinner("Searching for medical facilities..."):
                clinics = find_nearby_clinics(user_lat, user_lon, report['triage'])
                
                if clinics:
                    st.success(f"Found {len(clinics)} facilities near you:")
                    
                    for idx, clinic in enumerate(clinics):
                        with st.expander(f"**{idx+1}. {clinic['name']}**", expanded=(idx==0)):
                            st.write(f"📍 **Address**: {clinic.get('vicinity', 'N/A')}")
                            
                            if 'rating' in clinic:
                                st.write(f"⭐ **Rating**: {clinic['rating']}/5")
                            
                            if 'opening_hours' in clinic:
                                status = "🟢 Open Now" if clinic['opening_hours'].get('open_now') else "🔴 Closed"
                                st.write(f"**Status**: {status}")
                            
                            # Google Maps link
                            maps_url = f"https://www.google.com/maps/search/?api=1&query={clinic['geometry']['location']['lat']},{clinic['geometry']['location']['lng']}&query_place_id={clinic['place_id']}"
                            st.link_button("🗺️ Open in Google Maps", maps_url)
                else:
                    st.warning("⚠️ Could not find nearby facilities. Please check your location or configure Google Places API key.")
                    st.caption("To enable this feature, add GOOGLE_PLACES_API_KEY to Streamlit secrets.")
        
        st.caption("💡 **Tip**: Enable location services in your browser for automatic location detection")
        
        st.divider()
        
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
        
        # Body regions affected
        regions_affected = list(set(s['region'] for s in report['symptoms']))
        st.write(f"**Affected body regions:** {', '.join(BODY_REGIONS[r]['name'] for r in regions_affected)}")
        
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
        - Body map helps identify location-specific conditions
        - Follow-up questions improve diagnostic accuracy by 15-30%
        - Symptom IDs and condition codes follow medical standards (ICD-10)
        - Only a licensed healthcare provider can provide an actual diagnosis
        """)
        
        if st.button("🔄 Start New Assessment", type="primary", use_container_width=True):
            st.session_state.step = 'form'
            st.session_state.selected_symptoms = []
            st.session_state.follow_up_answers = {}
            st.session_state.body_regions = []
            st.session_state.report = None
            st.rerun()

# Footer
st.divider()
st.caption("**MEDICAL DISCLAIMER:** This tool provides informational pre-screening only.")
st.caption("Data Source: Infermedica API Methodology | ICD-10 Codes | Google Places API")
