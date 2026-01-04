from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

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
    # SEUL CHANGEMENT: Ajout de db_column='filiere_id'
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, db_column='filiere_id', related_name='promotions')
    
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
    # CHANGEMENT CRITIQUE: db_column='id' car dans la BD c'est 'id', pas 'utilisateur_id'
    utilisateur = models.OneToOneField(
        Utilisateur, 
        on_delete=models.CASCADE, 
        primary_key=True,
        db_column='id',  # <-- CHANGEMENT ICI
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
    # CHANGEMENT CRITIQUE: db_column='id' car dans la BD c'est 'id', pas 'utilisateur_id'
    utilisateur = models.OneToOneField(
        Utilisateur, 
        on_delete=models.CASCADE, 
        primary_key=True,
        db_column='id',  # <-- CHANGEMENT ICI
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
# Modèle: Etudiant (CHANGEMENTS IMPORTANTS)
# ============================================
class Etudiant(models.Model):
    # CHANGEMENT CRITIQUE: db_column='id' car dans la BD c'est 'id' (clé étrangère vers Utilisateur)
    utilisateur = models.OneToOneField(
        Utilisateur, 
        on_delete=models.CASCADE, 
        primary_key=True,
        db_column='id',  # <-- CHANGEMENT ICI
        related_name='etudiant_profile'
    )
    # CHANGEMENT: db_column='promotion_id'
    promotion = models.ForeignKey(
        Promotion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_column='promotion_id',  # <-- CHANGEMENT ICI
        related_name='etudiants'
    )
    code_etudiant = models.CharField(max_length=50, unique=True)
    
    # CHANGEMENT: On garde le champ mais avec une logique différente
    dernier_seuil_alerte = models.IntegerField(default=0, db_column='dernier_seuil_alerte')
    
    class Meta:
        db_table = 'etudiant'
        verbose_name = 'Étudiant'
        verbose_name_plural = 'Étudiants'
        indexes = [
            models.Index(fields=['code_etudiant']),
            models.Index(fields=['dernier_seuil_alerte']),
        ]
    
    def __str__(self):
        return f"{self.code_etudiant} - {self.utilisateur.prenom} {self.utilisateur.nom}"
    
    # Propriété pour accéder à l'ID utilisateur facilement
    @property
    def id(self):
        return self.utilisateur.id
<<<<<<< HEAD
    
    # AJOUT: Méthode pour compter les absences
    def compter_absences(self):
        """Retourne le nombre total d'absences (justifiées + non justifiées)"""
        return self.presences.filter(
            statut__in=['ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE']
        ).count()
    
    # MODIFICATION: Méthode simplifiée pour vérifier et créer des alertes
    def verifier_et_creer_alerte_absences(self, presence_id=None):
        """
        Vérifie si l'étudiant dépasse 3 absences et crée une notification
        """
        from django.utils import timezone
        
        total_absences = self.compter_absences()
        
        # SEUIL FIXE: 3 absences
        seuil = 3
        
        # Vérifier si l'étudiant dépasse 3 absences
        if total_absences > seuil:
            # Vérifier s'il a déjà reçu une alerte pour ce nombre d'absences
            if self.dernier_seuil_alerte < total_absences:
                
                # Construire le message
                message =  f"Vous avez dépassé le nombre d'absences autorisé.\n"
                message += f"Vous avez atteint {total_absences} absences.\n"
                message += f"Vous devez contacter rapidement l'administration."
                
               
                
                # Créer la notification
                Notification.objects.create(
                    etudiant=self,
                    message=message,
                    type_notification='ALERTE_ABSENCES',
                    lu=False
                )
                
                # Mettre à jour le dernier seuil d'alerte avec le nombre actuel d'absences
                self.dernier_seuil_alerte = total_absences
                self.save(update_fields=['dernier_seuil_alerte'])
                
                print(f"Alerte créée pour {self.code_etudiant} : {total_absences} absences")
                return True
        
        return False
=======
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0


# ============================================
# Modèle: Groupe
# ============================================
class Groupe(models.Model):
    nom = models.CharField(max_length=100)
    # CHANGEMENT: db_column='promotion_id'
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, db_column='promotion_id', related_name='groupes')
    
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
    # CHANGEMENTS: Ajout de db_column
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, db_column='etudiant_id')
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, db_column='groupe_id')
    
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
    # CHANGEMENT: db_column='professeur_id'
    professeur = models.ForeignKey(
        Professeur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_column='professeur_id',  # <-- CHANGEMENT ICI
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
    # CHANGEMENT: db_column='administrateur_id'
    administrateur = models.ForeignKey(
        Administrateur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_column='administrateur_id',  # <-- CHANGEMENT ICI
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
    # CHANGEMENTS: db_column pour toutes les clés étrangères
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, db_column='cours_id', related_name='seances')
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, db_column='groupe_id', related_name='seances')
    planning = models.ForeignKey(Planning, on_delete=models.CASCADE, db_column='planning_id', related_name='seances')
    
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
    STATUT_JUSTIFICATION_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('ACCEPTEE', 'Acceptée'),
        ('REFUSEE', 'Refusée'),
    ]
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES)
    justification = models.TextField(blank=True, null=True)
    fichier_justificatif = models.BinaryField(blank=True, null=True)
<<<<<<< HEAD
    statut_justification = models.CharField(
=======
    statut_justification = models.CharField(  # NOUVEAU: statut de validation
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
        max_length=20, 
        choices=STATUT_JUSTIFICATION_CHOICES, 
        default='EN_ATTENTE',
        blank=True,
        null=True
    )
    date_saisie = models.DateTimeField(auto_now_add=True)
<<<<<<< HEAD
    
    # AJOUT: Champ pour suivre si une notification d'absence a été créée
    notification_absence_cree = models.BooleanField(default=False, db_column='notification_absence_cree')
    
=======
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
    # CHANGEMENTS: db_column pour les clés étrangères
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, db_column='etudiant_id', related_name='presences')
    seance = models.ForeignKey(Seance, on_delete=models.CASCADE, db_column='seance_id', related_name='presences')
    
    class Meta:
        db_table = 'presence'
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        unique_together = ('etudiant', 'seance')
        indexes = [
            models.Index(fields=['etudiant']),
            models.Index(fields=['seance']),
            models.Index(fields=['statut']),
<<<<<<< HEAD
            models.Index(fields=['statut_justification']),
            models.Index(fields=['notification_absence_cree']),
=======
             models.Index(fields=['statut_justification']),
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
        ]
    
    def __str__(self):
        return f"{self.etudiant.code_etudiant} - {self.seance.cours.code} - {self.statut}"
    
    def save(self, *args, **kwargs):
        # Sauvegarder les anciennes valeurs pour comparaison
        if self.pk:
            try:
                old_instance = Presence.objects.get(pk=self.pk)
                self._old_statut = old_instance.statut
                self._old_statut_justification = old_instance.statut_justification
            except Presence.DoesNotExist:
                self._old_statut = None
                self._old_statut_justification = None
        else:
            self._old_statut = None
            self._old_statut_justification = None
        
        # Sauvegarder d'abord pour avoir un ID
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Si c'est une NOUVELLE absence, créer une notification et vérifier les alertes
        if is_new and self.statut in ['ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE']:
            self.creer_notification_absence()
            # Vérifier si l'étudiant dépasse 3 absences
            self.etudiant.verifier_et_creer_alerte_absences(self.id)
        
        # Si le statut CHANGE vers une absence, vérifier aussi
        elif not is_new and self._old_statut != self.statut:
            if self.statut in ['ABSENT_JUSTIFIE', 'ABSENT_NON_JUSTIFIE']:
                # Vérifier si une notification existe déjà
                if not self.notification_absence_cree:
                    self.creer_notification_absence()
                # Vérifier si l'étudiant dépasse 3 absences
                self.etudiant.verifier_et_creer_alerte_absences(self.id)
        
        # Si le statut de justification a changé, mettre à jour la notification
        elif not is_new and hasattr(self, '_old_statut_justification'):
            if self._old_statut_justification != self.statut_justification:
                self.mettre_a_jour_notification_justification()
    
    def creer_notification_absence(self):
        """Crée une notification automatique pour une absence"""
        try:
            # Construire le message selon le type d'absence
            date_cours = self.seance.date.strftime("%d/%m/%Y")
            cours = self.seance.cours.libelle
            horaire = f"{self.seance.heure_debut.strftime('%H:%M')}-{self.seance.heure_fin.strftime('%H:%M')}"
            salle = f" en salle {self.seance.salle}" if self.seance.salle else ""
            
            if self.statut == 'ABSENT_JUSTIFIE':
                if self.statut_justification == 'EN_ATTENTE':
                    message = f"⏳ Vous avez une absence justifiée en attente de validation pour le cours '{cours}' du {date_cours}."
                    type_notif = 'ABSENCE'
                elif self.statut_justification == 'ACCEPTEE':
                    message = f"✅ Votre justification pour le cours '{cours}' du {date_cours} a été acceptée."
                    type_notif = 'JUSTIFICATION_ACCEPTEE'
                elif self.statut_justification == 'REFUSEE':
                    message = f"❌ Votre justification pour le cours '{cours}' du {date_cours} a été refusée."
                    type_notif = 'JUSTIFICATION_REFUSEE'
                else:
                    message = f"📝 Vous avez une absence justifiée pour le cours '{cours}' du {date_cours}."
                    type_notif = 'ABSENCE'
            else:  # ABSENT_NON_JUSTIFIE
                message = f"⚠️ Vous avez une absence non justifiée au cours de '{cours}' du {date_cours}."
                type_notif = 'ABSENCE'
            
            # Ajouter les détails
            message += f" Horaire: {horaire}{salle}"
            
            # Créer la notification
            Notification.objects.create(
                etudiant=self.etudiant,
                presence=self,
                message=message,
                type_notification=type_notif,
                lu=False
            )
            
            # Marquer que la notification a été créée
            self.notification_absence_cree = True
            Presence.objects.filter(pk=self.pk).update(notification_absence_cree=True)
            
            print(f"Notification créée pour absence ID {self.id}")
            
        except Exception as e:
            print(f"Erreur création notification: {str(e)}")
    
    def mettre_a_jour_notification_justification(self):
        """Met à jour la notification quand une justification est traitée"""
        try:
            # Trouver la notification existante pour cette présence
            notification = Notification.objects.filter(
                presence=self,
                type_notification='ABSENCE'
            ).first()
            
            if notification and self.statut_justification in ['ACCEPTEE', 'REFUSEE']:
                date_cours = self.seance.date.strftime("%d/%m/%Y")
                cours = self.seance.cours.libelle
                
                if self.statut_justification == 'ACCEPTEE':
                    nouveau_message = f"✅ Votre justification pour le cours '{cours}' du {date_cours} a été acceptée."
                    nouveau_type = 'JUSTIFICATION_ACCEPTEE'
                else:
                    nouveau_message = f"❌ Votre justification pour le cours '{cours}' du {date_cours} a été refusée."
                    nouveau_type = 'JUSTIFICATION_REFUSEE'
                
                # Mettre à jour la notification existante
                notification.message = nouveau_message
                notification.type_notification = nouveau_type
                notification.lu = False  # Marquer comme non lue
                notification.save()
                
                print(f"Notification mise à jour pour présence ID {self.id}")
            
        except Exception as e:
            print(f"Erreur mise à jour notification: {str(e)}")


# ============================================
# Modèle: Notification
# ============================================
class Notification(models.Model):
    TYPE_CHOICES = [
        ('ABSENCE', 'Notification d\'absence'),
        ('JUSTIFICATION_ACCEPTEE', 'Justification acceptée'),
        ('JUSTIFICATION_REFUSEE', 'Justification refusée'),
        ('ALERTE_ABSENCES', 'Alerte nombre d\'absences'),  # <-- MODIFIÉ: type unique pour toutes les alertes
        ('AUTRE', 'Autre'),
    ]
    
    message = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
<<<<<<< HEAD
    
    # AJOUT: Type de notification
    type_notification = models.CharField(
        max_length=30, 
        choices=TYPE_CHOICES, 
        default='ABSENCE',
        db_column='type_notification'
    )
    
=======
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
    # CHANGEMENTS: db_column pour les clés étrangères
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE, db_column='etudiant_id', related_name='notifications')
    presence = models.ForeignKey(
        Presence, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
<<<<<<< HEAD
        db_column='presence_id',
=======
        db_column='presence_id',  # <-- CHANGEMENT ICI
>>>>>>> 2e85289e870c9bb608dfa9d388270d523a561fa0
        related_name='notifications'
    )
    
    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['etudiant']),
            models.Index(fields=['type_notification']),
            models.Index(fields=['lu']),
        ]
        ordering = ['-date_envoi']
    
    def __str__(self):
        return f"Notification pour {self.etudiant.code_etudiant} - {'Lu' if self.lu else 'Non lu'}"