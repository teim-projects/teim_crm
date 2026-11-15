import re
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib import messages
from .decorators import is_admin_or_superadmin


class AdminOnlyDeleteMiddleware:
    """
    Global security middleware:
    Ensures ONLY Admin (role == 'admin') or Super Admin (is_superuser == True)
    can execute ANY delete operation in the entire CRM.
    All other roles attempting deletion are immediately blocked with a 403 / error message.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.delete_pattern = re.compile(r'(?:^|/|[_-])delete(?:$|/|[_-])', re.IGNORECASE)

    def __call__(self, request):
        path = request.path_info

        # Check if HTTP method is DELETE or if URL path matches a delete route
        is_delete_action = (request.method == 'DELETE') or bool(self.delete_pattern.search(path))

        if is_delete_action:
            user = getattr(request, 'user', None)

            # Check if user has Admin or Super Admin rights
            if not is_admin_or_superadmin(user):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': 'Permission denied: Only Admin or Super Admin are authorized to delete records from the system.'
                    }, status=403)

                messages.error(request, "Permission denied: Only Admin or Super Admin are authorized to delete records from the system.")
                referer = request.META.get('HTTP_REFERER')
                if referer and referer != request.build_absolute_uri():
                    return redirect(referer)
                return redirect('/')

        return self.get_response(request)
