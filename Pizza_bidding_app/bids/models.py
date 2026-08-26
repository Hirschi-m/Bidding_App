from django.conf import settings
from django.db import models
from django.utils import timezone


class Season(models.Model):
    name = models.CharField(max_length=120)
    year = models.PositiveIntegerField()
    number_of_games = models.PositiveIntegerField(default=10)
    pizza_budget_per_game = models.DecimalField(max_digits=10, decimal_places=2, default=350)
    season_budget = models.DecimalField(max_digits=10, decimal_places=2, default=3500)
    bid_open = models.DateTimeField()
    bid_close = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.year})"

    @property
    def bidding_open(self):
        return self.is_active and self.bid_open <= timezone.now() < self.bid_close


class Game(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="games")
    game_number = models.PositiveIntegerField()
    date = models.DateField()
    opponent = models.CharField(max_length=120)
    location = models.CharField(max_length=200, blank=True)
    pizza_quantity = models.PositiveIntegerField(default=20)
    delivery_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["season", "game_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "game_number"], name="unique_game_per_season"
            )
        ]

    def __str__(self):
        return f"{self.season.year} Game {self.game_number}: {self.opponent}"


class Provider(models.Model):
    company_name = models.CharField(max_length=160)
    contact_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pizza_provider",
    )

    def __str__(self):
        return self.company_name


class Invitation(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="invitations")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="invitations")
    token = models.CharField(max_length=64, unique=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["season", "provider"], name="unique_season_provider_invitation"
            )
        ]

    @property
    def is_usable(self):
        return (
            self.accepted_at is None
            and self.provider.is_active
            and (self.expires_at is None or timezone.now() < self.expires_at)
        )

    def __str__(self):
        return f"{self.provider} — {self.season}"


class Bid(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("withdrawn", "Withdrawn"),
    ]
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="bids")
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="bids")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["game", "provider"], name="one_bid_per_provider_per_game"
            )
        ]
        ordering = ["total", "submitted_at"]
