# decorators.py

from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.contrib import messages


def is_admin_or_superadmin(user):
    """
    Check if the user is authenticated, active, and has Admin or Super Admin privileges.
    Returns True for Django superusers or users whose UserProfile role is 'admin'.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    profile = getattr(user, 'userprofile', None)
    if profile and str(getattr(profile, 'role', '')).strip().lower() == 'admin':
        return True
    return False


def admin_or_superadmin_required(view_func):
    """
    Decorator to restrict access strictly to Admin or Super Admin users.
    Any other role attempting access is blocked and notified.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if is_admin_or_superadmin(request.user):
            return view_func(request, *args, **kwargs)

        # AJAX / JSON response
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': False,
                'error': 'Permission denied: Only Admin or Super Admin are authorized to perform delete operations.'
            }, status=403)

        messages.error(request, "Permission denied: Only Admin or Super Admin are authorized to perform delete operations.")
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('/')

    return wrapper


def role_required(allowed_roles=[]):
    """
    Decorator checking allowed roles. Superusers are automatically granted access.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.is_active:
                if request.user.is_superuser:
                    return view_func(request, *args, **kwargs)
                profile = getattr(request.user, 'userprofile', None)
                if profile and profile.role in allowed_roles:
                    return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Access denied. Account is inactive or disabled.")
        return wrapper
    return decorator
