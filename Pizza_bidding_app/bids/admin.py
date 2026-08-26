import secrets

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Season, Game, Provider, Invitation, Bid


DATETIME_INPUT_FORMAT = "%Y-%m-%dT%H:%M"


class InvitationAdminForm(forms.ModelForm):
    expires_at = forms.DateTimeField(
        required=True,
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(
            format=DATETIME_INPUT_FORMAT,
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    class Meta:
        model = Invitation
        fields = "__all__"


class SeasonAdminForm(forms.ModelForm):
    bid_open = forms.DateTimeField(
        required=True,
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(
            format=DATETIME_INPUT_FORMAT,
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    bid_close = forms.DateTimeField(
        required=True,
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(
            format=DATETIME_INPUT_FORMAT,
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    class Meta:
        model = Season
        fields = "__all__"


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    form = SeasonAdminForm

    list_display = (
        "name",
        "year",
        "number_of_games",
        "pizza_budget_per_game",
        "bid_open",
        "bid_close",
        "is_active",
    )


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "season",
        "game_number",
        "date",
        "opponent",
        "pizza_quantity",
        "location",
    )
    list_filter = ("season",)


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "contact_name",
        "email",
        "is_active",
        "user",
    )
    search_fields = (
        "company_name",
        "contact_name",
        "email",
    )


@admin.action(description="Send invitation email to selected providers")
def send_invitations(modeladmin, request, queryset):
    sent = 0

    for invitation in queryset.select_related("provider", "season"):
        if not invitation.provider.is_active:
            continue

        if invitation.accepted_at:
            continue

        invitation.token = secrets.token_urlsafe(32)
        invitation.sent_at = timezone.now()

        # IMPORTANT:
        # Do NOT modify expires_at here.
        invitation.save(update_fields=["token", "sent_at"])

        url = request.build_absolute_uri(
            reverse(
                "invitation",
                kwargs={"token": invitation.token},
            )
        )

        subject = f"Invitation to bid — {invitation.season.name}"

        body = (
            f"Hello {invitation.provider.contact_name},\n\n"
            f"You have been invited to submit pizza bids for "
            f"{invitation.season.name}.\n\n"
            f"Company: {invitation.provider.company_name}\n"
            f"Season bid deadline: "
            f"{timezone.localtime(invitation.season.bid_close):%B %d, %Y at %I:%M %p}\n"
            f"Invitation expires: "
            f"{timezone.localtime(invitation.expires_at):%B %d, %Y at %I:%M %p}\n\n"
            f"Use the secure invitation link below to activate "
            f"your provider account:\n\n"
            f"{url}\n\n"
            "Do not share this invitation link.\n\n"
            "Thank you."
        )

        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [invitation.provider.email],
            fail_silently=False,
        )

        sent += 1

    modeladmin.message_user(
        request,
        f"Sent {sent} invitation(s).",
        messages.SUCCESS,
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    form = InvitationAdminForm

    list_display = (
        "season",
        "provider",
        "sent_at",
        "accepted_at",
        "expires_at",
        "status",
        "invitation_url",
    )

    list_filter = (
        "season",
        "accepted_at",
    )

    actions = [send_invitations]

    readonly_fields = (
        "token",
        "sent_at",
        "accepted_at",
        "invitation_url",
    )

    @admin.display(description="Status")
    def status(self, obj):
        if obj.accepted_at:
            return "Accepted"

        if obj.expires_at and timezone.now() >= obj.expires_at:
            return "Expired"

        if obj.sent_at:
            return "Sent"

        return "Not sent"

    @admin.display(description="Invitation URL")
    def invitation_url(self, obj):
        if not obj.token:
            return "No token"

        url = f"http://127.0.0.1:8000/invite/{obj.token}/"

        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url,
            url,
        )

    def save_model(self, request, obj, form, change):
        if not obj.token:
            obj.token = secrets.token_urlsafe(32)

        super().save_model(request, obj, form, change)


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = (
        "game",
        "provider",
        "total",
        "status",
        "submitted_at",
    )

    list_filter = (
        "status",
        "game__season",
    )

    search_fields = (
        "provider__company_name",
        "game__opponent",
    )
