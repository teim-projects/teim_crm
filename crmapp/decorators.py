# decorators.py

from functools import wraps
from django.http import HttpResponseForbidden

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.is_active and hasattr(request.user, 'userprofile'):
                if request.user.userprofile.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Access denied. Account is inactive or disabled.")
        return wrapper
    return decorator
