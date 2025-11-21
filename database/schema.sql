-- ============================================
-- Système de Gestion des Absences
-- Université Ibn Zohr - Faculté des Sciences - Agadir
-- Filière: ADIA (Analyse de Données et Intelligence Artificielle)
-- Base de données PostgreSQL
-- ============================================

-- Supprimer les tables si elles existent déjà
DROP TABLE IF EXISTS Presence CASCADE;
DROP TABLE IF EXISTS Notification CASCADE;
DROP TABLE IF EXISTS Seance CASCADE;
DROP TABLE IF EXISTS Planning CASCADE;
DROP TABLE IF EXISTS Cours CASCADE;
DROP TABLE IF EXISTS Etudiant_Groupe CASCADE;
DROP TABLE IF EXISTS Groupe CASCADE;
DROP TABLE IF EXISTS Etudiant CASCADE;
DROP TABLE IF EXISTS Professeur CASCADE;
DROP TABLE IF EXISTS Administrateur CASCADE;
DROP TABLE IF EXISTS Utilisateur CASCADE;
DROP TABLE IF EXISTS Promotion CASCADE;
DROP TABLE IF EXISTS Filiere CASCADE;

-- ============================================
-- Table: Utilisateur (classe mère)
-- ============================================
CREATE TABLE Utilisateur (
    id BIGSERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    mot_de_passe VARCHAR(255) NOT NULL,
    type_utilisateur VARCHAR(20) NOT NULL CHECK (type_utilisateur IN ('ETUDIANT', 'PROFESSEUR', 'ADMINISTRATEUR')),
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Table: Administrateur
-- ============================================
CREATE TABLE Administrateur (
    id BIGINT PRIMARY KEY REFERENCES Utilisateur(id) ON DELETE CASCADE
);

-- ============================================
-- Table: Professeur
-- ============================================
CREATE TABLE Professeur (
    id BIGINT PRIMARY KEY REFERENCES Utilisateur(id) ON DELETE CASCADE,
    specialite VARCHAR(100)
);

-- ============================================
-- Table: Filiere
-- ============================================
CREATE TABLE Filiere (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    nom VARCHAR(100) NOT NULL,
    niveau VARCHAR(50)
);

-- ============================================
-- Table: Promotion
-- ============================================
CREATE TABLE Promotion (
    id BIGSERIAL PRIMARY KEY,
    libelle VARCHAR(100) NOT NULL,
    annee_scolaire VARCHAR(20) NOT NULL,
    filiere_id BIGINT REFERENCES Filiere(id) ON DELETE CASCADE
);

-- ============================================
-- Table: Etudiant
-- ============================================
CREATE TABLE Etudiant (
    id BIGINT PRIMARY KEY REFERENCES Utilisateur(id) ON DELETE CASCADE,
    promotion_id BIGINT REFERENCES Promotion(id) ON DELETE SET NULL,
    code_etudiant VARCHAR(50) UNIQUE NOT NULL
);

-- ============================================
-- Table: Groupe
-- ============================================
CREATE TABLE Groupe (
    id BIGSERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    promotion_id BIGINT REFERENCES Promotion(id) ON DELETE CASCADE
);

-- Table association: Etudiant appartient à Groupe
CREATE TABLE Etudiant_Groupe (
    etudiant_id BIGINT REFERENCES Etudiant(id) ON DELETE CASCADE,
    groupe_id BIGINT REFERENCES Groupe(id) ON DELETE CASCADE,
    PRIMARY KEY (etudiant_id, groupe_id)
);

-- ============================================
-- Table: Cours
-- ============================================
CREATE TABLE Cours (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    libelle VARCHAR(150) NOT NULL,
    volume_horaire INT NOT NULL DEFAULT 0,
    professeur_id BIGINT REFERENCES Professeur(id) ON DELETE SET NULL
);

-- ============================================
-- Table: Planning
-- ============================================
CREATE TABLE Planning (
    id BIGSERIAL PRIMARY KEY,
    semaine INT NOT NULL CHECK (semaine BETWEEN 1 AND 52),
    annee INT NOT NULL,
    administrateur_id BIGINT REFERENCES Administrateur(id) ON DELETE SET NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Table: Seance
-- ============================================
CREATE TABLE Seance (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    heure_debut TIME NOT NULL,
    heure_fin TIME NOT NULL,
    salle VARCHAR(50),
    cours_id BIGINT REFERENCES Cours(id) ON DELETE CASCADE,
    groupe_id BIGINT REFERENCES Groupe(id) ON DELETE CASCADE,
    planning_id BIGINT REFERENCES Planning(id) ON DELETE CASCADE,
    CONSTRAINT check_heures CHECK (heure_fin > heure_debut)
);

-- ============================================
-- Table: Presence
-- ============================================
CREATE TABLE Presence (
    id BIGSERIAL PRIMARY KEY,
    statut VARCHAR(30) NOT NULL CHECK (statut IN ('PRESENT', 'ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE')),
    justification TEXT,
    fichier_justificatif BYTEA,
    date_saisie TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    etudiant_id BIGINT REFERENCES Etudiant(id) ON DELETE CASCADE,
    seance_id BIGINT REFERENCES Seance(id) ON DELETE CASCADE,
    UNIQUE (etudiant_id, seance_id)
);

-- ============================================
-- Table: Notification
-- ============================================
CREATE TABLE Notification (
    id BIGSERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    date_envoi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lu BOOLEAN DEFAULT FALSE,
    etudiant_id BIGINT REFERENCES Etudiant(id) ON DELETE CASCADE,
    presence_id BIGINT REFERENCES Presence(id) ON DELETE CASCADE
);

-- ============================================
-- Index pour optimiser les performances
-- ============================================
CREATE INDEX idx_utilisateur_email ON Utilisateur(email);
CREATE INDEX idx_utilisateur_type ON Utilisateur(type_utilisateur);
CREATE INDEX idx_etudiant_code ON Etudiant(code_etudiant);
CREATE INDEX idx_seance_date ON Seance(date);
CREATE INDEX idx_seance_cours ON Seance(cours_id);
CREATE INDEX idx_presence_etudiant ON Presence(etudiant_id);
CREATE INDEX idx_presence_seance ON Presence(seance_id);
CREATE INDEX idx_presence_statut ON Presence(statut);
CREATE INDEX idx_notification_etudiant ON Notification(etudiant_id);

-- ============================================
-- DONNÉES DE TEST
-- ============================================

-- Utilisateurs administrateurs
INSERT INTO Utilisateur (nom, prenom, email, mot_de_passe, type_utilisateur) VALUES
('ADMIN', 'SYSTEM', 'admin@uiz.ac.ma', 'admin123', 'ADMINISTRATEUR');

INSERT INTO Administrateur (id) VALUES (1);

-- Utilisateurs professeurs
INSERT INTO Utilisateur (nom, prenom, email, mot_de_passe, type_utilisateur) VALUES
('EL HABOUZ', 'EL HABOUZ', 'elhabouz@uiz.ac.ma', 'prof123', 'PROFESSEUR'),
('MANSOURI', 'MANSOURI', 'mansouri@uiz.ac.ma', 'prof123', 'PROFESSEUR'),
('EL OUAFDI', 'EL OUAFDI', 'elouafdi@uiz.ac.ma', 'prof123', 'PROFESSEUR'),
('ALAOUI', 'ALAOUI', 'alaoui@uiz.ac.ma', 'prof123', 'PROFESSEUR');

INSERT INTO Professeur (id, specialite) VALUES 
(2, 'Systèmes Distribués'),
(3, 'Technologies de l''Information'),
(4, 'Optimisation et Recherche Opérationnelle'),
(5, 'Informatique Décisionnelle');

-- Filières et Promotions
INSERT INTO Filiere (code, nom, niveau) VALUES
('INFO_01', 'ADIA', 'Licence'),
('INFO_02', 'IL', 'Master');

INSERT INTO Promotion (libelle, annee_scolaire, filiere_id) VALUES
('L3 ADIA', '2024-2025', 1),
('M1 ADIA', '2024-2025', 1);

-- Groupes
INSERT INTO Groupe (nom, promotion_id) VALUES
('Groupe 1', 1),
('Groupe 2', 1),
('Groupe 3', 1);

-- Étudiants (membres de l'équipe + autres)
INSERT INTO Utilisateur (nom, prenom, email, mot_de_passe, type_utilisateur) VALUES
('NAJIB ALAOUI', 'HOUDA', 'houdanajib.alaoui@gmail.com', 'etudiant123', 'ETUDIANT'),
('JAOUHER', 'AYA', 'jaouheraya12@gmail.com', 'etudiant123', 'ETUDIANT'),
('BENALI', 'YOUSSEF', 'youssef.benali@uiz.ac.ma', 'etudiant123', 'ETUDIANT'),
('ALAMI', 'FATIMA', 'fatima.alami@uiz.ac.ma', 'etudiant123', 'ETUDIANT'),
('RAHIMI', 'OMAR', 'omar.rahimi@uiz.ac.ma', 'etudiant123', 'ETUDIANT'),
('SAID', 'SARAH', 'sarah.said@uiz.ac.ma', 'etudiant123', 'ETUDIANT');

INSERT INTO Etudiant (id, promotion_id, code_etudiant) VALUES
(6, 2, 'ADIA2025001'),  -- Houda (M1)
(7, 2, 'ADIA2025002'),  -- Aya (M1)
(8, 1, 'ADIA2025003'),  -- Youssef (L3)
(9, 1, 'ADIA2025004'),  -- Fatima (L3)
(10, 1, 'ADIA2025005'), -- Omar (L3)
(11, 2, 'ADIA2025006'); -- Sarah (M1)

-- Association étudiants-groupes
INSERT INTO Etudiant_Groupe (etudiant_id, groupe_id) VALUES
(6, 3),   -- Houda dans Groupe 3
(7, 2),   -- Aya dans Groupe 2
(8, 1),   -- Youssef dans Groupe 1
(9, 2),   -- Fatima dans Groupe 2
(10, 1),  -- Omar dans Groupe 1
(11, 3);  -- Sarah dans Groupe 3

-- Cours
INSERT INTO Cours (code, libelle, volume_horaire, professeur_id) VALUES
('INFO301', 'Distributed Systems', 40, 2),
('INFO302', 'Tendances IT', 35, 3),
('MATH301', 'Optimisation et Recherche Opérationnelle', 40, 4),
('INFO303', 'Cyber Security', 30, 5),
('INFO304', 'Cloud Computing', 35, 2),
('INFO305', 'Big Data Analytics', 30, 3),
('MATH302', 'Data Mining', 35, 4);

-- Planning
INSERT INTO Planning (semaine, annee, administrateur_id) VALUES
(46, 2025, 1),  -- Semaine du 18-22 Novembre 2025
(47, 2025, 1),  -- Semaine du 25-29 Novembre 2025
(48, 2025, 1);  -- Semaine du 2-6 Décembre 2025

-- Séances (Semaine 46 - du 18 au 22 Novembre 2024)
INSERT INTO Seance (date, heure_debut, heure_fin, salle, cours_id, groupe_id, planning_id) VALUES
-- Lundi 18 Nov 2024
('2025-11-18', '08:00', '10:00', 'A101', 1, 1, 1),  -- Distributed Systems - Groupe 1
('2025-11-18', '10:15', '12:15', 'B202', 2, 2, 1),  -- Tendances IT - Groupe 2
('2025-11-18', '14:00', '16:00', 'C303', 3, 3, 1),  -- Optimisation - Groupe 3
-- Mardi 19 Nov 2024
('2025-11-19', '08:00', '10:00', 'A101', 4, 1, 1),  -- Cyber Security - Groupe 1
('2025-11-19', '10:15', '12:15', 'D404', 1, 2, 1),  -- Distributed Systems - Groupe 2
('2025-11-19', '14:00', '16:00', 'B202', 5, 3, 1),  -- Cloud Computing - Groupe 3
-- Mercredi 20 Nov 2024
('2025-11-20', '08:00', '10:00', 'C303', 2, 1, 1),  -- Tendances IT - Groupe 1
('2025-11-20', '10:15', '12:15', 'A101', 3, 2, 1),  -- Optimisation - Groupe 2
('2025-11-20', '14:00', '16:00', 'B202', 6, 3, 1),  -- Big Data - Groupe 3
-- Jeudi 21 Nov 2024
('2025-11-21', '08:00', '10:00', 'D404', 5, 1, 1),  -- Cloud Computing - Groupe 1
('2025-11-21', '10:15', '12:15', 'A101', 7, 2, 1),  -- Data Mining - Groupe 2
('2025-11-21', '14:00', '16:00', 'C303', 4, 3, 1),  -- Cyber Security - Groupe 3
-- Vendredi 22 Nov 2024
('2025-11-22', '08:00', '10:00', 'B202', 6, 1, 1),  -- Big Data - Groupe 1
('2025-11-22', '10:15', '12:15', 'A101', 1, 2, 1),  -- Distributed Systems - Groupe 2
('2025-11-22', '14:00', '16:00', 'D404', 7, 3, 1);  -- Data Mining - Groupe 3

-- Présences (données de test réalistes)
INSERT INTO Presence (statut, etudiant_id, seance_id, justification) VALUES
-- Séance 1 (Lundi 8h - Distributed Systems - Groupe 1)
('PRESENT', 8, 1, NULL),   -- Youssef
('PRESENT', 10, 1, NULL),  -- Omar
-- Séance 2 (Lundi 10h15 - Tendances IT - Groupe 2)
('PRESENT', 7, 2, NULL),   -- Aya
('ABSENT_NON_JUSTIFIE', 9, 2, NULL),  -- Fatima
-- Séance 3 (Lundi 14h - Optimisation - Groupe 3)
('PRESENT', 6, 3, NULL),   -- Houda
('PRESENT', 11, 3, NULL),  -- Sarah
-- Séance 4 (Mardi 8h - Cyber Security - Groupe 1)
('PRESENT', 8, 4, NULL),
('ABSENT_JUSTIFIE', 10, 4, 'Rendez-vous médical'),
-- Séance 5 (Mardi 10h15 - Distributed Systems - Groupe 2)
('PRESENT', 7, 5, NULL),
('PRESENT', 9, 5, NULL),
-- Séance 6 (Mardi 14h - Cloud Computing - Groupe 3)
('PRESENT', 6, 6, NULL),
('ABSENT_NON_JUSTIFIE', 11, 6, NULL),
-- Séance 7 (Mercredi 8h - Tendances IT - Groupe 1)
('PRESENT', 8, 7, NULL),
('PRESENT', 10, 7, NULL),
-- Séance 8 (Mercredi 10h15 - Optimisation - Groupe 2)
('ABSENT_JUSTIFIE', 7, 8, 'Problème de transport'),
('PRESENT', 9, 8, NULL),
-- Séance 9 (Mercredi 14h - Big Data - Groupe 3)
('PRESENT', 6, 9, NULL),
('PRESENT', 11, 9, NULL),
-- Séance 10 (Jeudi 8h - Cloud Computing - Groupe 1)
('PRESENT', 8, 10, NULL),
('PRESENT', 10, 10, NULL),
-- Séance 11 (Jeudi 10h15 - Data Mining - Groupe 2)
('PRESENT', 7, 11, NULL),
('ABSENT_NON_JUSTIFIE', 9, 11, NULL),
-- Séance 12 (Jeudi 14h - Cyber Security - Groupe 3)
('PRESENT', 6, 12, NULL),
('PRESENT', 11, 12, NULL),
-- Séance 13 (Vendredi 8h - Big Data - Groupe 1)
('PRESENT', 8, 13, NULL),
('PRESENT', 10, 13, NULL),
-- Séance 14 (Vendredi 10h15 - Distributed Systems - Groupe 2)
('PRESENT', 7, 14, NULL),
('PRESENT', 9, 14, NULL),
-- Séance 15 (Vendredi 14h - Data Mining - Groupe 3)
('ABSENT_JUSTIFIE', 6, 15, 'Urgence familiale'),
('PRESENT', 11, 15, NULL);

-- Notifications
INSERT INTO Notification (message, etudiant_id, presence_id) VALUES
('Vous avez une absence non justifiée au cours de Tendances IT du 18/11/2024 à 10h15', 9, 2),
('Vous avez une absence non justifiée au cours de Cloud Computing du 19/11/2024 à 14h00', 11, 6),
('Votre justification pour l''absence du 19/11/2024 (Cyber Security) a été acceptée', 10, 4),
('Vous avez une absence non justifiée au cours de Data Mining du 21/11/2024 à 10h15', 9, 24),
('Votre justification pour l''absence du 20/11/2024 (Optimisation) a été acceptée', 7, 18),
('⚠️ ALERTE: Vous avez 2 absences non justifiées. Au-delà de 3, vous serez convoqué', 9, 24),
('Votre justification pour l''absence du 22/11/2024 (Data Mining) a été acceptée', 6, 33);

-- ============================================
-- Vues utiles pour les statistiques
-- ============================================

-- Vue: Taux de présence par étudiant
CREATE VIEW v_taux_presence_etudiant AS
SELECT 
    e.id AS etudiant_id,
    u.nom,
    u.prenom,
    e.code_etudiant,
    COUNT(p.id) AS total_seances,
    SUM(CASE WHEN p.statut = 'PRESENT' THEN 1 ELSE 0 END) AS presences,
    ROUND(100.0 * SUM(CASE WHEN p.statut = 'PRESENT' THEN 1 ELSE 0 END) / COUNT(p.id), 2) AS taux_presence
FROM Etudiant e
JOIN Utilisateur u ON e.id = u.id
LEFT JOIN Presence p ON e.id = p.etudiant_id
GROUP BY e.id, u.nom, u.prenom, e.code_etudiant;

-- Vue: Statistiques par cours
CREATE VIEW v_statistiques_cours AS
SELECT 
    c.id AS cours_id,
    c.libelle AS cours,
    COUNT(DISTINCT s.id) AS nombre_seances,
    COUNT(p.id) AS total_presences_enregistrees,
    SUM(CASE WHEN p.statut = 'PRESENT' THEN 1 ELSE 0 END) AS presents,
    SUM(CASE WHEN p.statut = 'ABSENT_JUSTIFIE' THEN 1 ELSE 0 END) AS absents_justifies,
    SUM(CASE WHEN p.statut = 'ABSENT_NON_JUSTIFIE' THEN 1 ELSE 0 END) AS absents_non_justifies
FROM Cours c
LEFT JOIN Seance s ON c.id = s.cours_id
LEFT JOIN Presence p ON s.id = p.seance_id
GROUP BY c.id, c.libelle;
