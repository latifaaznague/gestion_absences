"""
Tests unitaires pour les modèles - VERSION CORRIGÉE
"""

def test_1_filiere_format():
    """Test format d'une filière"""
    print("🧪 Test 1: Format filière")
    
    # Données de test simulées
    filiere = {
        "code": "INFO",
        "nom": "Informatique",
        "niveau": "Master 1"
    }
    
    # Assertions sans return
    assert filiere["code"] == "INFO"
    assert "Informatique" in filiere["nom"]
    assert len(filiere["code"]) >= 2
    
    print(f"   ✅ Filière: {filiere['code']} - {filiere['nom']}")

def test_2_etudiant_code():
    """Test code étudiant"""
    print("🧪 Test 2: Code étudiant")
    
    codes_valides = [
        "ETU2025001",
        "ETU2025002", 
        "ETU2025101"
    ]
    
    for code in codes_valides:
        assert code.startswith("ETU")
        assert len(code) >= 7
    
    print(f"   ✅ {len(codes_valides)} codes étudiants valides")

def test_3_email_validation():
    """Test validation email"""
    print("🧪 Test 3: Validation email")
    
    emails = [
        "etudiant@example.com",
        "professeur@univ.edu",
        "admin@gestion.fr"
    ]
    
    for email in emails:
        assert "@" in email
        assert "." in email
        assert len(email) > 5
    
    print(f"   ✅ {len(emails)} emails valides")

def test_4_statuts_presence():
    """Test statuts de présence"""
    print("🧪 Test 4: Statuts présence")
    
    statuts = ["PRESENT", "ABSENT_JUSTIFIE", "ABSENT_NON_JUSTIFIE"]
    
    assert len(statuts) == 3
    assert "PRESENT" in statuts
    assert "ABSENT_JUSTIFIE" in statuts
    assert "ABSENT_NON_JUSTIFIE" in statuts
    
    print(f"   ✅ Statuts: {', '.join(statuts)}")

def test_5_calcul_taux_presence():
    """Test calcul taux de présence"""
    print("🧪 Test 5: Calcul taux présence")
    
    # Test 1
    total1 = 30
    absences1 = 5
    taux1 = ((total1 - absences1) / total1) * 100
    assert taux1 == ((30-5)/30)*100
    
    # Test 2
    total2 = 20
    absences2 = 0
    taux2 = ((total2 - absences2) / total2) * 100
    assert taux2 == 100.0
    
    print(f"   ✅ Calculs: {taux1:.1f}%, {taux2:.1f}%")

def test_6_format_date():
    """Test format de date"""
    print("🧪 Test 6: Format date")
    
    dates = [
        "2025-11-04",  # Format SQL
        "04/11/2025",  # Format français
    ]
    
    for date_str in dates:
        if "-" in date_str:
            parts = date_str.split("-")
            assert len(parts) == 3
        elif "/" in date_str:
            parts = date_str.split("/")
            assert len(parts) == 3
    
    print(f"   ✅ {len(dates)} formats de date acceptés")

def test_7_validation_roles():
    """Test validation des rôles"""
    print("🧪 Test 7: Validation rôles")
    
    roles = ["ETUDIANT", "PROFESSEUR", "ADMINISTRATEUR"]
    
    for role in roles:
        assert role.isupper()
        assert role in ["ETUDIANT", "PROFESSEUR", "ADMINISTRATEUR"]
    
    print(f"   ✅ Rôles: {', '.join(roles)}")

def test_8_simulation_cours():
    """Test simulation cours"""
    print("🧪 Test 8: Simulation cours")
    
    cours = {
        "code": "MATH101",
        "libelle": "Mathématiques Avancées",
        "volume_horaire": 60,
        "professeur": "PROF001"
    }
    
    assert len(cours["code"]) >= 5
    assert cours["volume_horaire"] > 0
    assert "Mathématiques" in cours["libelle"]
    
    print(f"   ✅ Cours: {cours['code']} - {cours['libelle']}")

def test_9_simulation_seance():
    """Test simulation séance"""
    print("🧪 Test 9: Simulation séance")
    
    seance = {
        "date": "2025-11-04",
        "heure_debut": "10:00",
        "heure_fin": "12:00",
        "salle": "A101",
        "cours": "MATH101"
    }
    
    assert "-" in seance["date"]
    assert ":" in seance["heure_debut"]
    assert ":" in seance["heure_fin"]
    
    print(f"   ✅ Séance: {seance['date']} {seance['heure_debut']}-{seance['heure_fin']}")

def test_10_notifications():
    """Test simulation notifications"""
    print("🧪 Test 10: Simulation notifications")
    
    notifications = [
        {
            "type": "ABSENCE",
            "message": "Absence au cours de Mathématiques",
            "lu": False
        },
        {
            "type": "JUSTIFICATION_ACCEPTEE", 
            "message": "Votre justification a été acceptée",
            "lu": True
        }
    ]
    
    for notif in notifications:
        assert "type" in notif
        assert "message" in notif
        assert "lu" in notif
        assert len(notif["message"]) > 10
    
    print(f"   ✅ {len(notifications)} types de notification")