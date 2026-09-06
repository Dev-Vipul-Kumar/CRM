from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """Allow only Admin role users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.role != request.user.Role.ADMIN:
            messages.error(request, "You do not have permission to access this page.")
            return redirect("dashboard:index")
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    """Allow Admin and Manager role users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.role not in (
            request.user.Role.ADMIN,
            request.user.Role.MANAGER,
        ):
            messages.error(request, "You do not have permission to access this page.")
            return redirect("dashboard:index")
        return view_func(request, *args, **kwargs)
    return wrapper


def roles_required(*roles):
    """Allow specific roles. Usage: @roles_required('ADMIN', 'MANAGER')"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if request.user.role not in roles:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("dashboard:index")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
