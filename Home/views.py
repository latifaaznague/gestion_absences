from django.shortcuts import redirect

def index(request):
    # CORRECTION : Utilisez l'URL correcte
    return redirect("/accounts/login/")  # URL directe
    
    # OU si vous avez bien configuré le namespace accounts :
    # return redirect("accounts:login_page")