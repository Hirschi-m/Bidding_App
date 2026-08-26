from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("invite/<str:token>/", views.invitation, name="invitation"),
    path("games/<int:game_id>/bid/", views.submit_bid, name="submit_bid"),
    path("my-bids/", views.my_bids, name="my_bids"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/season/<int:season_id>/", views.admin_season_dashboard, name="admin_season_dashboard"),
]
