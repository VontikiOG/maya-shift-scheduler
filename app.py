import streamlit as st
import pandas as pd
import random
from datetime import datetime

# הגדרות עמוד נעימות
st.set_page_config(page_title="המשמרות של מאיה", page_icon="🌸", layout="centered")

st.markdown("""
<style>
    .stApp { direction: rtl; }
    p, div, h1, h2, h3, h4, h5, h6, label, span, li, button, input { text-align: right !important; }
    [data-testid="stDataFrame"] { direction: rtl; }
</style>
""", unsafe_allow_html=True)

# פונקציית עזר לזיהוי סופ"ש (שישי-שבת)
def is_weekend(date_str):
    try:
        # הנחה שהתאריך בפורמט DD/MM/YYYY
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        return date_obj.weekday() in [4, 5] # 4=שישי, 5=שבת
    except:
        return False

# אלגוריתם השיבוץ
def generate_schedule(df_availability):
    schedule = []
    # מציאת כל התאריכים הייחודיים מהקובץ
    all_dates = df_availability['תאריך'].unique()
    
    for current_date in sorted(all_dates):
        is_we = is_weekend(current_date)
        available_today = df_availability[df_availability['תאריך'] == current_date]['שם רופא'].tolist()
        
        # סינון לפי חוקים
        bmt_candidates = []
        hemato_candidates = []
        
        for doc in available_today:
            # חוקי סופ"ש
            if doc == "בהאא עתאמנה" and not is_we: continue
            if doc == "מטקוביץ אליעזר" and not is_we: continue
            
            # חוקי מחלקות
            if doc == "בהאא עתאמנה" or doc == "ילנמה טראסוב":
                bmt_candidates.append(doc)
            else:
                bmt_candidates.append(doc)
                hemato_candidates.append(doc)
                
        # שיבוץ אקראי מתוך הפנויים (בשלב הבא נוסיף כאן את מד הצדק)
        hemato_doc = "אין רופא פנוי"
        bmt_doc = "אין רופא פנוי"
        
        if hemato_candidates:
            hemato_doc = random.choice(hemato_candidates)
            if hemato_doc in bmt_candidates:
                bmt_candidates.remove(hemato_doc) # מניעת כפילות מאותו רופא
                
        if bmt_candidates:
            bmt_doc = random.choice(bmt_candidates)
            
        schedule.append({
            "תאריך": current_date,
            "סוג יום": "סופ״ש 🌴" if is_we else "אמצע שבוע ☀️",
            "המטואונקולוגיה": hemato_doc,
            "השתלות מח עצם": bmt_doc,
            "שעות": "15:00 - 08:00"
        })
        
    return pd.DataFrame(schedule)

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

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("מערכת השיבוצים של מאיה 🌸")
        st.markdown("ברוכה הבאה! כאן נהפוך את כאב הראש של השיבוצים לקלי קלות.")
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
        st.info("אנא התחברי למערכת כדי להעלות אילוצים ולייצר סידור עבודה חודשי.")
        st.stop()

    st.subheader("📝 יצירת סידור עבודה חדש")
    st.markdown("העלי את קובץ האקסל עם אילוצי הרופאים (עמודות נדרשות: `שם רופא`, `תאריך`).")
    
    uploaded_file = st.file_uploader("בחרי קובץ אקסל או CSV", type=['csv', 'xlsx'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('csv'):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)
                
            st.success("הקובץ נטען בהצלחה! ✨")
            
            with st.expander("הצגת הנתונים הגולמיים שהועלו"):
                st.dataframe(df_input)
                
            if st.button("🪄 צרי סידור עבודה אוטומטי", type="primary"):
                with st.spinner("מחשב את השיבוץ המושלם..."):
                    df_schedule = generate_schedule(df_input)
                    st.session_state.final_schedule = df_schedule
                    
        except Exception as e:
            st.error(f"אוי, משהו השתבש בקריאת הקובץ. ודאי שהעמודות כתובות נכון. שגיאה: {e}")

    if "final_schedule" in st.session_state:
        st.divider()
        st.subheader("🎉 סידור העבודה מוכן!")
        st.dataframe(st.session_state.final_schedule, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()