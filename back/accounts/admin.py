from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Direction, Management, Coordination


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ["email", "name", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff", "direction"]
    search_fields = ["email", "name"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações Pessoais", {"fields": ("name", "cpf", "phone", "avatar")}),
        ("Organização", {"fields": ("direction", "management", "coordination")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "is_active", "is_staff"),
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
