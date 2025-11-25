 CREATE TABLE IF NOT EXISTS presence (
    id SERIAL PRIMARY KEY,
    etudiant_id INT,
    seance_id INT,
    statut VARCHAR(20),
    date_saisie TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS seance (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100),
    valide BOOLEAN DEFAULT FALSE
);

