from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Direction, Management, Coordination, PasswordResetToken


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ["email", "name", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff", "direction"]
    search_fields = ["email", "name"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações Pessoais", {"fields": ("name", "role", "cpf", "phone", "avatar")}),
        ("Organização", {"fields": ("direction", "management", "coordination")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "role", "password1", "password2", "is_active", "is_staff"),
        }),
    )


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


@admin.register(Management)
class ManagementAdmin(admin.ModelAdmin):
    list_display = ["name", "direction", "is_active"]
    list_filter = ["direction"]
    search_fields = ["name"]


@admin.register(Coordination)
class CoordinationAdmin(admin.ModelAdmin):
    list_display = ["name", "management", "is_active"]
    list_filter = ["management__direction", "management"]
    search_fields = ["name"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token_short", "created_at", "expires_at", "is_used", "is_valid_status"]
    list_filter = ["is_used", "created_at"]
    search_fields = ["user__email", "user__name", "token", "ip_address"]
    readonly_fields = ["user", "token", "created_at", "expires_at", "is_used", "used_at", "ip_address"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def token_short(self, obj):
        return f"{obj.token[:12]}..."
    token_short.short_description = "Token"

    def is_valid_status(self, obj):
        if obj.is_used:
            return "❌ Usado"
        elif obj.is_valid():
            return "✅ Válido"
        else:
            return "⏰ Expirado"
    is_valid_status.short_description = "Status"

    def has_add_permission(self, request):
        # Tokens são criados apenas via service
        return False

    def has_change_permission(self, request, obj=None):
        # Tokens não podem ser editados
        return False
