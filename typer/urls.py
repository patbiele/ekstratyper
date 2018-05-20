from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^login/$', views.login, {'template_name': 'auth/login.html'}, name='login'),
    url(r'^logout/$', auth_views.logout_then_login, name='logout'),
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^league/(?P<league_id>[0-9]+)/$', views.league, name='league'),
    url(r'^group/(?P<group_id>[0-9]+)/$', views.group, name='group'),
    url(r'^bets/game/(?P<group_id>[0-9]+)/(?P<game_id>[0-9]+)$', views.bets_single_game, name='bets/game'),
    url(r'^bets/round/(?P<group_id>[0-9]+)/(?P<round>[0-9]+)$', views.bets_single_round, name='bets/round'),
    url(r'^bets/all/(?P<group_id>[0-9]+)$', views.bets_all, name='bets/all'),
    url(r'^bets/member/(?P<group_id>[0-9]+)/(?P<member_id>[0-9]+)$', views.bets_single_member, name='bets/member'),
    url(r'^bets/stats/(?P<group_id>[0-9]+)$', views.bets_stats, name='bets'),
    url(r'^bet/(?P<round>[0-9]+)/(?P<group_id>[0-9]+)$', views.bet, name='bet'),
    url(r'^vote/(?P<round>[0-9]+)/(?P<group_id>[0-9]+)$', views.vote, name='vote'),
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^profile/pass$', views.password_change, name='profile/pass'),
    url(r'^profile/alias$', views.alias_change, name='profile/alias'),
]