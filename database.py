import sqlite3
import os
import hashlib
from datetime import datetime


# ============================================================
# DATABASE PATH
# ============================================================

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "stroke_cds.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# ============================================================
# USERS TABLE
# ============================================================

def ensure_users_table():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# ASSESSMENTS TABLE
# ============================================================

def ensure_assessment_columns():

    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Create basic table if it does not exist
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    conn.commit()

    # --------------------------------------------------------
    # Get existing columns
    # --------------------------------------------------------

    cursor.execute("PRAGMA table_info(assessments)")

    existing_columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    # --------------------------------------------------------
    # ALL REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = {

        # ====================================================
        # USER
        # ====================================================

        "username": "TEXT",

        # ====================================================
        # PATIENT INFORMATION
        # ====================================================

        "patient_name": "TEXT",
        "age": "INTEGER",
        "gender": "TEXT",

        # ====================================================
        # PHYSICAL INFORMATION
        # ====================================================

        "height": "REAL",
        "weight": "REAL",
        "bmi": "REAL",

        # ====================================================
        # MEDICAL INFORMATION
        # ====================================================

        "hypertension": "INTEGER DEFAULT 0",
        "heart_disease": "INTEGER DEFAULT 0",
        "ever_married": "TEXT",
        "residence_type": "TEXT",
        "work_type": "TEXT",

        # ====================================================
        # GLUCOSE
        # ====================================================

        "avg_glucose_level": "REAL",
        "glucose_level": "REAL",

        # ====================================================
        # SMOKING
        # ====================================================

        "smoking_status": "TEXT",

        # ====================================================
        # BEFAST
        # ====================================================

        "balance": "INTEGER DEFAULT 0",
        "eyes": "INTEGER DEFAULT 0",
        "face": "INTEGER DEFAULT 0",
        "arm": "INTEGER DEFAULT 0",
        "speech": "INTEGER DEFAULT 0",
        "time_symptom": "TEXT",

        # ====================================================
        # OLD / COMPATIBILITY BEFAST COLUMNS
        # ====================================================

        "balance_difficulty": "INTEGER DEFAULT 0",
        "vision_problems": "INTEGER DEFAULT 0",
        "face_drooping": "INTEGER DEFAULT 0",
        "arm_weakness": "INTEGER DEFAULT 0",
        "speech_difficulty": "INTEGER DEFAULT 0",
        "severe_headache": "INTEGER DEFAULT 0",

        # ====================================================
        # PREDICTION RESULTS
        # ====================================================

        "risk_score": "REAL",
        "ml_probability": "REAL",
        "final_risk_score": "REAL",
        "risk_level": "TEXT",
        "recommendation": "TEXT",

        # ====================================================
        # DATE / TIME
        # ====================================================

        "assessment_date": "TEXT",
        "assessment_time": "TEXT",
        "created_at": "TEXT"
    }

    # --------------------------------------------------------
    # ADD EVERY MISSING COLUMN
    # --------------------------------------------------------

    for column_name, column_type in required_columns.items():

        if column_name not in existing_columns:

            try:

                cursor.execute(
                    f"""
                    ALTER TABLE assessments
                    ADD COLUMN {column_name} {column_type}
                    """
                )

            except sqlite3.OperationalError:
                pass

    conn.commit()

    # --------------------------------------------------------
    # REFRESH COLUMN LIST
    # --------------------------------------------------------

    cursor.execute("PRAGMA table_info(assessments)")

    existing_columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    # ========================================================
    # SYNCHRONIZE GLUCOSE COLUMNS
    # ========================================================

    if (
        "glucose_level" in existing_columns
        and "avg_glucose_level" in existing_columns
    ):

        try:

            cursor.execute("""
                UPDATE assessments
                SET glucose_level = avg_glucose_level
                WHERE glucose_level IS NULL
                AND avg_glucose_level IS NOT NULL
            """)

            cursor.execute("""
                UPDATE assessments
                SET avg_glucose_level = glucose_level
                WHERE avg_glucose_level IS NULL
                AND glucose_level IS NOT NULL
            """)

        except sqlite3.OperationalError:
            pass

    # ========================================================
    # SYNCHRONIZE FINAL RISK SCORE
    # ========================================================

    try:

        cursor.execute("""
            UPDATE assessments
            SET final_risk_score = risk_score
            WHERE final_risk_score IS NULL
            AND risk_score IS NOT NULL
        """)

    except sqlite3.OperationalError:
        pass

    # ========================================================
    # CREATE / UPDATE OLD RISK SCORE FROM ML PROBABILITY
    # ========================================================

    try:

        cursor.execute("""
            UPDATE assessments
            SET risk_score = ml_probability * 100
            WHERE risk_score IS NULL
            AND ml_probability IS NOT NULL
        """)

    except sqlite3.OperationalError:
        pass

    # ========================================================
    # SYNCHRONIZE BEFAST COLUMNS
    # ========================================================

    try:

        cursor.execute("""
            UPDATE assessments
            SET balance_difficulty = balance
            WHERE balance_difficulty IS NULL
            AND balance IS NOT NULL
        """)

        cursor.execute("""
            UPDATE assessments
            SET vision_problems = eyes
            WHERE vision_problems IS NULL
            AND eyes IS NOT NULL
        """)

        cursor.execute("""
            UPDATE assessments
            SET face_drooping = face
            WHERE face_drooping IS NULL
            AND face IS NOT NULL
        """)

        cursor.execute("""
            UPDATE assessments
            SET arm_weakness = arm
            WHERE arm_weakness IS NULL
            AND arm IS NOT NULL
        """)

        cursor.execute("""
            UPDATE assessments
            SET speech_difficulty = speech
            WHERE speech_difficulty IS NULL
            AND speech IS NOT NULL
        """)

    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    ensure_users_table()
    ensure_assessment_columns()


# ============================================================
# REGISTER USER
# ============================================================

def register_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        hashed_password = hash_password(password)

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                password,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                username,
                hashed_password,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()

        return True, "Account created successfully."

    except sqlite3.IntegrityError:

        return False, "Username already exists."

    except Exception as e:

        return False, str(e)

    finally:

        conn.close()


# ============================================================
# AUTHENTICATE USER
# ============================================================

def authenticate_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        hashed_password = hash_password(password)

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            AND password = ?
            """,
            (
                username,
                hashed_password
            )
        )

        user = cursor.fetchone()

        if user:
            return dict(user)

        return None

    finally:

        conn.close()


# ============================================================
# CHECK USER EXISTS
# ============================================================

def user_exists(username):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        result = cursor.fetchone()

        return result is not None

    finally:

        conn.close()


# ============================================================
# SAVE PATIENT ASSESSMENT
# ============================================================

def save_assessment(
    username=None,
    patient_name=None,
    age=None,
    gender=None,
    hypertension=0,
    heart_disease=0,
    ever_married="",
    residence_type="",
    avg_glucose_level=0,
    glucose_level=None,
    bmi=0,
    smoking_status="",
    work_type="",
    height=0,
    weight=0,

    # BEFAST
    balance=0,
    eyes=0,
    face=0,
    arm=0,
    speech=0,
    time_symptom="",

    # Compatibility BEFAST fields
    face_drooping=0,
    arm_weakness=0,
    speech_difficulty=0,
    vision_problems=0,
    balance_difficulty=0,
    severe_headache=0,

    # Prediction
    risk_score=0,
    ml_probability=0,
    final_risk_score=None,
    risk_level="",
    recommendation=""
):

    # --------------------------------------------------------
    # Make sure database is repaired
    # --------------------------------------------------------

    ensure_assessment_columns()

    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()

    assessment_date = now.strftime(
        "%Y-%m-%d"
    )

    assessment_time = now.strftime(
        "%H:%M:%S"
    )

    created_at = now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # ========================================================
    # GLUCOSE COMPATIBILITY
    # ========================================================

    if glucose_level is None:

        glucose_level = avg_glucose_level

    else:

        avg_glucose_level = glucose_level

    # ========================================================
    # FINAL SCORE COMPATIBILITY
    # ========================================================

    if final_risk_score is None:

        final_risk_score = risk_score

    # ========================================================
    # BEFAST COMPATIBILITY
    # ========================================================

    face_drooping = int(
        bool(face_drooping) or bool(face)
    )

    arm_weakness = int(
        bool(arm_weakness) or bool(arm)
    )

    speech_difficulty = int(
        bool(speech_difficulty) or bool(speech)
    )

    vision_problems = int(
        bool(vision_problems) or bool(eyes)
    )

    balance_difficulty = int(
        bool(balance_difficulty) or bool(balance)
    )

    # ========================================================
    # INSERT ASSESSMENT
    # ========================================================

    try:

        cursor.execute(
            """
            INSERT INTO assessments
            (
                username,
                patient_name,
                age,
                gender,

                height,
                weight,
                bmi,

                hypertension,
                heart_disease,
                ever_married,
                residence_type,
                work_type,

                avg_glucose_level,
                glucose_level,
                smoking_status,

                balance,
                eyes,
                face,
                arm,
                speech,
                time_symptom,

                balance_difficulty,
                vision_problems,
                face_drooping,
                arm_weakness,
                speech_difficulty,
                severe_headache,

                risk_score,
                ml_probability,
                final_risk_score,
                risk_level,
                recommendation,

                assessment_date,
                assessment_time,
                created_at
            )
            VALUES
            (
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            """,
            (
                username,
                patient_name,
                age,
                gender,

                height,
                weight,
                bmi,

                hypertension,
                heart_disease,
                ever_married,
                residence_type,
                work_type,

                avg_glucose_level,
                glucose_level,
                smoking_status,

                int(balance),
                int(eyes),
                int(face),
                int(arm),
                int(speech),
                time_symptom,

                balance_difficulty,
                vision_problems,
                face_drooping,
                arm_weakness,
                speech_difficulty,
                int(severe_headache),

                risk_score,
                ml_probability,
                final_risk_score,
                risk_level,
                recommendation,

                assessment_date,
                assessment_time,
                created_at
            )
        )

        conn.commit()

        return cursor.lastrowid

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        conn.close()


# ============================================================
# GET PATIENT HISTORY
# ============================================================

def get_patient_history(username=None):

    ensure_assessment_columns()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        if username:

            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    patient_name,
                    age,
                    gender,
                    final_risk_score,
                    risk_score,
                    ml_probability,
                    risk_level,
                    recommendation,
                    assessment_date,
                    assessment_time,
                    created_at
                FROM assessments
                WHERE username = ?
                ORDER BY id DESC
                """,
                (username,)
            )

        else:

            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    patient_name,
                    age,
                    gender,
                    final_risk_score,
                    risk_score,
                    ml_probability,
                    risk_level,
                    recommendation,
                    assessment_date,
                    assessment_time,
                    created_at
                FROM assessments
                ORDER BY id DESC
                """
            )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# GET ALL ASSESSMENTS
# ============================================================

def get_all_assessments():

    ensure_assessment_columns()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT *
            FROM assessments
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# GET ONE ASSESSMENT
# ============================================================

def get_assessment(assessment_id):

    ensure_assessment_columns()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT *
            FROM assessments
            WHERE id = ?
            """,
            (assessment_id,)
        )

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

    finally:

        conn.close()


# ============================================================
# DELETE ONE ASSESSMENT
# ============================================================

def delete_assessment(assessment_id):

    ensure_assessment_columns()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM assessments
            WHERE id = ?
            """,
            (assessment_id,)
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:

        conn.close()


# ============================================================
# GET ASSESSMENTS BY PATIENT NAME
# ============================================================

def get_assessments_by_patient_name(patient_name):

    ensure_assessment_columns()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT *
            FROM assessments
            WHERE patient_name = ?
            ORDER BY id DESC
            """,
            (patient_name,)
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ============================================================
# REPAIR DATABASE
# ============================================================

def repair_database():

    """
    Repairs the existing stroke_cds.db database
    without deleting existing records.
    """

    print("Checking database...")

    initialize_database()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "PRAGMA table_info(assessments)"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    conn.close()

    print("Database repair completed.")
    print()
    print("Assessment table columns:")

    for column in columns:
        print(" -", column)


# ============================================================
# AUTOMATIC DATABASE INITIALIZATION
# ============================================================

initialize_database()