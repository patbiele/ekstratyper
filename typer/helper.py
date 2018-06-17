# -*- coding: utf-8 -*-

from django.db.models import Q, Count, Sum
from django.shortcuts import redirect
import requests as req
from .models import *

def risk_handler(new_bet=None, old_bet=None):
    if new_bet != old_bet:
        if old_bet is not None:
            old_bet.is_risk = False
            old_bet.save()
        if new_bet is not None:
            new_bet.is_risk = True
            new_bet.save()

def get_games_for_bet(group, round):
    try:
        games_in_round = Game.objects.filter(league_id=group.league, round=round)
    except Game.DoesNotExist:
        return redirect('group', group.id)
    if not group.is_vote:
        return games_in_round.order_by('game_date')
    default_teams = DefaultTeamGroup.objects.filter(group=group)
    default_team_ids = [t.team_id for t in default_teams]
    default_games = Game.objects.filter(Q(league_id=group.league, round=round) &
                                        (Q(home_team__in=default_team_ids) | Q(away_team__in=default_team_ids)))
    games_in_round=games_in_round.exclude(pk__in=default_games)
    votes = Votes.objects.filter(group=group, game__in=games_in_round).values('game_id')\
                         .annotate(count=Count('game_id'))\
                         .order_by('count')
    try:
        current_highest_count = votes.first().get('count')
    except AttributeError:
        return default_games
    total_spots = group.bets_per_round-default_games.count()
    temp_vote_winners = []
    real_vote_winners = []
    for v in votes:
        if v.get('count') != current_highest_count:
            if total_spots-(len(real_vote_winners)+len(temp_vote_winners)) >= 0 :
                real_vote_winners += temp_vote_winners
                temp_vote_winners = []
            else:
                remaining = total_spots-len(real_vote_winners)
                while(remaining>0):
                    highest_vote = temp_vote_winners[0]
                    for t in temp_vote_winners[1:]:
                        if TeamPlace.objects.values_list('points', flat=True).get(team=highest_vote.game.home_team)+\
                           TeamPlace.objects.values_list('points', flat=True).get(team=highest_vote.game.away_team)<\
                           TeamPlace.objects.values_list('points', flat=True).get(team=t.game.home_team)+\
                           TeamPlace.objects.values_list('points', flat=True).get(team=t.game.away_team):
                            highest_vote = t
                    real_vote_winners += highest_vote
                    temp_vote_winners.remove(highest_vote)
                    remaining -= 1
            current_highest_count = v.get('count')
        if total_spots == len(real_vote_winners): break
        else:
            temp_vote_winners.append(v)
    if total_spots != len(real_vote_winners):
        if total_spots-len(real_vote_winners) == len(temp_vote_winners):
            real_vote_winners += temp_vote_winners
        else:
            remaining = total_spots - len(real_vote_winners)
            while (remaining > 0):
                highest_vote = temp_vote_winners[0]
                for t in temp_vote_winners[1:]:
                    if TeamPlace.objects.values_list('points', flat=True).get(team=highest_vote.game.home_team) + \
                            TeamPlace.objects.values_list('points', flat=True).get(team=highest_vote.game.away_team) < \
                                    TeamPlace.objects.values_list('points', flat=True).get(team=t.game.home_team) + \
                                    TeamPlace.objects.values_list('points', flat=True).get(team=t.game.away_team):
                        highest_vote = t
                real_vote_winners += highest_vote
                temp_vote_winners.remove(highest_vote)
                remaining -= 1
    voted_game_ids = [v.get('game_id') for v in real_vote_winners]
    games=games_in_round.filter(pk__in=voted_game_ids) | default_games

    return games.order_by('game_date')

def get_games_for_vote(group, games):
    default_teams = DefaultTeamGroup.objects.filter(group=group)
    default_team_ids = [t.team_id for t in default_teams]
    return games.exclude(Q(home_team__in=default_team_ids) | Q(away_team__in=default_team_ids))

def bound_formset_games_label(formset, games, bets=[]):
    for f, g, b in zip(formset, games, bets):
        f.fields['home_bet'].label = str(g.home_team)
        f.fields['away_bet'].label = str(g.away_team)
        if b is not None:
            f.fields['home_bet'].initial = b.home_bet
            f.fields['away_bet'].initial = b.away_bet
        if g.was_game_started() or g.was_game_finished():
            f.fields['home_bet'].disabled = True
            f.fields['away_bet'].disabled = True

def sum_up_points(group_id):
    members = MemberGroup.objects.filter(group_id=group_id)
    for member in members:
        pts = Bet.objects.filter(group_id=group_id, bettor_id=member.member.id).exclude(points=0).aggregate(Sum('points'))['points__sum']
        if pts is None: pts = 0
        pts += Bet.objects.filter(group_id=group_id, bettor_id=member.member.id, is_bonus=True).count()
        member.points = pts
        member.save()

def score_bonus_game(group_id, game_id):
    bets = Bet.objects.filter(group_id=group_id, game_id=game_id, points__gt = 0)
    if bets.count()==1:
        bet = bets.first()
        bet.is_bonus = True
        bet.save()

def score_bonus_round(group_id, round):
    bettors_id = MemberGroup.objects.filter(group_id=group_id).values_list('bettor_id', flat=True)
    max_games = Group.objects.values_list('bets_per_round', flat=True).get(pk=group_id)
    for b in bettors_id:
        if Bet.objects.filter(bettor_id=b, round=round, points__gt = 0).count() == max_games:
            try:
                BonusRound.objects.get(member_id=b, group_id=group_id, round=round, is_bonus=True)
            except BonusRound.DoesNotExist:
                bonus = BonusRound(member_id=b, group_id=group_id, round=round, is_bonus=True)
                bonus.save()

def count_rounds(group):
    return group.league.game_set.values_list('round', flat=True).distinct()

def lowest_round_open_for_vote(group):
    # return earliest round where first game start in more than 24hours
    max_rounds = count_rounds(group)
    for round in max_rounds:
        try:
            game = Game.objects.filter(league_id=group.league, round=round).order_by('game_date').first()
        except Game.DoesNotExist:
            return 0
        if not game.is_game_soon(1): return round
    # if no round found, return over max_round
    return max_rounds+1

def score_points(game):
    h_score = game.score_home
    a_score = game.score_away
    if h_score==None or a_score==None:
        return None
    d_score = h_score - a_score
    bets = Bet.objects.filter(game=game)
    for bet in bets:
        h_bet = bet.home_bet
        a_bet = bet.away_bet
        d_bet = h_bet-a_bet
        pts = 0

        if d_bet == 0 and d_score==0:
            pts = 3 if h_score==h_bet else 1
        elif d_bet*d_score>0:
            if d_score==d_bet:
                pts = 3 if h_bet==h_score else 2
            else: pts = 1

        if bet.is_risk:
            if pts == 0: pts = -3
            else: pts+=pts

        bet.points = pts
        bet.save()

def scraper(round):
    pass