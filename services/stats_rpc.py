from services.db import get_conn

def dashboard_stats(request):
    conn = get_conn()
    cur = conn.cursor()

    # Total étudiants
    cur.execute("SELECT COUNT(*) FROM etudiant")
    students = cur.fetchone()[0]

    # Total cours
    cur.execute("SELECT COUNT(*) FROM cours")
    courses = cur.fetchone()[0]

    # Absences non justifiées
    cur.execute("""
        SELECT COUNT(*) 
        FROM presence 
        WHERE statut = 'ABSENT_NON_JUSTIFIE'
    """)
    absences_nj = cur.fetchone()[0]

    # Absences par semaine
    cur.execute("""
        SELECT EXTRACT(WEEK FROM date_saisie) AS semaine, COUNT(*)
        FROM presence
        WHERE statut = 'ABSENT_NON_JUSTIFIE'
        GROUP BY semaine
        ORDER BY semaine
    """)
    weekly = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "students": students,
        "courses": courses,
        "absences_nj": absences_nj,
        "weekly": [{"week": int(w), "total": t} for w, t in weekly]
    }
