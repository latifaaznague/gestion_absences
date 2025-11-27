from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractBaseUser

# ============================================
# Modèle: Filiere
# ============================================
class Filiere(models.Model):
    code = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    niveau = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'filiere'
        verbose_name = 'Filière'
        verbose_name_plural = 'Filières'
    
    def __str__(self):
        return f"{self.code} - {self.nom}"


# ============================================
# Modèle: Promotion
# ============================================
class Promotion(models.Model):
    libelle = models.CharField(max_length=100)
    annee_scolaire = models.CharField(max_length=20)
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, related_name='promotions')
    
    class Meta:
        db_table = 'promotion'
        verbose_name = 'Promotion'
        verbose_name_plural = 'Promotions'
    
    def __str__(self):
        return f"{self.libelle} ({self.annee_scolaire})"


# ============================================
# Modèle: Utilisateur (classe mère)
# ============================================
class Utilisateur(models.Model):
    TYPE_CHOICES = [
        ('ETUDIANT', 'Étudiant'),
        ('PROFESSEUR', 'Professeur'),
        ('ADMINISTRATEUR', 'Administrateur'),
    ]
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    mot_de_passe = models.CharField(max_length=255)
    type_utilisateur = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'utilisateur'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['type_utilisateur']),
        ]
    
    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.type_utilisateur})"


# ============================================
# Modèle: Administrateur
# ============================================
class Administrateur(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='admin_profile'
    )
    
    class Meta:
        db_table = 'administrateur'
        verbose_name = 'Administrateur'
        verbose_name_plural = 'Administrateurs'
    
    def __str__(self):
        return f"Admin: {self.utilisateur.prenom} {self.utilisateur.nom}"


# ============================================
# Modèle: Professeur
# ============================================
class Professeur(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='prof_profile'
    )
    specialite = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = 'professeur'
        verbose_name = 'Professeur'
        verbose_name_plural = 'Professeurs'
    
    def __str__(self):
        return f"Prof: {self.utilisateur.prenom} {self.utilisateur.nom}"


# ============================================
# Modèle: Etudiant
# ============================================
class Etudiant(models.Model):
    utilisateur = models.OneToOneField(
        Utilisateur, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='etudiant_profile'
    )
    promotion = models.ForeignKey(
        Promotion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='etudiants'
    )
    code_etudiant = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'etudiant'
        verbose_name = 'Étudiant'
        verbose_name_plural = 'Étudiants'
        indexes = [
            models.Index(fields=['code_etudiant']),
        ]
    
    def __str__(self):
        return f"{self.code_etudiant} - {self.utilisateur.prenom} {self.utilisateur.nom}"


# ============================================
# Modèle: Groupe
# ============================================
class Groupe(models.Model):
    nom = models.CharField(max_length=100)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='groupes')
    etudiants = models.ManyToManyField(Etudiant, through='EtudiantGroupe', related_name='groupes')
    
    class Meta:
        db_table = 'groupe'
        verbose_name = 'Groupe'
        verbose_name_plural = 'Groupes'
    
    def __str__(self):
        return f"{self.nom} - {self.promotion.libelle}"


# ============================================
# Modèle: EtudiantGroupe (table association)
# ============================================
class EtudiantGroupe(models.Model):
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'etudiant_groupe'
        unique_together = ('etudiant', 'groupe')
        verbose_name = 'Étudiant-Groupe'
        verbose_name_plural = 'Étudiants-Groupes'
    
    def __str__(self):
        return f"{self.etudiant.code_etudiant} -> {self.groupe.nom}"


# ============================================
# Modèle: Cours
# ============================================
class Cours(models.Model):
    code = models.CharField(max_length=50, unique=True)
    libelle = models.CharField(max_length=150)
    volume_horaire = models.IntegerField(default=0)
    professeur = models.ForeignKey(
        Professeur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cours'
    )
    
    class Meta:
        db_table = 'cours'
        verbose_name = 'Cours'
        verbose_name_plural = 'Cours'
    
    def __str__(self):
        return f"{self.code} - {self.libelle}"


# ============================================
# Modèle: Planning
# ============================================
class Planning(models.Model):
    semaine = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(52)])
    annee = models.IntegerField()
    administrateur = models.ForeignKey(
        Administrateur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='plannings'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'planning'
        verbose_name = 'Planning'
        verbose_name_plural = 'Plannings'
    
    def __str__(self):
        return f"Planning S{self.semaine} - {self.annee}"


# ============================================
# Modèle: Seance
# ============================================
class Seance(models.Model):
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    salle = models.CharField(max_length=50, blank=True, null=True)
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='seances')
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, related_name='seances')
    planning = models.ForeignKey(Planning, on_delete=models.CASCADE, related_name='seances')
    
    class Meta:
        db_table = 'seance'
        verbose_name = 'Séance'
        verbose_name_plural = 'Séances'
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['cours']),
        ]
    
    def __str__(self):
        return f"{self.cours.libelle} - {self.date} ({self.heure_debut}-{self.heure_fin})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.heure_fin <= self.heure_debut:
            raise ValidationError("L'heure de fin doit être après l'heure de début")


# ============================================
# Modèle: Presence
# ============================================
class Presence(models.Model):
    STATUT_CHOICES = [
        ('PRESENT', 'Présent'),
        ('ABSENT_JUSTIFIE', 'Absent Justifié'),
        ('ABSENT_NON_JUSTIFIE', 'Absent Non Justifié'),
    ]
    
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES)
    justification = models.TextField(blank=True, null=True)
    fichier_justificatif = models.BinaryField(blank=True, null=True)
    date_saisie = models.DateTimeField(auto_now_add=True)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='presences')
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, related_name='presences')
    
    class Meta:
        db_table = 'presence'
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        unique_together = ('etudiant', 'seance')
        indexes = [
            models.Index(fields=['etudiant']),
            models.Index(fields=['seance']),
            models.Index(fields=['statut']),
        ]
    
    def __str__(self):
        return f"{self.etudiant.code_etudiant} - {self.seance.cours.code} - {self.statut}"


# ============================================
# Modèle: Notification
# ============================================
class Notification(models.Model):
    message = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, related_name='notifications')
    presence = models.ForeignKey(
        Presence, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications'
    )
    
    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['etudiant']),
        ]
        ordering = ['-date_envoi']
    
    def __str__(self):
        return f"Notification pour {self.etudiant.code_etudiant} - {'Lu' if self.lu else 'Non lu'}"
