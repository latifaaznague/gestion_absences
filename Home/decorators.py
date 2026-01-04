from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from functools import wraps

def auth_required_django(roles=None):
    def decorator(view):
        def wrapper(request, *args, **kwargs):
            if not request.session.get("rpc_token"):
                # URL directe - plus sûr
                return redirect("/accounts/login/")  # <-- SIMPLE ET FIABLE
            
            if roles:
                role = request.session.get("role")
                if role not in roles:
                    return HttpResponseForbidden()
            
            return view(request, *args, **kwargs)
        return wrapper
    return decorator