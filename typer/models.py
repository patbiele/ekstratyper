# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils.encoding import python_2_unicode_compatible
from pytz import timezone as tz
from django.http import request

class User(AbstractUser):
    alias = models.CharField(max_length=50, null=True, blank=True)

    def get_display_name(self):
        return self.alias if self.alias is not None and self.alias != '' else self.username

    def __str__(self):
        return self.get_display_name()

@python_2_unicode_compatible
class League(models.Model):
    league_name = models.CharField(max_length=50)

    def __str__(self):
        return self.league_name

@python_2_unicode_compatible
class Team(models.Model):
    team_name = models.CharField(max_length=50)
    league = models.ForeignKey(League)
    short_name = models.CharField(max_length=5, default='XXX')

    def __str__(self):
        return self.team_name

@python_2_unicode_compatible
class Group(models.Model):
    group_name = models.CharField(max_length=50)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    group_admin = models.ForeignKey(User)
    is_vote = models.BooleanField(default=False)
    bets_per_round = models.SmallIntegerField(default=1)

    def __str__(self):
        ans = self.group_name
        if self.is_vote: ans += ' - z systemem głosowania'
        return ans

@python_2_unicode_compatible
class MemberGroup(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return (str(self.group)+" - "+str(self.member))

@python_2_unicode_compatible
class Game(models.Model):
    game_date = models.DateTimeField()
    home_team = models.ForeignKey(Team, related_name='home_team')
    away_team = models.ForeignKey(Team, related_name='away_team')
    score_home = models.PositiveSmallIntegerField(null=True, blank=True)
    score_away = models.PositiveSmallIntegerField(null=True, blank=True)
    round = models.PositiveSmallIntegerField(null=True,default=0)
    league = models.ForeignKey(League, on_delete=models.CASCADE, null=True)

    def __getitem__(self, item):
        return self.item

    def is_game_soon(self, days=4):
        #return True if game start in at least x (4) days
        return self.game_date < timezone.now() + datetime.timedelta(days=days) and self.game_date > timezone.now()

    def was_game_finished(self):
        #return True if at least 2 hours past from game start(2 hours for sake of simplicity)
        return self.game_date <= timezone.now() - datetime.timedelta(hours=2)

    def was_game_started(self):
        #return True if game start time passed
        return self.game_date <= timezone.now()

    def __str__(self):
        ans = str(self.home_team)+' '
        ans += str(self.score_home) if self.score_home is not None else '-'
        ans += ':'
        ans += str(self.score_away) if self.score_away is not None else '-'
        ans += ' '+str(self.away_team)
        return ans

class Bet(models.Model):
    bettor = models.ForeignKey(User)
    game = models.ForeignKey(Game)
    group = models.ForeignKey(Group)
    home_bet = models.PositiveSmallIntegerField()
    away_bet = models.PositiveSmallIntegerField()
    is_risk = models.BooleanField(default=False)
    is_bonus = models.BooleanField(default=False)
    points = models.SmallIntegerField(null=True,blank=True,default=None)

    def __str__(self):
        ans = str(self.bettor)+' '
        ans += str(self.home_bet)+':'+str(self.away_bet) if self.home_bet and self.away_bet else '-:-'
        ans += ' pkt:'+str(self.points) if self.points else ' pkt brak'
        if self.is_risk: ans += ' no i pewniak!'
        return ans

class Votes(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    voter = models.ForeignKey(User, on_delete=models.CASCADE,default=None)

class BonusRound(models.Model):
    is_bonus = models.BooleanField(default=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    round = models.PositiveSmallIntegerField(null=True,blank=True,default=None)

class DefaultTeamGroup(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

class TeamPlace(models.Model):
    team = models.ForeignKey(Team)
    points = models.SmallIntegerField()
    season = models.SmallIntegerField()

    def __str__(self):
        return str(self.team)+' - '+str(self.points)