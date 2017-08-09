# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import *

class TeamAdmin(admin.ModelAdmin):
    list_display = ('team_name','short_name','league')

class UserAdmin(admin.ModelAdmin):
    list_display = ('username','alias', 'last_login', 'is_active', 'is_superuser')

class BetAdmin(admin.ModelAdmin):
    list_display = ('bettor', 'home_bet', 'away_bet', 'is_risk', 'points', 'game')

class GameAdmin(admin.ModelAdmin):
    list_display = ('game_date','home_team', 'score_home', 'score_away', 'away_team')
    ordering = ('game_date',)

admin.site.register(User, UserAdmin)
admin.site.register(League)
admin.site.register(Team, TeamAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(Group)
admin.site.register(Bet, BetAdmin)
admin.site.register(MemberGroup)
admin.site.register(TeamPlace)