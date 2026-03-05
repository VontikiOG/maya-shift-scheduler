import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
import calendar

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
    try:
        # כאן המערכת תקרא את קובץ ה-CSV שתעלה
        df = pd.read_csv("doctors.csv")
        return df
    except FileNotFoundError:
        # נתונים זמניים למקרה שהקובץ טרם הועלה (רק לצורך תצוגה)
        return pd.DataFrame({
            "שם רופא": ["בהאא עתאמנה", "מטקוביץ אליעזר", "ילנמה טראסוב", "רופא רגיל א'", "רופא רגיל ב'"],
            "טלפון": ["0500000001", "0500000002", "0500000003", "0500000004", "0500000005"]
        })

# --- אזור ניהול ---
@st.dialog("🔒 כניסת מנהלת")
def admin_login():
    st.markdown("בוקר טוב! הזיני סיסמה כדי להתחיל לעבוד.")
    pwd = st.text_input("סיסמה", type="password")
    if st.button("התחברי 🌸", use_container_width=True):
        if pwd == "MAYA3":
            st.session_state.maya_logged_in = True
            st.rerun()
        else:
            st.error("סיסמה שגויה, נסי שוב מאיה! 😊")

def main():
    if "maya_logged_in" not in st.session_state:
        st.session_state.maya_logged_in = False
    
    # מאגר לשמירת התאריכים שמאיה מזינה
    if "availability_dict" not in st.session_state:
        st.session_state.availability_dict = {}

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("מערכת השיבוצים של מאיה 🌸")
        st.markdown(f"**מכינים את סידור העבודה לחודש: {TARGET_MONTH}**")
    with col2:
        if not st.session_state.maya_logged_in:
            if st.button("כניסת מנהלת ⚙️"):
                admin_login()
        else:
            if st.button("התנתקי 👋"):
                st.session_state.maya_logged_in = False
                st.rerun()

    st.divider()

    if not st.session_state.maya_logged_in:
        st.info("אנא התחברי למערכת כדי להתחיל לשבץ משמרות.")
        st.stop()

    # טעינת רשימת הרופאים
    df_doctors = load_doctors_data()
    doctor_names = df_doctors['שם רופא'].tolist()

    st.subheader("👩‍⚕️ הזנת זמינות רופאים")
    st.markdown("בחרי רופא מהרשימה וסמני את התאריכים שהוא פנוי בהם.")
    
    # שלב 1: בחירת רופא (אופציה 1 - תיק אישי)
    selected_doctor = st.selectbox("בחירת רופא להזנה:", ["-- בחרי רופא --"] + doctor_names)
    
    if selected_doctor != "-- בחרי רופא --":
        with st.container(border=True):
            st.markdown(f"#### התאריכים של {selected_doctor}")
            
            # לוגיקה חכמה: חסימת ימי חול למי שעובד רק סופ"ש
            if selected_doctor in ["בהאא עתאמנה", "מטקוביץ אליעזר"]:
                st.info("💡 שימי לב: רופא זה עובד רק בסופי שבוע. המערכת מציגה רק ימי שישי ושבת.")
                options_for_doctor = WEEKEND_DATES
            else:
                options_for_doctor = ALL_DATES
                
            # שליפת נתונים קיימים אם מאיה כבר הזינה בעבר
            current_selections = st.session_state.availability_dict.get(selected_doctor, [])
            
            # בחירת התאריכים (Multi-select נוח)
            selected_dates = st.multiselect(
                "סמני את התאריכים (אפשר לבחור כמה ביחד):", 
                options_for_doctor,
                default=current_selections
            )
            
            if st.button(f"💾 שמרי תאריכים ל{selected_doctor}", type="primary"):
                st.session_state.availability_dict[selected_doctor] = selected_dates
                st.success(f"מעולה! התאריכים של {selected_doctor} נשמרו בהצלחה. ✨")
                time.sleep(1) # השהייה קלה לחוויה חלקה
                st.rerun()

    st.divider()
    
    # שלב 2: מעקב - מי כבר הוזן?
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
            st.success("האלגוריתם (שנבנה בהמשך) ירוץ עכשיו על הנתונים שהזנת! 🚀")
            # כאן יכנס בעתיד קוד השיבוץ (מד הצדק)
    else:
        st.caption("עדיין לא הוזנו תאריכים לאף רופא.")

if __name__ == "__main__":
    import time # הוספת time להשהייה חלקה
    main()
