import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import time
import json
import os
import io
import urllib.parse

# הגדרות עמוד נעימות
st.set_page_config(page_title="המשמרות של מאיה", page_icon="🌸", layout="centered")

st.markdown("""
<style>
    .stApp { direction: rtl; }
    p, div, h1, h2, h3, h4, h5, h6, label, span, li, button, input { text-align: right !important; }
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] { direction: rtl; }
    .success-text { color: #2e7d32; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

DRAFT_FILE = "schedule_draft.json"

# רשימת חגים לדוגמה 
HOLIDAYS = {
    "02/04/2026": "ערב פסח 🍷",
    "03/04/2026": "פסח 🍷",
    "08/04/2026": "ערב שביעי של פסח",
    "09/04/2026": "שביעי של פסח",
    "21/04/2026": "ערב יום העצמאות",
    "22/04/2026": "יום העצמאות 🇮🇱",
    "21/05/2026": "ערב שבועות",
    "22/05/2026": "שבועות 🌾"
}

# --- פונקציות טיוטה ושמירת מצב ---
def save_draft(data):
    try:
        with open(DRAFT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"שגיאה בשמירת הטיוטה: {e}")

def load_draft():
    if os.path.exists(DRAFT_FILE):
        try:
            with open(DRAFT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

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
        if current_date.weekday() in [4, 5]: 
            weekend_dates.append(date_str)
            
    return all_dates, weekend_dates, f"{month:02d}/{year}"

ALL_DATES, WEEKEND_DATES, TARGET_MONTH = get_next_month_dates()

def is_weekend(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").weekday() in [4, 5]
    except:
        return False

# --- טעינת נתוני הרופאים מ-CSV והכנת מספרי טלפון ---
@st.cache_data
def load_doctors_data():
    for enc in ['utf-8', 'cp1255', 'iso-8859-8']:
        try:
            df = pd.read_csv("doctors_list.csv", encoding=enc)
            df.columns = df.columns.str.strip()
            if 'מספר טלפון' in df.columns:
                cleaned_phones = df['מספר טלפון'].astype(str).str.replace("'", "").str.replace("-", "").str.strip()
                df['טלפון_נקי'] = cleaned_phones.apply(lambda x: "972" + x[1:] if x.startswith("0") else x)
            return df
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            return pd.DataFrame(columns=["שם הרופא", "מספר טלפון", "טלפון_נקי"])
    return pd.DataFrame(columns=["שם הרופא", "מספר טלפון", "טלפון_נקי"])

# --- אלגוריתם "מד הצדק" המשודרג (v2.1) ---
def generate_fair_schedule(availability_dict):
    all_dates = set()
    for dates in availability_dict.values():
        all_dates.update(dates)
    
    sorted_dates = sorted(list(all_dates), key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
    burnout_scores = {doc: 0 for doc in availability_dict.keys()}
    
    # מעקב מדויק אחרי מי עובד מתי
    assigned_dates = {doc: set() for doc in availability_dict.keys()}
    # כמה תאריכים כל רופא נתן למאיה
    avail_counts = {doc: len(dates) for doc, dates in availability_dict.items()}
    
    schedule = []
    bmt_keywords = ["ילנה", "טראסוב", "בהאא", "עתאמנה"]
    
    # פונקציית בדיקת רצף (חוק ברזל: לא עובדים יומיים ברצף)
    def can_work(doc, date_str):
        d = datetime.strptime(date_str, "%d/%m/%Y")
        prev_d = (d - timedelta(days=1)).strftime("%d/%m/%Y")
        next_d = (d + timedelta(days=1)).strftime("%d/%m/%Y")
        return (prev_d not in assigned_dates[doc]) and (next_d not in assigned_dates[doc])

    # --- שלב 1: שיבוץ ראשוני ---
    for date_str in sorted_dates:
        is_we = is_weekend(date_str)
        holiday_note = HOLIDAYS.get(date_str, "")
        
        # מסננים רק את מי שפנוי היום *וגם* לא עבד אתמול/מחר
        valid_docs = [doc for doc, dates in availability_dict.items() if date_str in dates and can_work(doc, date_str)]
        
        if not valid_docs:
            schedule.append({
                "תאריך": date_str, "סוג יום": "סופ״ש 🌴" if is_we else "אמצע שבוע ☀️",
                "הערות": holiday_note,
                "המטואונקולוגיה": "חסר רופא 🚨", "השתלות מח עצם": "חסר רופא 🚨"
            })
            continue
            
        bmt_only_docs = [d for d in valid_docs if any(k in d for k in bmt_keywords)]
        regular_docs = [d for d in valid_docs if d not in bmt_only_docs]
        
        bmt_doc = None
        hemato_doc = None
        
        # סדר העדיפויות במיון:
        # 1. חובה לדאוג למי שאין לו עדיין 2 משמרות.
        # 2. קדימות למי שנתן הכי מעט תאריכים פנויים החודש (הקמצנים קודם!).
        # 3. קדימות למי שיש לו פחות משמרות כרגע.
        # 4. שחיקה - המטו מעלים עומס, השתלות מורידים (פרס).
        
        if bmt_only_docs:
            bmt_only_docs.sort(key=lambda d: (
                len(assigned_dates[d]) >= 2,
                avail_counts[d],
                len(assigned_dates[d]),
                burnout_scores[d]
            ))
            bmt_doc = bmt_only_docs[0]
            
        if regular_docs:
            regular_docs.sort(key=lambda d: (
                len(assigned_dates[d]) >= 2,
                avail_counts[d],
                len(assigned_dates[d]),
                burnout_scores[d]
            ))
            hemato_doc = regular_docs[0]
            regular_docs.remove(hemato_doc)
            
        if not bmt_doc and regular_docs:
            regular_docs.sort(key=lambda d: (
                len(assigned_dates[d]) >= 2,
                avail_counts[d],
                len(assigned_dates[d]),
                -burnout_scores[d] # מינוס = לקחת את מי שנטחן הכי הרבה בהמטו
            ))
            bmt_doc = regular_docs[0]
            
        if bmt_doc:
            burnout_scores[bmt_doc] += 1
            assigned_dates[bmt_doc].add(date_str)
        if hemato_doc:
            burnout_scores[hemato_doc] += 2
            assigned_dates[hemato_doc].add(date_str)
            
        schedule.append({
            "תאריך": date_str,
            "סוג יום": "סופ״ש 🌴" if is_we else "אמצע שבוע ☀️",
            "הערות": holiday_note,
            "המטואונקולוגיה": hemato_doc if hemato_doc else "חסר רופא 🚨",
            "השתלות מח עצם": bmt_doc if bmt_doc else "חסר רופא 🚨"
        })

    # --- שלב 2: מנגנון "רובין הוד" לתיקון מינימום 2 משמרות ---
    for doc in availability_dict.keys():
        # כל עוד לרופא יש פחות מ-2 משמרות, ויש לו עוד תאריכים פנויים שהוא לא עובד בהם:
        while len(assigned_dates[doc]) < 2 and avail_counts[doc] > len(assigned_dates[doc]):
            swapped = False
            for date_str in availability_dict[doc]:
                if date_str in assigned_dates[doc]: continue
                if not can_work(doc, date_str): continue # אסור ליצור לו רצף
                
                # מציאת היום הספציפי בטבלה
                day_dict = next(item for item in schedule if item["תאריך"] == date_str)
                curr_hemato = day_dict["המטואונקולוגיה"]
                curr_bmt = day_dict["השתלות מח עצם"]
                
                is_bmt_only_doc = any(k in doc for k in bmt_keywords)
                
                # מנסים לקחת משמרת המטו ממישהו שיש לו 3 משמרות ומעלה
                if not is_bmt_only_doc and curr_hemato != "חסר רופא 🚨" and len(assigned_dates.get(curr_hemato, [])) > 2:
                    day_dict["המטואונקולוגיה"] = doc
                    assigned_dates[curr_hemato].remove(date_str)
                    burnout_scores[curr_hemato] -= 2
                    assigned_dates[doc].add(date_str)
                    burnout_scores[doc] += 2
                    swapped = True
                    break
                    
                # מנסים לקחת משמרת השתלות ממישהו שיש לו 3 משמרות ומעלה
                if curr_bmt != "חסר רופא 🚨" and len(assigned_dates.get(curr_bmt, [])) > 2:
                    day_dict["השתלות מח עצם"] = doc
                    assigned_dates[curr_bmt].remove(date_str)
                    burnout_scores[curr_bmt] -= 1
                    assigned_dates[doc].add(date_str)
                    burnout_scores[doc] += 1
                    swapped = True
                    break
                    
            if not swapped:
                break # אם עברנו על כל התאריכים ואי אפשר להחליף, עוצרים.

    return pd.DataFrame(schedule), burnout_scores

# --- אזור ניהול ויומן שינויים ---
@st.dialog("🔒 כניסת מנהלת")
def admin_login():
    st.markdown("בוקר טוב מאיה! הזיני סיסמה כדי להתחיל לעבוד.")
    pwd = st.text_input("סיסמה", type="password")
    
    correct_password = st.secrets.get("ADMIN_PASSWORD", "PASSWORD_NOT_SET")
    
    if st.button("התחברי 🌸", use_container_width=True):
        if pwd == correct_password and correct_password != "PASSWORD_NOT_SET":
            st.session_state.maya_logged_in = True
            st.rerun()
        elif correct_password == "PASSWORD_NOT_SET":
            st.error("🚨 שגיאת מערכת: מנהל המערכת טרם הגדיר סיסמה בשרת (Secrets).")
        else:
            st.error("סיסמה שגויה, נסי שוב מאיה! 😊")

@st.dialog("📜 יומן שינויים - היסטוריית הפיתוח")
def show_changelog():
    st.markdown("""
    **v2.1.0 | חוקי ברזל ומינימום משמרות 🛡️**
    * **איסור רצף (No Consecutive Shifts):** האלגוריתם מונע לחלוטין מצב שבו רופא (רגיל או חריג) עובד יומיים ברצף.
    * **תעדוף "הקמצנים":** שיבוץ המשמרות מתחיל מהרופאים שנתנו הכי מעט תאריכים, כדי להבטיח שהם ישובצו ולא יפוספסו.
    * **הבטחת מינימום 2 משמרות:** הוספת מנגנון "רובין הוד" חכם בסוף השיבוץ - אם מישהו קיבל רק משמרת אחת (אבל פנוי לעוד), המערכת תשאב משמרת ממישהו שעובד 3+ משמרות ותעביר אליו.

    **v2.0.0 | חווית משתמש ואבטחה מלאה 🚀**
    * הורדה לאקסל, טבלת עריכה חופשית ידנית, ייצור וואטסאפים אוטומטיים לשליחה מהירה, והעברת הסיסמה למנגנון Secrets.

    **v1.1.0 | טיוטות אוטומטיות ומד הצדק ⚖️**
    * מנגנון טיוטה Auto-Save, ואלגוריתם "נקודות שחיקה" המחלק משמרות לפי עומס קודם ותעדוף מחלקות.

    **v1.0.0 | גרסת הבסיס למאיה 🌸**
    * ממשק נקי, קריאת CSV עמידה לשגיאות קידוד, וזיהוי חריגי סופ"ש באופן אוטומטי.
    """)
    if st.button("סגירה", use_container_width=True):
        st.rerun()

def main():
    if "maya_logged_in" not in st.session_state:
        st.session_state.maya_logged_in = False
    
    if "availability_dict" not in st.session_state:
        st.session_state.availability_dict = load_draft()

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
        st.info("אנא התחברי למערכת כדי להתחיל לשבץ משמרות.")
        st.caption("*(הטיוטה היומית נשמרת אוטומטית גם אם הדפדפן נסגר)*")
        st.stop()

    df_doctors = load_doctors_data()
    if df_doctors.empty:
        st.warning("⚠️ הקובץ doctors_list.csv חסר. אנא העלי אותו לשרת הגיטהאב.")
        st.stop()
        
    doctor_names = df_doctors['שם הרופא'].tolist()
    
    total_doctors = len(doctor_names)
    fed_doctors_count = len(st.session_state.availability_dict.keys())
    progress_val = min(fed_doctors_count / total_doctors if total_doctors > 0 else 0, 1.0)

    st.subheader("👩‍⚕️ הזנת זמינות רופאים")
    st.progress(progress_val, text=f"הוזנו {fed_doctors_count} מתוך {total_doctors} רופאים בקובץ")
    
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
            
            def format_date_option(d):
                return f"{d} - {HOLIDAYS[d]}" if d in HOLIDAYS else d
            
            selected_dates = st.multiselect(
                "סמני את התאריכים (אפשר לבחור כמה ביחד):", 
                options_for_doctor,
                default=current_selections,
                format_func=format_date_option
            )
            
            if st.button(f"💾 שמרי תאריכים ל{selected_doctor}", type="primary"):
                if selected_dates:
                    st.session_state.availability_dict[selected_doctor] = selected_dates
                elif selected_doctor in st.session_state.availability_dict:
                    del st.session_state.availability_dict[selected_doctor]
                
                save_draft(st.session_state.availability_dict)
                st.success(f"מעולה! התאריכים של {selected_doctor} נשמרו. ✨")
                time.sleep(1) 
                st.rerun()

    st.divider()
    
    fed_doctors = list(st.session_state.availability_dict.keys())
    
    if fed_doctors:
        with st.expander("📋 רשימת הרופאים שכבר הוזנו החודש"):
            cols = st.columns(3)
            for i, doc in enumerate(fed_doctors):
                num_shifts = len(st.session_state.availability_dict[doc])
                cols[i % 3].markdown(f"✅ {doc} ({num_shifts})")
            
        st.write("")
        if st.button("🪄 צרי סידור עבודה אוטומטי (לפי מד הצדק)", type="primary", use_container_width=True):
            with st.spinner("האלגוריתם מחשב את השיבוץ ההוגן ביותר... ⚖️"):
                schedule_df, burnout_dict = generate_fair_schedule(st.session_state.availability_dict)
                st.session_state.final_schedule = schedule_df
                st.session_state.burnout_scores = burnout_dict
                st.rerun()
    else:
        st.caption("עדיין לא הוזנו תאריכים לאף רופא.")

    if "final_schedule" in st.session_state:
        st.divider()
        st.subheader("🎉 סידור העבודה מוכן! (טבלה ניתנת לעריכה)")
        st.markdown("אם משהו לא מסתדר לך, **את יכולה ללחוץ על השמות בטבלה ולשנות אותם ידנית** לפני שאת מורידה את הקובץ.")
        
        edited_df = st.data_editor(st.session_state.final_schedule, use_container_width=True, hide_index=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='סידור חודשי')
        
        st.download_button(
            label="📥 לחצי כאן להורדת הסידור המלא לאקסל",
            data=output.getvalue(),
            file_name=f"schedule_{TARGET_MONTH.replace('/', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        
        st.divider()
        st.subheader("📱 שליחת הודעות אישיות לרופאים")
        st.markdown("המערכת הכינה הודעות מרוכזות לכל רופא עם המשמרות שלו:")
        
        shifts_by_doc = {}
        for idx, row in edited_df.iterrows():
            date = row['תאריך']
            hemato = row['המטואונקולוגיה']
            bmt = row['השתלות מח עצם']
            
            if hemato and "חסר רופא" not in hemato:
                shifts_by_doc.setdefault(hemato, []).append(f"• {date} (המטואונקולוגיה)")
            if bmt and "חסר רופא" not in bmt:
                shifts_by_doc.setdefault(bmt, []).append(f"• {date} (השתלות מח עצם)")
                
        phone_dict = dict(zip(df_doctors['שם הרופא'], df_doctors['טלפון_נקי']))
        
        if shifts_by_doc:
            with st.expander("רשימת הודעות מוכנות לשליחה (לחצי לפתיחה)"):
                for doc, shifts in shifts_by_doc.items():
                    phone = phone_dict.get(doc, "")
                    if phone:
                        msg = f"היי ד״ר {doc}, להלן המשמרות שלך לחודש הקרוב:\n" + "\n".join(shifts) + "\n\nתודה רבה, מאיה 🌸"
                        url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
                        st.link_button(f"💬 שלחי לוואטסאפ של {doc}", url)
                    else:
                        st.warning(f"אין מספר טלפון מעודכן לד״ר {doc}")
                        
        with st.expander("📊 מאחורי הקלעים: טבלת נקודות השחיקה ומשמרות ששובצו"):
            st.markdown("*(המטו = +2 נקודות, השתלות = +1 נקודה. המערכת דאגה למינימום 2 משמרות היכן שניתן)*")
            burnout_data = []
            for doc, score in st.session_state.burnout_scores.items():
                shifts_count = len(shifts_by_doc.get(doc, []))
                burnout_data.append({"שם הרופא": doc, "כמות משמרות": shifts_count, "נקודות שחיקה": score})
            
            burnout_df = pd.DataFrame(burnout_data).sort_values(by="נקודות שחיקה", ascending=False)
            st.dataframe(burnout_df, hide_index=True)

    st.write("")
    st.write("")
    with st.expander("⚙️ אפשרויות מתקדמות (איפוס המערכת)"):
        st.warning("לחיצה על הכפתור תמחק את כל התאריכים שהזנת עד כה גם מהגיבוי. הפעולה בלתי הפיכה.")
        if st.button("🗑️ נקי הכל והתחילי מחדש", type="primary"):
            st.session_state.availability_dict = {}
            if "final_schedule" in st.session_state:
                del st.session_state.final_schedule
            if os.path.exists(DRAFT_FILE):
                os.remove(DRAFT_FILE)
            st.success("הכל נוקה בהצלחה! אפשר להתחיל סידור חדש.")
            time.sleep(1)
            st.rerun()

if __name__ == "__main__":
    main()
