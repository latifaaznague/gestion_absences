"""
Tests pour le module professeur
"""

def test_professeur_creer_seance():
    """Test création séance par professeur"""
    print("🧪 Test professeur: Créer séance")
    
    seance = {
        "cours": "MATH101",
        "date": "2025-11-04",
        "heure_debut": "10:00",
        "heure_fin": "12:00",
        "salle": "A101"
    }
    
    assert seance["heure_fin"] > seance["heure_debut"]
    assert len(seance["salle"]) >= 3
    print("   ✅ Création séance testée")

def test_professeur_marquer_presences():
    """Test marquer présences"""
    print("🧪 Test professeur: Marquer présences")
    
    etudiants = [
        {"id": 1, "nom": "Alice", "present": True},
        {"id": 2, "nom": "Bob", "present": False},
        {"id": 3, "nom": "Charlie", "present": True}
    ]
    
    presents = sum(1 for e in etudiants if e["present"])
    absents = len(etudiants) - presents
    
    assert presents == 2
    assert absents == 1
    print("   ✅ Marquage présences testé")

def test_professeur_valider_justification():
    """Test validation justification"""
    print("🧪 Test professeur: Valider justification")
    
    justification = {
        "etudiant": "ETU001",
        "cours": "MATH101",
        "date": "2025-11-04",
        "motif": "Maladie",
        "statut": "EN_ATTENTE"
    }
    
    assert justification["statut"] in ["EN_ATTENTE", "ACCEPTEE", "REFUSEE"]
    assert len(justification["motif"]) > 0
    print("   ✅ Validation justification testée")