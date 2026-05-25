from django.contrib import admin

from apps.users.models import Library, MemberProfile, StaffProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "phone_number", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "name", "sso_id")
    list_filter = ("is_active", "is_staff")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "sso_id", "date_joined", "created_at", "updated_at")


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type")
    search_fields = ("code", "name")
    list_filter = ("type",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "identity_number", "member_type", "member_level", "is_verified")
    search_fields = ("user__email", "user__name", "identity_number")
    list_filter = ("member_type", "member_level")
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(boolean=True, description="Verified")
    def is_verified(self, obj):
        return obj.is_verified


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "library", "role")
    search_fields = ("user__email", "user__name")
    list_filter = ("role", "library")
    readonly_fields = ("id", "created_at", "updated_at")
