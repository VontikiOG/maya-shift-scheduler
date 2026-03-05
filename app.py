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

def is_weekend(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").weekday() in [4, 5]
    except:
        return False

# --- טעינת נתוני הרופאים מ-CSV ---
@st.cache_data
def load_doctors_data():
    for enc in ['utf-8', 'cp1255', 'iso-8859-8']:
        try:
            df = pd.read_csv("doctors_list.csv", encoding=enc)
            df.columns = df.columns.str.strip()
            if 'מספר טלפון' in df.columns:
                df['מספר טלפון'] = df['מספר טלפון'].astype(str).str.replace("'", "").str.strip()
            return df
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            return pd.DataFrame(columns=["שם הרופא", "מספר טלפון"])
    return pd.DataFrame(columns=["שם הרופא", "מספר טלפון"])

# --- אלגוריתם "מד הצדק" (שיטת השחיקה) ---
def generate_fair_schedule(availability_dict):
    # מציאת כל התאריכים הייחודיים שהוזנו
    all_dates = set()
    for dates in availability_dict.values():
        all_dates.update(dates)
    
    # מיון התאריכים כרונולוגית
    sorted_dates = sorted(list(all_dates), key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
    
    # אתחול נקודות שחיקה (כולם מתחילים מאפס)
    burnout_scores = {doc: 0 for doc in availability_dict.keys()}
    schedule = []
    
    # מילות מפתח לזיהוי רופאי השתלות בלבד
    bmt_keywords = ["ילנה", "טראסוב", "בהאא", "עתאמנה"]
    
    for date_str in sorted_dates:
        is_we = is_weekend(date_str)
        available_today = [doc for doc, dates in availability_dict.items() if date_str in dates]
        
        if not available_today:
            schedule.append({
                "תאריך": date_str, "סוג יום": "סופ״ש 🌴" if is_we else "אמצע שבוע ☀️",
                "המטואונקולוגיה": "חסר רופא 🚨", "השתלות מח עצם": "חסר רופא 🚨"
            })
            continue
            
        # חלוקה לקבוצות
        bmt_only_docs = [d for d in available_today if any(k in d for k in bmt_keywords)]
        regular_docs = [d for d in available_today if d not in bmt_only_docs]
        
        bmt_doc = None
        hemato_doc = None
        
        # 1. קודם כל דואגים להשתלות אם יש רופא שיכול לעשות רק את זה
        if bmt_only_docs:
            bmt_doc = min(bmt_only_docs, key=lambda d: burnout_scores[d])
            
        # 2. שיבוץ המטואונקולוגיה (הכי חשוב!) - ניתן לרופא הרגיל עם *הכי מעט* שחיקה
        if regular_docs:
            hemato_doc = min(regular_docs, key=lambda d: burnout_scores[d])
            regular_docs.remove(hemato_doc) # יורד מהרשימה להיום
            
        # 3. אם אין רופא השתלות ייעודי ויש עוד רופאים רגילים, ניתן את ההשתלות כפרס לזה עם *הכי הרבה* שחיקה
        if not bmt_doc and regular_docs:
            bmt_doc = max(regular_docs, key=lambda d: burnout_scores[d])
            
        # עדכון השחיקה
        if bmt_doc: burnout_scores[bmt_doc] += 1
        if hemato_doc: burnout_scores[hemato_doc] += 2
        
        schedule.append({
            "תאריך": date_str,
            "סוג יום": "סופ״ש 🌴" if is_we else "אמצע שבוע ☀️",
            "המטואונקולוגיה": hemato_doc if hemato_doc else "חסר רופא 🚨",
            "השתלות מח עצם": bmt_doc if bmt_doc else "חסר רופא 🚨"
        })
        
    return pd.DataFrame(schedule), burnout_scores

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
    **v1.1.0 | גרסת "מד הצדק" ⚖️**
    * **הסרת ססמאות:** מחיקת הסיסמה הגלויה מעמוד הבית לטובת אבטחת מידע.
    * **אלגוריתם שחיקה (Burnout):** פיתוח אלגוריתם שיבוץ חכם המחלק "נקודות שחיקה" (המטו=2, השתלות=1) כדי לדאוג לאיזון עומסים הוגן בין חברי הצוות.
    * **תעדוף חריגים:** בניית מנגנון שמשריין אוטומטית משמרות השתלות לרופאים המורשים למחלקה זו בלבד (ילנה, בהאא), ואת שאריות משמרות ההשתלות מחלק כ"פרס" לרופאים שנטחנו בהמטו.
    * **לוח בקרה למאיה:** הוספת תצוגת טבלת הוגנות חודשית למנהלת, כדי שתוכל לראות בדיוק כמה נקודות צבר כל רופא ולהסביר את השיבוץ לצוות.

    **v1.0.0 | גרסת הבסיס למאיה 🌸**
    * הקמת תשתית ידידותית, קריאת CSV מאובטחת ללא הצגת טלפונים, לוגיקת סופי שבוע אוטומטית לרופאים רלוונטיים (מטקוביץ, בהאא).
    """)
    if st.button("סגירה", use_container_width=True):
        st.rerun()

def main():
    if "maya_logged_in" not in st.session_state:
        st.session_state.maya_logged_in = False
    
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
        # הסיסמה הוסרה לחלוטין מכאן!
        st.info("אנא התחברי למערכת כדי להתחיל לשבץ משמרות.")
        st.stop()

    df_doctors = load_doctors_data()
    if df_doctors.empty:
        st.warning("⚠️ הקובץ doctors_list.csv חסר. אנא העלי אותו לשרת הגיטהאב.")
        st.stop()
        
    doctor_names = df_doctors['שם הרופא'].tolist()

    st.subheader("👩‍⚕️ הזנת זמינות רופאים")
    st.markdown("בחרי רופא מהרשימה וסמני את התאריכים שהוא פנוי בהם. מספרי הטלפון שמורים בבטחה במערכת.")
    
    selected_doctor = st.selectbox("בחירת רופא להזנה:", ["-- בחרי רופא --"] + doctor_names)
    
    if selected_doctor != "-- בחרי רופא --":
        with st.container(border=True):
            st.markdown(f"#### התאריכים של {selected_doctor}")
            
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
                if selected_dates:
                    st.session_state.availability_dict[selected_doctor] = selected_dates
                elif selected_doctor in st.session_state.availability_dict:
                    del st.session_state.availability_dict[selected_doctor]
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
        if st.button("🪄 צרי סידור עבודה אוטומטי (לפי מד הצדק)", type="primary", use_container_width=True):
            with st.spinner("האלגוריתם מחשב את השיבוץ ההוגן ביותר... ⚖️"):
                schedule_df, burnout_dict = generate_fair_schedule(st.session_state.availability_dict)
                st.session_state.final_schedule = schedule_df
                st.session_state.burnout_scores = burnout_dict
                st.rerun()
    else:
        st.caption("עדיין לא הוזנו תאריכים לאף רופא.")

    # תצוגת הסידור והשחיקה אחרי שהאלגוריתם רץ
    if "final_schedule" in st.session_state:
        st.divider()
        st.subheader("🎉 סידור העבודה מוכן!")
        st.dataframe(st.session_state.final_schedule, use_container_width=True, hide_index=True)
        
        with st.expander("📊 מאחורי הקלעים: טבלת נקודות השחיקה של הצוות (שקיפות!)"):
            st.markdown("*(המטו = +2 נקודות, השתלות = +1 נקודה. המערכת דואגת למי שיש לו הכי מעט)*")
            burnout_df = pd.DataFrame(list(st.session_state.burnout_scores.items()), columns=["שם הרופא", "נקודות שחיקה"])
            burnout_df = burnout_df.sort_values(by="נקודות שחיקה", ascending=False)
            st.dataframe(burnout_df, hide_index=True)

if __name__ == "__main__":
    main()
