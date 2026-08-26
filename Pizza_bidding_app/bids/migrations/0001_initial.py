from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Season",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("year", models.PositiveIntegerField()),
                ("number_of_games", models.PositiveIntegerField(default=10)),
                ("pizza_budget_per_game", models.DecimalField(decimal_places=2, default=350, max_digits=10)),
                ("season_budget", models.DecimalField(decimal_places=2, default=3500, max_digits=10)),
                ("bid_open", models.DateTimeField()),
                ("bid_close", models.DateTimeField()),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Provider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_name", models.CharField(max_length=160)),
                ("contact_name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pizza_provider", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Game",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("game_number", models.PositiveIntegerField()),
                ("date", models.DateField()),
                ("opponent", models.CharField(max_length=120)),
                ("location", models.CharField(blank=True, max_length=200)),
                ("pizza_quantity", models.PositiveIntegerField(default=20)),
                ("delivery_time", models.TimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="games", to="bids.season")),
            ],
            options={
                "ordering": ["season", "game_number"],
                "constraints": [models.UniqueConstraint(fields=("season", "game_number"), name="unique_game_per_season")],
            },
        ),
        migrations.CreateModel(
            name="Invitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=64, unique=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="bids.provider")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="bids.season")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("season", "provider"), name="unique_season_provider_invitation")],
            },
        ),
        migrations.CreateModel(
            name="Bid",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=10)),
                ("delivery_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("tax", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("withdrawn", "Withdrawn")], default="draft", max_length=20)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bids", to="bids.game")),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bids", to="bids.provider")),
            ],
            options={
                "ordering": ["total", "submitted_at"],
                "constraints": [models.UniqueConstraint(fields=("game", "provider"), name="one_bid_per_provider_per_game")],
            },
        ),
    ]
