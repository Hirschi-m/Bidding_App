from decimal import Decimal
import secrets

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BidForm, ProviderActivationForm
from .models import Bid, Game, Invitation, Provider, Season


def home(request):
    games = (
        Game.objects.filter(
            season__is_active=True
        )
        .select_related("season")
        .order_by("season__year", "game_number")
    )

    return render(
        request,
        "home.html",
        {"games": games},
    )


def provider_for(request):
    try:
        provider = request.user.pizza_provider
    except (AttributeError, Provider.DoesNotExist):
        raise Http404("Provider account not configured.")

    if not provider.is_active:
        raise Http404("Provider account is inactive.")

    return provider


def invitation(request, token):
    invite = get_object_or_404(
        Invitation.objects.select_related(
            "provider",
            "season",
        ),
        token=token,
    )

    if invite.accepted_at:
        return render(
            request,
            "registration/invitation_invalid.html",
            {
                "title": "Invitation already accepted",
                "message": (
                    "This invitation has already been used. "
                    "Please use the Provider Login page instead."
                ),
            },
        )

    if not invite.is_usable:
        return render(
            request,
            "registration/invitation_invalid.html",
            {
                "title": "Invitation expired",
                "message": (
                    "This invitation is no longer valid. "
                    "Please contact the football program administrator "
                    "for a new invitation."
                ),
            },
        )

    if request.method == "POST":
        form = ProviderActivationForm(request.POST)

        if form.is_valid():
            provider = invite.provider
            user = provider.user

            if user is None:
                username = (
                    f"provider_{provider.pk}_{secrets.token_hex(8)}"
                )

                user = User(
                    username=username,
                    email=provider.email,
                )

                provider.user = user

            user.email = provider.email
            user.first_name = provider.contact_name
            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            user.save()

            invite.accepted_at = timezone.now()
            invite.save(update_fields=["accepted_at"])

            provider.save(update_fields=["user"])

            login(request, user)

            messages.success(
                request,
                (
                    "Your provider account is ready. "
                    "Welcome to the pizza bidding portal."
                ),
            )

            return redirect("home")

    else:
        form = ProviderActivationForm()

    return render(
        request,
        "registration/invitation.html",
        {
            "form": form,
            "invitation": invite,
        },
    )


@login_required
def submit_bid(request, game_id):
    provider = provider_for(request)

    game = get_object_or_404(
        Game.objects.select_related("season"),
        pk=game_id,
    )

    season = game.season

    # Provider must have an accepted invitation for this season.
    if not Invitation.objects.filter(
        season=season,
        provider=provider,
        accepted_at__isnull=False,
    ).exists():
        messages.error(
            request,
            "You are not authorized to bid for this season.",
        )
        return redirect("home")

    # The season's bid window controls whether a new bid can be submitted.
    if not season.bidding_open:
        messages.error(
            request,
            "Bidding is currently closed for this game.",
        )
        return redirect("home")

    # Look for an existing bid from this provider for this game.
    bid = Bid.objects.filter(
        game=game,
        provider=provider,
    ).first()

    # A submitted bid is final and cannot be changed.
    if bid and bid.status == "submitted":
        return render(
            request,
            "bids/submit_bid.html",
            {
                "game": game,
                "bid": bid,
                "submitted": True,
            },
        )

    # This should normally only occur for a future draft-based workflow.
    # For now, an existing non-submitted bid can be reused.
    if bid is None:
        bid = Bid(
            game=game,
            provider=provider,
            subtotal=Decimal("0.00"),
            total=Decimal("0.00"),
        )

    if request.method == "POST":
        form = BidForm(
            request.POST,
            instance=bid,
        )

        if form.is_valid():
            bid = form.save(commit=False)

            # Set ownership explicitly on the server.
            bid.game = game
            bid.provider = provider

            # Form.save() calculates total and sets status.
            bid.submitted_at = timezone.now()

            bid.save()

            messages.success(
                request,
                "Your sealed bid has been submitted and locked.",
            )

            return redirect("my_bids")

    else:
        form = BidForm(instance=bid)

    return render(
        request,
        "bids/submit_bid.html",
        {
            "form": form,
            "game": game,
            "bid": bid,
            "submitted": False,
        },
    )


@login_required
def my_bids(request):
    provider = provider_for(request)

    bids = (
        Bid.objects.filter(provider=provider)
        .select_related(
            "game",
            "game__season",
        )
        .order_by(
            "-game__season__year",
            "game__game_number",
        )
    )

    return render(
        request,
        "bids/my_bids.html",
        {
            "bids": bids,
        },
    )


@staff_member_required
def admin_dashboard(request):
    seasons = Season.objects.all().order_by(
        "-year",
        "-id",
    )

    season_rows = []

    for season in seasons:
        games = list(season.games.all())

        submitted = Bid.objects.filter(
            game__season=season,
            status="submitted",
        ).count()

        season_rows.append(
            {
                "season": season,
                "game_count": len(games),
                "bid_count": submitted,
                "providers": Invitation.objects.filter(
                    season=season,
                    accepted_at__isnull=False,
                ).count(),
            }
        )

    return render(
        request,
        "dashboard/index.html",
        {
            "season_rows": season_rows,
        },
    )


@staff_member_required
def admin_season_dashboard(request, season_id):
    season = get_object_or_404(
        Season,
        pk=season_id,
    )

    games = list(season.games.all())

    invitations = list(
        Invitation.objects.filter(
            season=season
        )
        .select_related("provider")
        .order_by("provider__company_name")
    )

    game_rows = []

    for game in games:
        bids = list(
            Bid.objects.filter(
                game=game,
                status="submitted",
            )
            .select_related("provider")
            .order_by(
                "total",
                "submitted_at",
            )
        )

        lowest = bids[0].total if bids else None

        average = (
            sum(
                (b.total for b in bids),
                Decimal("0.00"),
            )
            / len(bids)
            if bids
            else None
        )

        game_rows.append(
            {
                "game": game,
                "bids": bids,
                "lowest": lowest,
                "average": average,
                "budget": season.pizza_budget_per_game,
            }
        )

    season_bids = []

    for invitation in invitations:
        provider = invitation.provider

        provider_bids = list(
            Bid.objects.filter(
                game__season=season,
                provider=provider,
                status="submitted",
            )
        )

        total = sum(
            (b.total for b in provider_bids),
            Decimal("0.00"),
        )

        season_bids.append(
            {
                "provider": provider,
                "bid_count": len(provider_bids),
                "total": total,
            }
        )

    season_bids.sort(
        key=lambda row: (
            row["bid_count"] == 0,
            row["total"],
        )
    )

    return render(
        request,
        "dashboard/season.html",
        {
            "season": season,
            "game_rows": game_rows,
            "invitations": invitations,
            "season_bids": season_bids,
        },
    )

