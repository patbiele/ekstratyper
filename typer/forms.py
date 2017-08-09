# -*- coding: utf-8 -*-
from django import forms
from .models import User, Bet

class EditProfileForm(forms.Form):

    alias = forms.CharField(label='Alias', required=False)

    class Meta:
        model = User
        fields = ['alias']

class BetForm(forms.Form):
    home_bet = forms.IntegerField(label='Gospodarz', min_value=0, max_value=255, required=False, label_suffix='')
    away_bet = forms.IntegerField(label='Gosc', min_value=0, max_value=255, required=False, label_suffix='')

    class Meta:
        model = Bet
        fields = ['home_bet', 'away_bet']

class VoteForm(forms.Form):
    vote = forms.MultipleChoiceField(label='Głosuj', widget=forms.CheckboxSelectMultiple())

    def __init__(self, choices, *args, **kwargs):
        super(VoteForm, self).__init__(*args, **kwargs)
        self.fields['vote'].choices = choices

class RiskBetForm(forms.Form):
    game_id = forms.ChoiceField(label='Pewniak', required=False, choices=[])

    def __init__(self, risk_data, *args, **kwargs):
        super(RiskBetForm, self).__init__(*args, **kwargs)
        self.fields['game_id'].choices = risk_data
