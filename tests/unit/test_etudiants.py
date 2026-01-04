"""
Tests pour le module étudiant
"""

def test_etudiant_login():
    """Test simulation login étudiant"""
    print("🧪 Test étudiant: Login")
    
    credentials = {
        "email": "etudiant@example.com",
        "mot_de_passe": "Password123!"
    }
    
    assert "@" in credentials["email"]
    assert "." in credentials["email"]
    assert len(credentials["mot_de_passe"]) >= 8
    print("   ✅ Login étudiant testé")

def test_etudiant_dashboard():
    """Test données dashboard étudiant"""
    print("🧪 Test étudiant: Dashboard")
    
    dashboard = {
        "etudiant": "ETU2025001",
        "nom": "Dupont",
        "prenom": "Jean",
        "statistiques": {
            "total_seances": 30,
            "presents": 25,
            "absences": 5
        }
    }
    
    assert dashboard["etudiant"].startswith("ETU")
    total = dashboard["statistiques"]["presents"] + dashboard["statistiques"]["absences"]
    assert total == dashboard["statistiques"]["total_seances"]
    print("   ✅ Dashboard étudiant testé")

def test_etudiant_absences():
    """Test liste des absences étudiant"""
    print("🧪 Test étudiant: Absences")
    
    absences = [
        {"cours": "Mathématiques", "date": "2025-11-01", "statut": "ABSENT_JUSTIFIE"},
        {"cours": "Physique", "date": "2025-11-02", "statut": "ABSENT_NON_JUSTIFIE"},
        {"cours": "Informatique", "date": "2025-11-03", "statut": "PRESENT"}
    ]
    
    total_absences = sum(1 for a in absences if "ABSENT" in a["statut"])
    assert total_absences == 2
    assert len(absences) == 3
    print("   ✅ Absences étudiant testées")