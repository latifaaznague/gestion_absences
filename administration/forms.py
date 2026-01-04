from django import forms

class AdminProfileForm(forms.Form):
    nom = forms.CharField(max_length=50, label="Nom")
    prenom = forms.CharField(max_length=50, label="Prénom")
    email = forms.EmailField(label="Email")
    password = forms.CharField(
        widget=forms.PasswordInput, 
        required=False, 
        label="Nouveau mot de passe"
    )
