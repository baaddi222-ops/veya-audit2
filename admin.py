from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm

from .models import User


class EmailUserCreationForm(UserCreationForm):
    """Django's stock UserCreationForm is bound to a `username` field,
    which this custom user model does not have — using it unchanged raises
    FieldError on the admin 'add user' page."""

    class Meta:
        model = User
        fields = ('email',)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = EmailUserCreationForm
    ordering = ['email']
    list_display = ['email', 'is_active', 'is_staff', 'date_joined']
    # date_joined is auto_now_add (non-editable) → must be read-only here.
    readonly_fields = ['date_joined', 'last_login']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),
    )
    search_fields = ['email']
