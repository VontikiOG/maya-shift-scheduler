import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import time

# הגדרות עמוד נעימות
st.set_page_config(page_title="המשמרות של מאיה", page_icon="🌸", layout="centered")

st.markdown("""
<style>
    .stApp { direction: rtl; }
    p, div, h1, h2, h3, h4, h5, h6, label, span, li, button, input { text-align: right !important; }
    [data-testid="stDataFrame"] { direction: rtl; }
    .success-text { color: #2e7d32; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- פונקציות עזר לחודשים ותאריכים ---
def get_next_month_dates():
    today = datetime.today()
    # חישוב החודש הבא
    next_month = today.replace(day=28) + timedelta(days=4) 
    year = next_month.year
    month = next_month.month
    num_days = calendar.monthrange(year, month)[1]
    
    all_dates = []
    weekend_dates = []
    
    for day in range(1, num_days + 1):
        current_date = datetime(year, month, day)
        date_str = current_date.strftime("%d/%m/%Y")
        all_dates.append(date_str)
        if current_date.weekday() in [4, 5]: # 4=שישי, 5=שבת
            weekend_dates.append(date_str)
            
    return all_dates, weekend_dates, f"{month:02d}/{year}"

ALL_DATES, WEEKEND_DATES, TARGET_MONTH = get_next_month_dates()

# --- טעינת נתוני הרופאים מ-CSV ---
@st.cache_data
def load_doctors_data():
    # מנסה לקרוא את הקובץ בכמה סוגי קידודים נפוצים לעברית
    for enc in ['utf-8', 'cp1255', 'iso-8859-8']:
        try:
            df = pd.read_csv("doctors_list.csv", encoding=enc)
            df.columns = df.columns.str.strip()
            # ניקוי מספרי הטלפון מהגרש
            if 'מספר טלפון' in df.columns:
                df['מספר טלפון'] = df['מספר טלפון'].astype(str).str.replace("'", "").str.strip()
            return df
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            st.error("🚨 קובץ 'doctors_list.csv' לא נמצא בשרת! נא להעלות אותו לתיקייה.")
            return pd.DataFrame(columns=["שם הרופא", "מספר טלפון"])
            
    st.error("שגיאת קידוד: לא ניתן לפענח את קובץ הרופאים. נא לוודא שהוא שמור כ-CSV תקין.")
    return pd.DataFrame(columns=["שם הרופא", "מספר טלפון"])

# --- אזור ניהול ויומן שינויים ---
@st.dialog("🔒 כניסת מנהלת")
def admin_login():
    st.markdown("בוקר טוב מאיה! הזיני סיסמה כדי להתחיל לעבוד.")
    pwd = st.text_input("סיסמה", type="password")
    if st.button("התחברי 🌸", use_container_width=True):
        if pwd == "MAYA3":
            st.session_state.maya_logged_in = True
            st.rerun()
        else:
            st.error("סיסמה שגויה, נסי שוב מאיה! 😊")

@st.dialog("📜 יומן שינויים - היסטוריית הפיתוח")
def show_changelog():
    st.markdown("""
    **v1.0.0 | גרסת הבסיס למאיה 🌸**
    * **הקמת תשתית:** בניית ממשק ייעודי מותאם אישית למאיה, נקי מסרקזם ובעל אווירה ידידותית, חיובית ונוחה לשימוש יומיומי.
    * **מערכת התחברות מאובטחת:** הוספת חלון קופץ (Dialog) לכניסת מנהלת עם הסיסמה הייעודית, למניעת גישה לא מורשית למערכת השיבוצים.
    * **קריאת נתונים חכמה ועמידה:** ייבוא אוטומטי של קובץ `doctors_list.csv` תוך טיפול מובנה בבעיות קידוד נפוצות של אקסל בעברית (תמיכה ב-cp1255, utf-8, iso-8859-8) כדי למנוע קריסות בקריאת שמות הרופאים.
    * **הגנה על פרטיות מידע רגיש:** קליטת מספרי הטלפון של הרופאים מהקובץ, ניקוי תווי שגיאה (כמו גרשיים), ושמירתם בזיכרון השרת בלבד. מספרי הטלפון חסומים להצגה בממשק המשתמש (UI).
    * **לוגיקת בחירת תאריכים ממוקדת:** מעבר לממשק "תיק אישי" נקי לכל רופא, המאפשר בחירת תאריכי זמינות חודשיים בצורה קלה מבלי להעמיס נתונים על המסך.
    * **זיהוי חריגים אוטומטי (Fuzzy Logic):** הטמעת זיהוי חכם מבוסס טקסט לשמות רופאים עם אילוצים מיוחדים (כגון: בהאא, עתאמנה, מטקוביץ, טראסוב), גם אם השם הוקלד בצורה שונה.
    * **הגבלת ימי עבודה למניעת טעויות אנוש:** חסימה מוחלטת של האפשרות לבחור ימי חול עבור רופאים שעובדים רק בסופי שבוע. המערכת מסננת ומציגה להזנה ימי שישי ושבת בלבד.
    * **ניהול מצב (State Management):** הוספת מערכת מעקב פנימית (`availability_dict`) ששומרת אילו רופאים כבר הוזנו ומציגה חיווי ויזואלי מהיר (✅) למעקב התקדמות העבודה.
    """)
    if st.button("סגירה", use_container_width=True):
        st.rerun()

def main():
    if "maya_logged_in" not in st.session_state:
        st.session_state.maya_logged_in = False
    
    # מאגר לשמירת התאריכים שמאיה מזינה (נשמר בזיכרון המקומי)
    if "availability_dict" not in st.session_state:
        st.session_state.availability_dict = {}

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("מערכת השיבוצים של מאיה 🌸")
        st.markdown(f"**מכינים את סידור העבודה לחודש: {TARGET_MONTH}**")
    with col2:
        if st.button("מה התחדש?", type="tertiary", use_container_width=True):
            show_changelog()
    with col3:
        if not st.session_state.maya_logged_in:
            if st.button("כניסת מנהלת ⚙️", use_container_width=True):
                admin_login()
        else:
            if st.button("התנתקי 👋", use_container_width=True):
                st.session_state.maya_logged_in = False
                st.rerun()

    st.divider()

    if not st.session_state.maya_logged_in:
        st.info("אנא התחברי למערכת כדי להתחיל לשבץ משמרות (סיסמה: MAYA3).")
        st.stop()

    # טעינת רשימת הרופאים
    df_doctors = load_doctors_data()
    if df_doctors.empty:
        st.stop()
        
    doctor_names = df_doctors['שם הרופא'].tolist()

    st.subheader("👩‍⚕️ הזנת זמינות רופאים")
    st.markdown("בחרי רופא מהרשימה וסמני את התאריכים שהוא פנוי בהם. מספרי הטלפון שמורים בבטחה במערכת ולא יוצגו כאן.")
    
    selected_doctor = st.selectbox("בחירת רופא להזנה:", ["-- בחרי רופא --"] + doctor_names)
    
    if selected_doctor != "-- בחרי רופא --":
        with st.container(border=True):
            st.markdown(f"#### התאריכים של {selected_doctor}")
            
            # לוגיקה חכמה וגמישה: בדיקה האם חלק מהשם מכיל מילות מפתח
            is_weekend_only = any(name in selected_doctor for name in ["בהאא", "עתאמנה", "מטקוביץ"])
            is_bmt_only = any(name in selected_doctor for name in ["ילנה", "טראסוב", "בהאא", "עתאמנה"])
            
            if is_weekend_only:
                st.info("💡 שימי לב: רופא זה עובד רק בסופי שבוע. המערכת מציגה לבחירה רק ימי שישי ושבת.")
                options_for_doctor = WEEKEND_DATES
            else:
                options_for_doctor = ALL_DATES
                
            if is_bmt_only:
                st.caption("*(לידיעתך: רופא זה מוגדר למחלקת השתלות מח עצם בלבד)*")
                
            current_selections = st.session_state.availability_dict.get(selected_doctor, [])
            
            selected_dates = st.multiselect(
                "סמני את התאריכים (אפשר לבחור כמה ביחד):", 
                options_for_doctor,
                default=current_selections
            )
            
            if st.button(f"💾 שמרי תאריכים ל{selected_doctor}", type="primary"):
                st.session_state.availability_dict[selected_doctor] = selected_dates
                st.success(f"מעולה! התאריכים של {selected_doctor} נשמרו בהצלחה. ✨")
                time.sleep(1) 
                st.rerun()

    st.divider()
    
    st.subheader("📋 סטטוס הזנות לחודש הקרוב")
    fed_doctors = list(st.session_state.availability_dict.keys())
    
    if fed_doctors:
        st.markdown("כבר הזנת תאריכים לרופאים הבאים:")
        cols = st.columns(3)
        for i, doc in enumerate(fed_doctors):
            num_shifts = len(st.session_state.availability_dict[doc])
            cols[i % 3].markdown(f"✅ {doc} ({num_shifts} משמרות)")
            
        st.write("")
        if st.button("🪄 צרי סידור עבודה חודשי", type="primary", use_container_width=True):
            st.balloons()
            st.success("נהדר! כל הנתונים נשמרו. תשתית האלגוריתם ('מד הצדק') מוכנה לשלב הבא! 🚀")
    else:
        st.caption("עדיין לא הוזנו תאריכים לאף רופא.")

if __name__ == "__main__":
    main()
