import streamlit as st
import joblib
import os
import pandas as pd
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from database import (
    initialize_database,
    register_user,
    authenticate_user,
    save_assessment,
    get_patient_history
)


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Clinical Decision Support System",
    page_icon="🏥",
    layout="wide"
)

MODEL_FILE = "stroke_model.pkl"


# ============================================================
# CHECK MODEL
# ============================================================

if not os.path.exists(MODEL_FILE):
    st.error(
        "stroke_model.pkl not found. "
        "Please make sure the model file is inside the "
        "stroke_cds project folder."
    )
    st.stop()

try:
    stroke_model = joblib.load(MODEL_FILE)
except Exception as e:
    st.error(f"Error loading stroke model: {e}")
    st.stop()


# ============================================================
# INITIALIZE DATABASE
# ============================================================

try:
    initialize_database()
except Exception as e:
    st.error(f"Database initialization error: {e}")
    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "logged_in": False,
    "username": "",
    "page": "dashboard",
    "prediction": None,
    "risk_score": None,
    "ml_probability": None,
    "recommendation": None,
    "befast_positive": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# CLEAR PREDICTION
# ============================================================

def clear_prediction():
    st.session_state.prediction = None
    st.session_state.risk_score = None
    st.session_state.ml_probability = None
    st.session_state.recommendation = None
    st.session_state.befast_positive = False


# ============================================================
# CREATE PDF REPORT
# ============================================================

def create_pdf(data):

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "HospitalTitle",
        parent=styles["Title"],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=5
    )

    report_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading2"],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=18
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=15,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_CENTER
    )

    story = []

    # ========================================================
    # HEADER
    # ========================================================

    story.append(
        Paragraph(
            "City General Hospital",
            title_style
        )
    )

    story.append(
        Paragraph(
            "AI Stroke Risk Assessment Report",
            report_style
        )
    )

    # ========================================================
    # PATIENT DETAILS
    # ========================================================

    patient_table = Table(
        [
            [
                Paragraph(
                    f"<b>Patient:</b> {data['patient_name']}",
                    normal_style
                ),
                Paragraph(
                    f"<b>Date:</b> {data['date']}",
                    normal_style
                )
            ],
            [
                Paragraph(
                    f"<b>Age:</b> {data['age']}",
                    normal_style
                ),
                Paragraph(
                    f"<b>Gender:</b> {data['gender']}",
                    normal_style
                )
            ]
        ],
        colWidths=[270, 210]
    )

    patient_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
        ])
    )

    story.append(patient_table)
    story.append(Spacer(1, 10))

    # ========================================================
    # RISK RESULT
    # ========================================================

    if data["risk_level"] == "HIGH":
        risk_color = colors.red
    elif data["risk_level"] == "MEDIUM":
        risk_color = colors.orange
    else:
        risk_color = colors.green

    risk_text = (
        f"<b>Risk Score: {data['risk_score']:.1f}% "
        f"({data['risk_level'].title()} Risk)</b>"
    )

    risk_paragraph = Paragraph(
        risk_text,
        ParagraphStyle(
            "RiskText",
            parent=normal_style,
            alignment=TA_CENTER,
            textColor=risk_color,
            fontSize=12
        )
    )

    risk_table = Table(
        [[risk_paragraph]],
        colWidths=[480]
    )

    risk_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.2, risk_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10)
        ])
    )

    story.append(risk_table)

    # ========================================================
    # CLINICAL INPUTS
    # ========================================================

    story.append(
        Paragraph(
            "Clinical Inputs",
            heading_style
        )
    )

    clinical_rows = [
        [
            Paragraph("<b>Hypertension</b>", normal_style),
            data["hypertension"]
        ],
        [
            Paragraph("<b>Heart Disease</b>", normal_style),
            data["heart_disease"]
        ],
        [
            Paragraph("<b>Ever Married</b>", normal_style),
            data["ever_married"]
        ],
        [
            Paragraph("<b>Work Type</b>", normal_style),
            data["work_type"]
        ],
        [
            Paragraph("<b>Residence Type</b>", normal_style),
            data["residence_type"]
        ],
        [
            Paragraph("<b>Height</b>", normal_style),
            f"{data['height']:.1f} cm"
        ],
        [
            Paragraph("<b>Weight</b>", normal_style),
            f"{data['weight']:.1f} kg"
        ],
        [
            Paragraph("<b>Avg Glucose Level</b>", normal_style),
            f"{data['glucose']:.2f} mg/dL"
        ],
        [
            Paragraph("<b>BMI</b>", normal_style),
            f"{data['bmi']:.2f}"
        ],
        [
            Paragraph("<b>Smoking Status</b>", normal_style),
            data["smoking_status"]
        ]
    ]

    clinical_table = Table(
        clinical_rows,
        colWidths=[200, 280]
    )

    clinical_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
        ])
    )

    story.append(clinical_table)

    # ========================================================
    # BEFAST
    # ========================================================

    story.append(
        Paragraph(
            "BEFAST Symptoms",
            heading_style
        )
    )

    befast_rows = [
        [
            Paragraph("<b>Balance</b>", normal_style),
            "YES" if data["balance"] else "NO"
        ],
        [
            Paragraph("<b>Eyes</b>", normal_style),
            "YES" if data["eyes"] else "NO"
        ],
        [
            Paragraph("<b>Face</b>", normal_style),
            "YES" if data["face"] else "NO"
        ],
        [
            Paragraph("<b>Arm</b>", normal_style),
            "YES" if data["arm"] else "NO"
        ],
        [
            Paragraph("<b>Speech</b>", normal_style),
            "YES" if data["speech"] else "NO"
        ],
        [
            Paragraph("<b>Time</b>", normal_style),
            data["time_symptom"]
        ]
    ]

    befast_table = Table(
        befast_rows,
        colWidths=[200, 280]
    )

    befast_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 7)
        ])
    )

    story.append(befast_table)

    # ========================================================
    # RECOMMENDATION
    # ========================================================

    story.append(
        Paragraph(
            "Recommendation",
            heading_style
        )
    )

    story.append(
        Paragraph(
            data["recommendation"],
            normal_style
        )
    )

    # ========================================================
    # BEFAST ALERT
    # ========================================================

    if data["befast_positive"]:

        story.append(Spacer(1, 10))

        alert_style = ParagraphStyle(
            "Alert",
            parent=normal_style,
            textColor=colors.red,
            fontSize=10,
            leading=14
        )

        story.append(
            Paragraph(
                "<b>BEFAST ALERT:</b> One or more sudden "
                "stroke warning signs are present. "
                "Seek emergency medical attention immediately.",
                alert_style
            )
        )

    # ========================================================
    # FOOTER
    # ========================================================

    story.append(Spacer(1, 25))

    story.append(
        Paragraph(
            "Generated by AI Stroke Prediction System",
            footer_style
        )
    )

    story.append(Spacer(1, 5))

    story.append(
        Paragraph(
            "This report is for screening purposes only "
            "and is not a medical diagnosis.",
            ParagraphStyle(
                "Disclaimer",
                parent=footer_style,
                fontSize=8
            )
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer


# ============================================================
# CUSTOM CSS FOR PATIENT HISTORY
# ============================================================

st.markdown(
    """
    <style>

    .history-table-container {
        width: 100%;
        overflow-x: auto;
        margin-top: 15px;
        margin-bottom: 20px;
    }

    .history-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-family: Arial, sans-serif;
        background-color: white;
    }

    .history-table th {
        background-color: #f1f3f5;
        color: #222222;
        font-weight: 700;
        text-align: center;
        padding: 12px 10px;
        border: 1px solid #d9d9d9;
        white-space: nowrap;
    }

    .history-table td {
        color: #222222;
        padding: 12px 10px;
        border: 1px solid #d9d9d9;
        text-align: center;
        white-space: nowrap;
    }

    .history-table th:nth-child(1),
    .history-table td:nth-child(1) {
        width: 8%;
    }

    .history-table th:nth-child(2),
    .history-table td:nth-child(2) {
        width: 20%;
        text-align: left;
    }

    .history-table th:nth-child(3),
    .history-table td:nth-child(3) {
        width: 10%;
    }

    .history-table th:nth-child(4),
    .history-table td:nth-child(4) {
        width: 12%;
    }

    .history-table th:nth-child(5),
    .history-table td:nth-child(5) {
        width: 14%;
    }

    .history-table th:nth-child(6),
    .history-table td:nth-child(6) {
        width: 14%;
    }

    .history-table th:nth-child(7),
    .history-table td:nth-child(7) {
        width: 22%;
    }

    .risk-low {
        display: inline-block;
        background-color: #d4edda;
        color: #155724;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 5px;
    }

    .risk-medium {
        display: inline-block;
        background-color: #fff3cd;
        color: #856404;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 5px;
    }

    .risk-high {
        display: inline-block;
        background-color: #f8d7da;
        color: #721c24;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 5px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# APPLICATION TITLE
# ============================================================

st.title("🏥 Clinical Decision Support System")


# ============================================================
# LOGIN / REGISTER PAGE
# ============================================================

if not st.session_state.logged_in:

    login_tab, register_tab = st.tabs(
        ["🔐 Login", "📝 Register"]
    )

    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

        st.subheader("🔐 Login")

        username = st.text_input(
            "Username",
            key="login_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "Login",
            use_container_width=True
        ):

            if not username or not password:

                st.warning(
                    "Please enter username and password."
                )

            elif authenticate_user(
                username,
                password
            ):

                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.page = "dashboard"

                clear_prediction()

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    # ========================================================
    # REGISTER
    # ========================================================

    with register_tab:

        st.subheader("📝 Create Account")

        new_username = st.text_input(
            "Username",
            key="register_username"
        )

        new_password = st.text_input(
            "Password",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="confirm_password"
        )

        if st.button(
            "Create Account",
            use_container_width=True
        ):

            if not new_username or not new_password:

                st.warning(
                    "Please fill in all required fields."
                )

            elif new_password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            elif len(new_password) < 6:

                st.error(
                    "Password must contain at least 6 characters."
                )

            else:

                success, message = register_user(
                    new_username,
                    new_password
                )

                if success:

                    st.success(message)

                    st.info(
                        "You can now go to the Login tab "
                        "and sign in."
                    )

                else:

                    st.error(message)


# ============================================================
# LOGGED-IN APPLICATION
# ============================================================

else:

    # ========================================================
    # DASHBOARD
    # ========================================================

    if st.session_state.page == "dashboard":

        st.subheader(
            f"Welcome, {st.session_state.username} 👋"
        )

        st.markdown("---")

        st.subheader("🩺 Patient Assessment")

        st.write(
            "Create a new stroke risk assessment using "
            "patient health information and BEFAST symptoms."
        )

        if st.button(
            "🩺 New Assessment",
            use_container_width=True
        ):

            clear_prediction()

            st.session_state.page = "assessment"

            st.rerun()

        st.markdown("---")

        st.subheader("📋 Patient History")

        st.write(
            "View previous patient assessments and risk reports."
        )

        if st.button(
            "📋 View Patient History",
            use_container_width=True
        ):

            st.session_state.page = "history"

            st.rerun()

        st.markdown("---")

        if st.button(
            "🚪 Logout",
            use_container_width=True
        ):

            clear_prediction()

            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.page = "dashboard"

            st.rerun()


    # ========================================================
    # PATIENT ASSESSMENT
    # ========================================================

    elif st.session_state.page == "assessment":

        st.subheader("🩺 Patient Assessment")

        st.write(
            "Enter the patient's health information and "
            "BEFAST symptoms."
        )

        if st.button("⬅️ Back to Dashboard"):

            clear_prediction()

            st.session_state.page = "dashboard"

            st.rerun()

        st.markdown("---")

        # ====================================================
        # PATIENT INFORMATION
        # ====================================================

        st.subheader("👤 Patient Information")

        col1, col2 = st.columns(2)

        with col1:

            patient_name = st.text_input(
                "Patient Name *"
            )

            age = st.number_input(
                "Age *",
                min_value=1,
                max_value=120,
                value=25,
                step=1
            )

            gender = st.selectbox(
                "Gender *",
                [
                    "Male",
                    "Female",
                    "Other"
                ]
            )

            height = st.number_input(
                "Height (cm)",
                min_value=50.0,
                max_value=250.0,
                value=160.0,
                step=0.1
            )

            weight = st.number_input(
                "Weight (kg)",
                min_value=10.0,
                max_value=300.0,
                value=60.0,
                step=0.1
            )

        with col2:

            bmi = weight / ((height / 100) ** 2)

            st.metric(
                "Calculated BMI",
                f"{bmi:.2f}"
            )

            hypertension = st.selectbox(
                "Hypertension",
                ["No", "Yes"]
            )

            heart_disease = st.selectbox(
                "Heart Disease",
                ["No", "Yes"]
            )

            ever_married = st.selectbox(
                "Ever Married",
                ["No", "Yes"]
            )

            residence_type = st.selectbox(
                "Residence Type",
                ["Urban", "Rural"]
            )

        st.markdown("---")

        # ====================================================
        # CLINICAL INFORMATION
        # ====================================================

        st.subheader(
            "🏥 Clinical & Lifestyle Information"
        )

        col1, col2 = st.columns(2)

        with col1:

            work_type = st.selectbox(
                "Work Type",
                [
                    "Private",
                    "Self-employed",
                    "Govt_job",
                    "Children",
                    "Never_worked"
                ]
            )

            glucose_level = st.number_input(
                "Average Glucose Level (mg/dL)",
                min_value=50.0,
                max_value=500.0,
                value=100.0,
                step=0.1
            )

        with col2:

            smoking_status = st.selectbox(
                "Smoking Status",
                [
                    "Never smoked",
                    "Formerly smoked",
                    "Smokes",
                    "Unknown"
                ]
            )

        st.markdown("---")

        # ====================================================
        # BEFAST
        # ====================================================

        st.subheader(
            "🚨 BEFAST Stroke Warning Signs"
        )

        st.info(
            "Select YES if the patient is currently "
            "experiencing the corresponding symptom."
        )

        col1, col2 = st.columns(2)

        with col1:

            balance = st.checkbox(
                "🧍 B - Balance: Sudden loss of balance or coordination"
            )

            eyes = st.checkbox(
                "👁️ E - Eyes: Sudden vision problems"
            )

            face = st.checkbox(
                "🙂 F - Face: Facial drooping or uneven smile"
            )

        with col2:

            arm = st.checkbox(
                "💪 A - Arm: Sudden weakness or numbness in an arm"
            )

            speech = st.checkbox(
                "🗣️ S - Speech: Difficulty speaking or understanding"
            )

            time_symptom = st.selectbox(
                "⏰ T - Time: When did symptoms begin?",
                [
                    "No symptoms",
                    "Within the last few minutes",
                    "Within the last hour",
                    "More than 1 hour ago",
                    "Unknown"
                ]
            )

        befast_positive = any([
            balance,
            eyes,
            face,
            arm,
            speech
        ])

        st.session_state.befast_positive = befast_positive

        st.markdown("---")

        # ====================================================
        # PREDICT RISK
        # ====================================================

        if st.button(
            "🔮 Predict Risk",
            use_container_width=True
        ):

            if not patient_name.strip():

                st.warning(
                    "Please enter the patient name."
                )

            else:

                patient_data = pd.DataFrame([
                    {
                        "gender": gender,
                        "age": age,
                        "hypertension":
                            1 if hypertension == "Yes" else 0,
                        "heart_disease":
                            1 if heart_disease == "Yes" else 0,
                        "ever_married":
                            ever_married,
                        "work_type":
                            work_type,
                        "Residence_type":
                            residence_type,
                        "avg_glucose_level":
                            glucose_level,
                        "bmi":
                            bmi,
                        "smoking_status":
                            smoking_status
                    }
                ])

                # ============================================
                # MODEL PREDICTION
                # ============================================

                try:

                    probability = (
                        stroke_model
                        .predict_proba(
                            patient_data
                        )[0][1]
                    )

                except Exception as e:

                    st.error(
                        f"Model prediction error: {e}"
                    )

                    st.stop()

                # ============================================
                # ML SCORE
                # ============================================

                ml_score = probability * 100

                # ============================================
                # BEFAST SCORE
                # ============================================

                befast_count = sum([
                    balance,
                    eyes,
                    face,
                    arm,
                    speech
                ])

                befast_score = min(
                    befast_count * 10,
                    50
                )

                # ============================================
                # FINAL SCORE
                # ============================================

                final_score = min(
                    (ml_score * 0.70) +
                    (befast_score * 0.30),
                    100
                )

                # ============================================
                # RISK LEVEL
                # ============================================

                if final_score >= 60:

                    risk_level = "HIGH"

                    recommendation = (
                        "High stroke-risk screening result. "
                        "Medical evaluation is recommended."
                    )

                elif final_score >= 30:

                    risk_level = "MEDIUM"

                    recommendation = (
                        "Moderate stroke-risk screening result. "
                        "Consider medical evaluation and "
                        "lifestyle risk-factor management."
                    )

                else:

                    risk_level = "LOW"

                    recommendation = (
                        "Low stroke-risk screening result based "
                        "on the entered information. Continue "
                        "healthy lifestyle practices and "
                        "regular health checks."
                    )

                # ============================================
                # BEFAST EMERGENCY OVERRIDE
                # ============================================

                if befast_positive:

                    risk_level = "HIGH"

                    recommendation = (
                        "BEFAST warning signs detected. "
                        "Possible stroke symptoms require "
                        "immediate medical attention."
                    )

                # ============================================
                # STORE RESULT
                # ============================================

                st.session_state.prediction = risk_level
                st.session_state.risk_score = final_score
                st.session_state.ml_probability = probability
                st.session_state.recommendation = recommendation


        # ====================================================
        # DISPLAY RESULT
        # ====================================================

        if st.session_state.prediction is not None:

            risk_level = st.session_state.prediction

            final_score = st.session_state.risk_score

            recommendation = (
                st.session_state.recommendation
            )

            st.markdown("---")

            st.subheader(
                "📊 Stroke Risk Assessment Result"
            )

            st.metric(
                "Risk Score",
                f"{final_score:.1f}%"
            )

            if risk_level == "HIGH":

                st.error(
                    f"🔴 HIGH RISK\n\n"
                    f"Risk Score: {final_score:.1f}%"
                )

            elif risk_level == "MEDIUM":

                st.warning(
                    f"🟠 MEDIUM RISK\n\n"
                    f"Risk Score: {final_score:.1f}%"
                )

            else:

                st.success(
                    f"🟢 LOW RISK\n\n"
                    f"Risk Score: {final_score:.1f}%"
                )

            st.info(
                f"**Recommendation:** {recommendation}"
            )

            if befast_positive:

                st.error(
                    "🚨 BEFAST ALERT: One or more sudden "
                    "stroke warning signs are present. "
                    "This screening result is not a diagnosis. "
                    "Seek emergency medical attention immediately."
                )

            # =================================================
            # PREPARE PDF DATA
            # =================================================

            report_data = {

                "patient_name":
                    patient_name.strip(),

                "date":
                    datetime.now().strftime(
                        "%d-%b-%Y"
                    ),

                "age":
                    age,

                "gender":
                    gender,

                "height":
                    height,

                "weight":
                    weight,

                "bmi":
                    bmi,

                "hypertension":
                    hypertension,

                "heart_disease":
                    heart_disease,

                "ever_married":
                    ever_married,

                "residence_type":
                    residence_type,

                "work_type":
                    work_type,

                "glucose":
                    glucose_level,

                "smoking_status":
                    smoking_status,

                "balance":
                    balance,

                "eyes":
                    eyes,

                "face":
                    face,

                "arm":
                    arm,

                "speech":
                    speech,

                "time_symptom":
                    time_symptom,

                "risk_score":
                    final_score,

                "risk_level":
                    risk_level,

                "recommendation":
                    recommendation,

                "befast_positive":
                    befast_positive
            }

            # =================================================
            # DOWNLOAD PDF
            # =================================================

            pdf_file = create_pdf(
                report_data
            )

            st.download_button(
                label="📥 Download Assessment Report",
                data=pdf_file,
                file_name=(
                    f"{patient_name.strip()}_"
                    "Stroke_Risk_Assessment.pdf"
                ),
                mime="application/pdf",
                use_container_width=True
            )

            # =================================================
            # SAVE ASSESSMENT
            # =================================================

            if st.button(
                "💾 Save Patient Assessment",
                use_container_width=True
            ):

                try:

                    saved_id = save_assessment(

                        username=
                            st.session_state.username,

                        patient_name=
                            patient_name.strip(),

                        age=
                            age,

                        gender=
                            gender,

                        hypertension=
                            1 if hypertension == "Yes" else 0,

                        heart_disease=
                            1 if heart_disease == "Yes" else 0,

                        ever_married=
                            ever_married,

                        residence_type=
                            residence_type,

                        avg_glucose_level=
                            glucose_level,

                        bmi=
                            round(bmi, 2),

                        smoking_status=
                            smoking_status,

                        work_type=
                            work_type,

                        height=
                            height,

                        weight=
                            weight,

                        balance=
                            int(balance),

                        eyes=
                            int(eyes),

                        face=
                            int(face),

                        arm=
                            int(arm),

                        speech=
                            int(speech),

                        time_symptom=
                            time_symptom,

                        risk_score=
                            float(final_score),

                        ml_probability=
                            float(
                                st.session_state.ml_probability
                            ),

                        risk_level=
                            risk_level,

                        recommendation=
                            recommendation
                    )

                    st.success(
                        "✅ Patient assessment saved successfully!"
                    )

                    clear_prediction()

                    st.session_state.page = "dashboard"

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Error saving assessment: {e}"
                    )


    # ========================================================
    # PATIENT HISTORY
    # ========================================================

    elif st.session_state.page == "history":

        st.subheader("📋 Patient History")

        st.write(
            "Previous patient assessments."
        )

        # ----------------------------------------------------
        # BACK TO DASHBOARD
        # ----------------------------------------------------

        if st.button("⬅️ Back to Dashboard"):

            st.session_state.page = "dashboard"

            st.rerun()

        st.markdown("---")

        try:

            # ------------------------------------------------
            # GET HISTORY FROM DATABASE
            # ------------------------------------------------

            history = get_patient_history(
                st.session_state.username
            )

            if history:

                history_data = []

                # ------------------------------------------------
                # PREPARE TABLE DATA
                # ------------------------------------------------

                for index, record in enumerate(
                    history,
                    start=1
                ):

                    # ------------------------------------------------
                    # PATIENT NAME
                    # ------------------------------------------------

                    patient_name_value = record.get(
                        "patient_name",
                        ""
                    )

                    # ------------------------------------------------
                    # AGE
                    # ------------------------------------------------

                    age_value = record.get(
                        "age",
                        ""
                    )

                    # ------------------------------------------------
                    # GENDER
                    # ------------------------------------------------

                    gender_value = record.get(
                        "gender",
                        ""
                    )

                    # ------------------------------------------------
                    # RISK SCORE
                    # ------------------------------------------------

                    risk_value = record.get(
                        "final_risk_score"
                    )

                    if risk_value is None:

                        risk_value = record.get(
                            "risk_score",
                            0
                        )

                    try:

                        risk_value = float(
                            risk_value
                        )

                    except:

                        risk_value = 0.0

                    # ------------------------------------------------
                    # RISK LEVEL
                    # ------------------------------------------------

                    risk_level_value = str(
                        record.get(
                            "risk_level",
                            "LOW"
                        )
                    ).upper()

                    # ------------------------------------------------
                    # DATE
                    # ------------------------------------------------

                    date_value = str(
                        record.get(
                            "assessment_date",
                            ""
                        )
                    )

                    # ------------------------------------------------
                    # TIME
                    # ------------------------------------------------

                    time_value = str(
                        record.get(
                            "assessment_time",
                            ""
                        )
                    )

                    # ------------------------------------------------
                    # FORMAT DATE
                    # ------------------------------------------------

                    formatted_date = date_value

                    try:

                        formatted_date = datetime.strptime(
                            date_value,
                            "%Y-%m-%d"
                        ).strftime(
                            "%d-%b-%Y"
                        )

                    except:

                        pass

                    # ------------------------------------------------
                    # FORMAT TIME
                    # ------------------------------------------------

                    formatted_time = time_value

                    if formatted_time:

                        formatted_time = formatted_time[:5]

                    # ------------------------------------------------
                    # DATE + TIME
                    # ------------------------------------------------

                    if formatted_date and formatted_time:

                        date_time_value = (
                            f"{formatted_date} "
                            f"{formatted_time}"
                        )

                    elif formatted_date:

                        date_time_value = formatted_date

                    else:

                        date_time_value = formatted_time

                    # ------------------------------------------------
                    # ADD ROW
                    # ------------------------------------------------

                    history_data.append({

                        "S.No":
                            index,

                        "Name":
                            patient_name_value,

                        "Age":
                            age_value,

                        "Risk %":
                            f"{risk_value:.1f}%",

                        "Gender":
                            gender_value,

                        "Status":
                            risk_level_value,

                        "Date & Time":
                            date_time_value
                    })

                # ------------------------------------------------
                # CREATE DATAFRAME
                # ------------------------------------------------

                history_df = pd.DataFrame(
                    history_data,
                    columns=[
                        "S.No",
                        "Name",
                        "Age",
                        "Risk %",
                        "Gender",
                        "Status",
                        "Date & Time"
                    ]
                )

                # ------------------------------------------------
                # DISPLAY HISTORY TABLE
                # ------------------------------------------------

                st.dataframe(
                    history_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={

                        "S.No":
                            st.column_config.NumberColumn(
                                "S.No",
                                width="small"
                            ),

                        "Name":
                            st.column_config.TextColumn(
                                "Name",
                                width="medium"
                            ),

                        "Age":
                            st.column_config.NumberColumn(
                                "Age",
                                width="small"
                            ),

                        "Risk %":
                            st.column_config.TextColumn(
                                "Risk %",
                                width="small"
                            ),

                        "Gender":
                            st.column_config.TextColumn(
                                "Gender",
                                width="small"
                            ),

                        "Status":
                            st.column_config.TextColumn(
                                "Status",
                                width="small"
                            ),

                        "Date & Time":
                            st.column_config.TextColumn(
                                "Date & Time",
                                width="medium"
                            )
                    }
                )

            else:

                st.info(
                    "No previous patient assessments found."
                )

        except Exception as e:

            st.error(
                f"Error loading patient history: {e}"
            )