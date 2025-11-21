# 🎓 Système de Gestion des Absences
**Université Ibn Zohr - Faculté des Sciences - Agadir**

Système distribué pour la gestion des présences et absences des étudiants de la filière ADIA (Analyse de Données et Intelligence Artificielle).

---

## 📋 Table des matières
- [Description](#description)
- [Base de données](#base-de-données)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Données de test](#données-de-test)
---

## 📖 Description

Ce système permet de :
- ✅ **Professeurs** : Marquer les présences/absences, consulter statistiques
- ✅ **Étudiants** : Consulter leur historique, justifier leurs absences
- ✅ **Administrateurs** : Gérer les cours, plannings, et étudiants

### Fonctionnalités principales
- Gestion des présences en temps réel
- Notifications automatiques pour absences non justifiées
- Statistiques et rapports de présence
- Justification d'absences avec pièces jointes
- Planning hebdomadaire dynamique



## 🗄️ Base de données

### Tables principales
- **Utilisateur** : Gestion des comptes (Étudiant, Professeur, Admin)
- **Etudiant / Professeur / Administrateur** : Tables spécialisées
- **Filiere / Promotion / Groupe** : Organisation académique
- **Cours** : Matières enseignées
- **Planning** : Plannings hebdomadaires
- **Seance** : Séances de cours programmées
- **Presence** : Enregistrement des présences/absences
- **Notification** : Alertes pour les étudiants

### Schéma
![Diagramme de classes](diagramme_classes.png)

---

## 💻 Installation

### Prérequis
- PostgreSQL 18 ou supérieur
- Git

### Étapes

#### 1. Cloner le repository
```bash
git clone https://github.com/votre-equipe/attendance-system-db.git
cd attendance-system-db
```

#### 2. Installer PostgreSQL
**Windows:**
- Télécharger depuis [postgresql.org](https://www.postgresql.org/download/windows/)
- Installer avec les paramètres par défaut
- Noter le mot de passe du super-utilisateur `postgres`

**macOS:**
```bash
brew install postgresql@18
brew services start postgresql@18
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql-18
sudo systemctl start postgresql
```

#### 3. Créer la base de données
```bash
# Se connecter à PostgreSQL
psql -U postgres

# Créer la base de données
CREATE DATABASE attendance_system;

# Quitter
\q
```

#### 4. Exécuter le script de création
```bash
psql -U postgres -d attendance_system -f database/schema.sql
```

#### 5. Vérifier l'installation
```bash
psql -U postgres -d attendance_system

# Dans psql, taper:
\dt  # Liste des tables
SELECT * FROM Utilisateur;  # Voir les utilisateurs de test
\q   # Quitter
```

---

## 🚀 Utilisation

### Se connecter avec les comptes de test

#### Administrateur
- **Email:** admin@uiz.ac.ma
- **Mot de passe:** admin123

#### Professeurs
| Nom | Email | Mot de passe | Spécialité |
|-----|-------|--------------|------------|
| EL HABOUZ | elhabouz@uiz.ac.ma | prof123 | Systèmes Distribués |
| MANSOURI | mansouri@uiz.ac.ma | prof123 | Tendances IT |
| EL OUAFDI | elouafdi@uiz.ac.ma | prof123 | Optimisation |
| ALAOUI | alaoui@uiz.ac.ma | prof123 | Informatique Décisionnelle |

#### Étudiants
| Nom | Email | Mot de passe | Code | Groupe |
|-----|-------|--------------|------|--------|
| HOUDA NAJIB ALAOUI | houdanajib.alaoui@gmail.com | etudiant123 | ADIA2024001 | 3 |
| AYA JAOUHER | jaouheraya12@gmail.com | etudiant123 | ADIA2024002 | 2 |
| YOUSSEF BENALI | youssef.benali@uiz.ac.ma | etudiant123 | ADIA2024003 | 1 |
| FATIMA ALAMI | fatima.alami@uiz.ac.ma | etudiant123 | ADIA2024004 | 2 |

### Requêtes SQL utiles

#### Voir le taux de présence d'un étudiant
```sql
SELECT * FROM v_taux_presence_etudiant 
WHERE code_etudiant = 'ADIA2024001';
```

#### Statistiques par cours
```sql
SELECT * FROM v_statistiques_cours;
```

#### Absences non justifiées
```sql
SELECT u.nom, u.prenom, COUNT(*) as nb_absences
FROM Presence p
JOIN Etudiant e ON p.etudiant_id = e.id
JOIN Utilisateur u ON e.id = u.id
WHERE p.statut = 'ABSENT_NON_JUSTIFIE'
GROUP BY u.nom, u.prenom
ORDER BY nb_absences DESC;
```

#### Planning de la semaine
```sql
SELECT 
    s.date,
    s.heure_debut,
    s.heure_fin,
    c.libelle as cours,
    s.salle,
    g.nom as groupe
FROM Seance s
JOIN Cours c ON s.cours_id = c.id
JOIN Groupe g ON s.groupe_id = g.id
JOIN Planning p ON s.planning_id = p.id
WHERE p.semaine = 46 AND p.annee = 2024
ORDER BY s.date, s.heure_debut;
```

---

## 📊 Données de test

Le script inclut des données de test réalistes :
- ✅ 1 Administrateur
- ✅ 4 Professeurs
- ✅ 6 Étudiants (dont les 2 membres de l'équipe)
- ✅ 3 Groupes
- ✅ 7 Cours
- ✅ 15 Séances (semaine complète)
- ✅ 33 Enregistrements de présence
- ✅ 7 Notifications

### Cours disponibles
1. **INFO301** - Distributed Systems (Prof. EL HABOUZ)
2. **INFO302** - Tendances IT (Prof. MANSOURI)
3. **MATH301** - Optimisation et Recherche Opérationnelle (Prof. EL OUAFDI)
4. **INFO303** - Cyber Security (Prof. ALAOUI)
5. **INFO304** - Cloud Computing (Prof. EL HABOUZ)
6. **INFO305** - Big Data Analytics (Prof. MANSOURI)
7. **MATH302** - Data Mining (Prof. EL OUAFDI)

