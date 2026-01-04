print("=== TESTS SIMPLES DÉMARRÉS ===")

def test_addition():
    """Test que 1+1=2"""
    print("🧪 Test d'addition...")
    resultat = 1 + 1
    assert resultat == 2, f"1+1 devrait être 2, pas {resultat}"
    print("✅ Addition correcte!")

def test_liste_etudiants():
    """Test avec une liste d'étudiants"""
    print("🧪 Test liste étudiants...")
    etudiants = ["Alice", "Bob", "Charlie", "David"]
    
    # Vérifications
    assert len(etudiants) == 4
    assert "Alice" in etudiants
    assert "Bob" in etudiants
    
    print(f"✅ {len(etudiants)} étudiants dans la liste")

def test_dictionnaire_absence():
    """Test création d'une absence"""
    print("🧪 Test création absence...")
    
    absence = {
        "etudiant": "ETU001",
        "cours": "MATH101",
        "date": "2025-11-04",
        "justifiee": False
    }
    
    assert absence["etudiant"] == "ETU001"
    assert absence["cours"] == "MATH101"
    assert absence["justifiee"] == False
    
    print(f"✅ Absence créée pour {absence['etudiant']}")

print("=== TESTS SIMPLES PRÊTS ===")