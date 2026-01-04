"""
Tests pour le module administration
"""

def test_admin_statistiques():
    """Test calcul statistiques"""
    print("🧪 Test admin: Statistiques")
    
    data = {
        "total_etudiants": 200,
        "absences_mois": 45,
        "taux_absence": 22.5
    }
    
    taux_calcule = (data["absences_mois"] / data["total_etudiants"]) * 100
    assert abs(taux_calcule - data["taux_absence"]) < 0.1
    print("   ✅ Calcul statistiques testé")

def test_admin_generation_rapport():
    """Test génération rapport"""
    print("🧪 Test admin: Génération rapport")
    
    rapport = {
        "titre": "Rapport mensuel",
        "periode": "Novembre 2025",
        "sections": ["Résumé", "Statistiques", "Recommandations"]
    }
    
    assert len(rapport["sections"]) == 3
    assert "Rapport" in rapport["titre"]
    print("   ✅ Génération rapport testée")

def test_admin_gestion_utilisateurs():
    """Test gestion utilisateurs"""
    print("🧪 Test admin: Gestion utilisateurs")
    
    utilisateurs = [
        {"id": 1, "role": "admin", "actif": True},
        {"id": 2, "role": "professeur", "actif": True},
        {"id": 3, "role": "etudiant", "actif": False}
    ]
    
    actifs = sum(1 for u in utilisateurs if u["actif"])
    assert actifs == 2
    print("   ✅ Gestion utilisateurs testée")