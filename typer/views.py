# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.contrib.auth import views as auth_views, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Value, Max, F
from django.http import HttpResponse
from .forms import *
from .helper import * # contains following libs
# from django.shortcuts import redirect
# from django.db.models import Q, Count
# from .models import *

def league(request, league_id):
    league = get_object_or_404(League, pk=league_id)
    try:
        MemberGroup.objects.get(group_id=Group.objects.get(league_id=league_id), member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('dashboard')
    games = league.game_set.order_by("game_date", "round")
    return render(request, 'league/index.html', {'league':league, 'games':games})

def group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('dashboard')

    # get closest game to current datetime
    current_round = Game.objects.values_list('round', flat=True).filter(league_id=group.league.id,
                                                                     game_date__gt=datetime.datetime.now()).order_by('game_date')
    if (current_round):
        current_round = current_round[0]
    else:
        current_round = Game.objects.filter(league_id=group.league.id).aggregate(Max('round'))['round__max']

    max_rounds = group.league.game_set.values_list('round', flat=True).distinct().filter(round__gte=(current_round-1)).order_by('round')
    # get only games starting from previous round
    games = [Game.objects.filter(round=r, league_id=group.league.id, round__gte=(current_round-1)).order_by('game_date') for r in max_rounds]
    members = MemberGroup.objects.filter(group_id=group_id).order_by('-points')
    members.all().annotate(previous_round=Value(0))

    for member in members:
        previous_round_pts = Bet.objects.values_list('points', flat=True).filter(bettor=member.member, game__round=current_round-1, group_id=group_id).aggregate(Sum('points'))['points__sum']
        if previous_round_pts is None: previous_round_pts = 0
        previous_round_pts += Bet.objects.filter(bettor=member.member, game__round=current_round-1, group_id=group_id, is_bonus=True).count()
        member.previous_round=previous_round_pts if previous_round_pts else 0

    for round in games:
        if round.exclude(score_home=None):
            for game in round:
                bets = Bet.objects.filter(game=game, group_id=group_id)
                if bets.filter(points=None):
                    score_points(bets[0].game)
                    score_bonus_game(group_id, game.id)
                    sum_up_points(group_id)

    context = {'group':group, 'members':members, 'games':games, 'max_rounds':max_rounds, 'current_round':current_round}
    if current_round > 2: context.update({'previous_rounds':range(1,current_round-1)})
    if group.is_vote:
        current_vote_round = lowest_round_open_for_vote(group)
        context.update({'current_vote_round':current_vote_round})
    return render(request, 'group/index.html', context)

def game(request, game_id, group_id):
    game = get_object_or_404(Game, pk=game_id)
    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('dashboard')


    return render(request, 'game/index.html', {'game':game})

def bet(request, round, group_id):
    group = get_object_or_404(Group, pk=group_id)
    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('dashboard')

    games = get_games_for_bet(group,round)

    betFormSet = forms.formset_factory(BetForm, extra=group.bets_per_round)
    context = {}
    risk_data = [('', '')]
    unchangeable_risk = False
    if group.is_vote:
        if int(round) >= lowest_round_open_for_vote(group):
            context.update({'vote_still_open':'Głosowanie wciąż jest otwarte'})

    for g in games:
        if not g.was_game_started() and not g.was_game_finished():
            risk_data.append((g.id, str(g.home_team) + ' - ' + str(g.away_team)))
    if request.method == 'POST':
        formset = betFormSet(data=request.POST)
        bound_formset_games_label(formset,games)
        risk = RiskBetForm(data=request.POST, risk_data=risk_data)
        if formset.is_valid():
            for f, g in zip(formset, games):
                if not g.was_game_started() and not g.was_game_finished():
                    cd_home_bet = f.cleaned_data.get('home_bet')
                    cd_away_bet = f.cleaned_data.get('away_bet')
                    if cd_home_bet is not None and cd_away_bet is not None:
                        try:
                            bet = Bet.objects.get(group_id=group_id, game_id=g.id, bettor_id=request.user.id)
                        except Bet.DoesNotExist:
                            # insert bet for this game, group and user
                            new_bet = Bet()
                            new_bet.bettor = request.user
                            new_bet.group = group
                            new_bet.game_id = g.id
                            new_bet.home_bet = cd_home_bet
                            new_bet.away_bet = cd_away_bet
                            new_bet.is_default = False
                            new_bet.save()
                        else:
                            # update bet for this game, group and user combination
                            if bet.home_bet != cd_home_bet or bet.away_bet != cd_away_bet:
                                bet.home_bet = cd_home_bet
                                bet.away_bet = cd_away_bet
                                bet.is_default = False
                                bet.save()

            if risk.is_valid():
                risk_game_id = risk.cleaned_data['game_id']
                try:
                    risk_game = Game.objects.get(pk=risk_game_id)
                except ValueError:
                    try:
                        old_risk_bet = Bet.objects.get(group_id=group_id, bettor_id=request.user.id, is_risk=True,
                                                       game__in=games)
                    except Bet.DoesNotExist:
                        context.update({'risk_info': "Wciąż nie obstawiłeś pewniaka!"})
                    else:
                        if not old_risk_bet.game.was_game_started() and not old_risk_bet.game.was_game_finished():
                            risk_handler(old_bet=old_risk_bet)
                            context.update({'risk_info': "Cofnąłeś pewniaka, poważnie?"})
                else:
                    if risk_game.was_game_started() or risk_game.was_game_finished():
                        context.update({'risk_info':"Minął czas obstawiania tego meczu!"})
                    else:
                        if risk_game_id != '':
                            try:
                                new_risk_bet = Bet.objects.get(group_id=group_id, bettor_id=request.user.id, game_id=risk_game_id)
                            except Bet.DoesNotExist:
                                context.update({'risk_info':"Nie możesz postawić pewniaka na mecz bez wyniku"})
                            else:
                                try:
                                    old_risk_bet = Bet.objects.get(group_id=group_id, bettor_id=request.user.id, is_risk=True, game__in=games)
                                except Bet.DoesNotExist:
                                    risk_handler(new_risk_bet)
                                    context.update({'risk_info':"Pewniak postawiony!"})
                                else:
                                    if new_risk_bet != old_risk_bet:
                                        risk_handler(new_risk_bet, old_risk_bet)
                                        context.update({'risk_info':"Pewniak zaktualizowany!"})

            else:
                context.update({'risk_info': "Wygląda na to że nie mogłeś zmienić pewniaka"})

    initial_risk = ''
    bets = []
    for g in games:
        try:
            b = Bet.objects.get(group_id=group_id, bettor_id=request.user.id, game_id=g.id)
            bets.append(b)
            if g.was_game_started() or g.was_game_finished():
                if b.is_risk:
                    unchangeable_risk = g
            else:
                if b.is_risk:
                    initial_risk = b.game_id
        except Bet.DoesNotExist:
            bets.append(None)

    formset = betFormSet()


    if not unchangeable_risk:
        risk = RiskBetForm(risk_data=risk_data, initial={'game_id':initial_risk})
        context.update({'risk':risk})
    else:
        context.update({'unchangeable_risk':unchangeable_risk})
    bound_formset_games_label(formset,games,bets)

    context.update({'round':round, 'group':group, 'formset':formset})

    return render(request, 'bet/index.html', context)

def profile(request):
    if request.user.is_anonymous():
        return redirect('login')
    return render(request, 'profile/index.html')

def alias_change(request):
    if request.user.is_anonymous():
        return redirect('login')
    profile = request.user
    form = EditProfileForm(request.POST)
    if request.method == 'POST':
        if form.is_valid():
            profile.alias = form.cleaned_data.get('alias')
            profile.save()
    form = EditProfileForm(initial={'alias': profile.alias})

    return render(request, 'profile/alias.html', {'form':form})

def login(request, *args, **kwargs):
    return auth_views.login(request, *args, **kwargs)

def vote(request, round, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.is_vote:
        return redirect('group', group_id)
    if int(round) < lowest_round_open_for_vote(group):
        return redirect('group', group_id)

    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('dashboard')
    try:
        games = Game.objects.filter(league_id=group.league, round=round).order_by('game_date')
    except Game.DoesNotExist:
        return redirect('dashboard')
    max_games = games.count()
    games = get_games_for_vote(group, games)
    try:
        votes = Votes.objects.filter(group_id=group_id, voter_id=request.user.id, game__in=games)
    except Game.DoesNotExist:
        return redirect('dashboard')

    # get max number of votes by calculating number of games excluded by default teams
    number_of_votes = group.bets_per_round-(max_games-games.count())
    vote_info = 'Zagłosuj dokładnie na: '+str(number_of_votes)
    choices = [(g.id, str(g.home_team) + ' - ' + str(g.away_team)) for g in games]

    if request.method == 'POST':
        data = dict(request.POST)['vote']
        if len(data)==number_of_votes:
            if votes.count() != 0:
                for v, d in zip(votes, data):
                    if v.game != d:
                        v.game_id = d
                        v.save()
            else:
                for d in data:
                    new_vote = Votes()
                    new_vote.voter = request.user
                    new_vote.group = group
                    new_vote.game_id = d
                    new_vote.save()
                #load new votes for initial form, only when adding new
                votes = Votes.objects.filter(group_id=group_id, voter_id=request.user.id, game__in=games)
            vote_info = 'Zapisano głosy'
        else:
            vote_info = 'Musisz zaznaczyć dokładnie: '+str(number_of_votes)

    form = VoteForm(choices=choices, initial={'vote': [v.game_id for v in votes]})

    context = {'form':form, 'param':[round, group_id], 'vote_info':vote_info}

    return render(request, 'vote/index.html', context)

def password_change(request):
    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('profile/pass')
    else:
        form = SetPasswordForm(request.user)
    return render(request, 'profile/pass.html', { 'form':form })

def bets_single_game(request, group_id, game_id):
    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('group', group_id)
    bets = Bet.objects.filter(game_id=game_id, group_id=group_id).order_by('bettor')

    context = {'bets':bets, 'group_id':group_id}

    if bets.filter(points=None):
        score_points(bets[0].game)
        score_bonus_game(group_id, game_id)
        sum_up_points(group_id)

    return render(request, 'bets/game.html', context)

def bets_single_round(request, group_id, round):
    try:
        mg = MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('group', group_id)
    games = Game.objects.filter(round=round, league=mg.group.league, game_date__lt=timezone.now()).order_by('game_date')
    bets = [Bet.objects.filter(game=g, group_id=group_id).order_by('bettor') for g in games]
    members = MemberGroup.objects.filter(group_id=group_id).order_by('member__alias')
    members.all().annotate(round_points=Value(0))
    for member in members:
        round_points = Bet.objects.values_list('points', flat=True).filter(bettor=member.member, game__round=round, group_id=group_id).aggregate(Sum('points'))['points__sum']
        if round_points:
            round_points += Bet.objects.filter(bettor=member.member, game__round=round, group_id=group_id, is_bonus=True).count()
        member.round_points = round_points if round_points else 0

    return render(request, 'bets/round.html', {'bets':bets, 'games':games, 'group_id':group_id, 'bets_per_round':mg.group.bets_per_round, 'members':members})

def bets_single_member(request, group_id, member_id):
    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('group', group_id)
    bets = Bet.objects.select_related('game').filter(bettor_id=member_id, group_id=group_id).order_by('game__game_date')

    return render(request, 'bets/member.html', {'bets':bets, 'group_id':group_id})

def bets_stats(request, group_id):
    try:
        MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('group', group_id)
    members = MemberGroup.objects.filter(group_id=group_id).order_by('member__alias')
    # 1 pewniaki
    members.all().annotate(risk_count=Value(0))
    members.all().annotate(risk_points=Value(0))
    members.all().annotate(risk_percent=Value(0))
    members.all().annotate(points_risk_6_count=Value(0))
    members.all().annotate(points_risk_4_count=Value(0))
    members.all().annotate(points_risk_2_count=Value(0))
    members.all().annotate(points_risk_3_count=Value(0))
    # 2 bonusy ilosc
    members.all().annotate(bonus_count=Value(0))
    # 3 typowane spotkania
    members.all().annotate(bet_count=Value(0))
    # 4 kolejki min/max
    members.all().annotate(round_max=Value(0))
    members.all().annotate(round_min=Value(0))
    members.all().annotate(round_max_points=Value(0))
    members.all().annotate(round_min_points=Value(0))
    # 5 idealne spotkania
    members.all().annotate(perfect_count=Value(0))
    # 6 rozklad punktow
    members.all().annotate(points_3_count=Value(0))
    members.all().annotate(points_2_count=Value(0))
    members.all().annotate(points_1_count=Value(0))
    members.all().annotate(points_0_count=Value(0))
    # 7 bez pewniakow
    members.all().annotate(riskless_points=Value(0))
    # 8 lechia
    members.all().annotate(lechia_points=Value(0))
    members.all().annotate(lechia_for_count=Value(0))
    members.all().annotate(lechia_against_count=Value(0))
    members.all().annotate(lechia_draw_count=Value(0))
    members.all().annotate(lechia_risk_against_count=Value(0))
    members.all().annotate(lechia_risk_for_count=Value(0))
    members.all().annotate(lechia_risk_draw_count=Value(0))
    # 8.1 lechia vs arka
    members.all().annotate(lechia_arka_points=Value(0))
    members.all().annotate(lechia_arka_for_count=Value(0))
    members.all().annotate(lechia_arka_against_count=Value(0))
    members.all().annotate(lechia_arka_draw_count=Value(0))
    # 9 typy na gospodarzy, gosci i remisy
    members.all().annotate(home_for_count=Value(0))
    members.all().annotate(away_for_count=Value(0))
    members.all().annotate(draw_count=Value(0))

    for member in members:
        member.risk_points = Bet.objects.values_list('points', flat=True).filter(bettor=member.member, is_risk=True,
                                                                   group_id=group_id).aggregate(Sum('points'))['points__sum']
        member.risk_count = Bet.objects.filter(bettor=member.member, is_risk=True, group_id=group_id).count()
        member.risk_percent = Bet.objects.filter(bettor=member.member, is_risk=True, group_id=group_id,
                                                 points__gte=0).count()/member.risk_count

        member.bonus_count = Bet.objects.filter(bettor=member.member, group_id=group_id, is_bonus=True).count()

        member.bet_count = Bet.objects.filter(bettor=member.member, group_id=group_id).count()

        member.perfect_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points__in=[3, 6]).count()

        member.round_max_points = 0
        member.round_min_points = 99
        for r in range(1,37):
            round_points = Bet.objects.values_list('points', flat=True).filter(bettor=member.member, game__round=r,
                                                group_id=group_id).aggregate(Sum('points'))['points__sum']
            if round_points:
                round_points += Bet.objects.filter(bettor=member.member, game__round=r, group_id=group_id,
                                                   is_bonus=True).count()
            round_points = round_points if round_points else 0
            if member.round_max_points < round_points:
                member.round_max_points = round_points
                member.round_max = r
            elif member.round_min_points > round_points:
                member.round_min_points = round_points
                member.round_min = r

        member.points_3_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=3).count()
        member.points_2_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=2, is_risk=False).count()
        member.points_1_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=1).count()
        member.points_0_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=0).count()
        member.points_risk_6_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=6).count()
        member.points_risk_4_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=4).count()
        member.points_risk_2_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=2, is_risk=True).count()
        member.points_risk_3_count = Bet.objects.filter(bettor=member.member, group_id=group_id, points=-3).count()

        member.riskless_points = Bet.objects.values_list('points', flat=True).filter(bettor=member.member, is_risk=True,
                                             group_id=group_id, points__gt=0).aggregate(Sum('points'))['points__sum']/2
        member.riskless_points += Bet.objects.values_list('points', flat=True).filter(bettor=member.member, is_risk=False,
                                             group_id=group_id, points__gt=0).aggregate(Sum('points'))['points__sum']
        member.riskless_points += Bet.objects.filter(bettor=member.member, group_id=group_id, is_bonus=True).count()

        member.lechia_points = Bet.objects.values_list('points', flat=True).filter(bettor=member.member,
                                         group_id=group_id, game__home_team=4).aggregate(Sum('points'))['points__sum']
        member.lechia_points += Bet.objects.values_list('points', flat=True).filter(bettor=member.member,
                                         group_id=group_id, game__away_team=4).aggregate(Sum('points'))['points__sum']
        member.lechia_points += Bet.objects.filter(bettor=member.member, group_id=group_id, is_bonus=True,
                                                   game__away_team=4).count()
        member.lechia_points += Bet.objects.filter(bettor=member.member, group_id=group_id, is_bonus=True,
                                                   game__home_team=4).count()
        member.lechia_for_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                     game__home_team=4, home_bet__gt=F('away_bet')).count()
        member.lechia_for_count += Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                      game__away_team=4, home_bet__lt=F('away_bet')).count()
        member.lechia_against_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                         game__home_team=4, home_bet__lt=F('away_bet')).count()
        member.lechia_against_count += Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                          game__away_team=4, home_bet__gt=F('away_bet')).count()
        member.lechia_draw_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                      game__home_team=4, home_bet=F('away_bet')).count()
        member.lechia_draw_count += Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                       game__away_team=4, home_bet=F('away_bet')).count()
        member.lechia_risk_for_count = Bet.objects.filter(bettor=member.member, group_id=group_id, is_risk=True,
                                                     game__home_team=4, home_bet__gt=F('away_bet')).count()
        member.lechia_risk_for_count += Bet.objects.filter(bettor=member.member, group_id=group_id, is_risk=True,
                                                      game__away_team=4, home_bet__lt=F('away_bet')).count()
        member.lechia_risk_against_count = Bet.objects.filter(bettor=member.member, group_id=group_id, is_risk=True,
                                                         game__home_team=4, home_bet__lt=F('away_bet')).count()
        member.lechia_risk_against_count += Bet.objects.filter(bettor=member.member, group_id=group_id, is_risk=True,
                                                          game__away_team=4, home_bet__gt=F('away_bet')).count()
        member.lechia_risk_draw_count = Bet.objects.filter(bettor=member.member, group_id=group_id, is_risk=True,
                                                      game__home_team=4, home_bet=F('away_bet')).count()
        member.lechia_risk_draw_count += Bet.objects.filter(bettor=member.member, group_id=group_id, is_risk=True,
                                                       game__away_team=4, home_bet=F('away_bet')).count()

        member.lechia_arka_points = Bet.objects.values_list('points', flat=True).filter(bettor=member.member,
                                                            group_id=group_id,game__home_team__in=[4,13],
                                                            game__away_team__in=[4,13]).aggregate(Sum('points'))['points__sum']
        member.lechia_arka_points += Bet.objects.filter(bettor=member.member, group_id=group_id, is_bonus=True,
                                                        game__home_team__in=[4,13], game__away_team__in=[4,13]).count()
        member.lechia_arka_for_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                     game__home_team=4, game__away_team=13, home_bet__gt=F('away_bet')).count()
        member.lechia_arka_for_count += Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                      game__away_team=4, game__home_team=13, home_bet__lt=F('away_bet')).count()
        member.lechia_arka_against_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                          game__home_team=4, game__away_team=13, home_bet__lt=F('away_bet')).count()
        member.lechia_arka_against_count += Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                           game__away_team=4, game__home_team=13, home_bet__gt=F('away_bet')).count()
        member.lechia_arka_draw_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                           game__home_team=4, game__away_team=13, home_bet=F('away_bet')).count()
        member.lechia_arka_draw_count += Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                            game__away_team=4, game__home_team=13, home_bet=F('away_bet')).count()

        member.home_for_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                     home_bet__gt=F('away_bet')).count()
        member.away_for_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                         home_bet__lt=F('away_bet')).count()
        member.draw_count = Bet.objects.filter(bettor=member.member, group_id=group_id,
                                                      home_bet=F('away_bet')).count()

    return render(request, 'bets/stats.html', {'members':members, 'group_id':group_id})

def bets_all(request, group_id):
    try:
        mg = MemberGroup.objects.get(group_id=group_id, member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        return redirect('group', group_id)
    total_rounds = mg.group.league.game_set.values_list('round', flat=True).distinct().order_by('round')
    max_round = 0
    for r in total_rounds:
        current = Game.objects.filter(round=r, game_date__lt=timezone.now()).first()
        if not current:
            break
        else:
            max_round = current.round

    members = MemberGroup.objects.filter(group_id=group_id).order_by('member__alias')
    sum_points = []
    for member in members:
        sum_points.append([member.member.get_display_name(),member.points])
        for round in range(1,max_round+1):
            round_points = Bet.objects.values_list('points', flat=True).filter(
                bettor=member.member, game__round=round, group_id=group_id).aggregate(Sum('points'))['points__sum']
            if round_points:
                round_points += Bet.objects.filter(bettor=member.member, game__round=round, group_id=group_id, is_bonus=True).count()
            else:
                round_points = 0
            sum_points[-1].append(round_points)

    bets = [Bet.objects.filter(game__round=round, group_id=group_id, game__game_date__lt=timezone.now()).order_by('bettor', 'game__game_date')\
            for round in range(1,max_round+1)]

    return render(request, 'bets/all.html', {'bets':bets, 'group_id':group_id, 'rounds':range(1,max_round+1), 'sum_points':sum_points})

def dashboard(request):
    if request.user.is_anonymous():
        return redirect('login')
    try:
        member_in_groups = MemberGroup.objects.filter(member_id=request.user.id)
    except MemberGroup.DoesNotExist:
        member_in_groups = 'Nie należysz do żadnej grupy'

    if member_in_groups.count() == 1:
        return redirect('group', member_in_groups.first().group_id)

    return render(request, 'index.html', {'member_in_groups':member_in_groups})