from django import template
register = template.Library()

@register.filter
def index(List, i):
    return List[int(i)]

@register.filter(name='chr')
def chr_(value):
    return chr(value + 64)

@register.filter(name='isNotDefault')
def isDefault_(label_tag):
    return True if label_tag != "Gospodarz" else False

@register.filter(name='group_playoff')
def group_playoff_(round):
    if round < 9:
        return 'Grupa '+chr_(round)
    elif round == 9:
        return 'Runda 1/8'
    elif round == 10:
        return 'Ćwierćfinały'
    elif round == 11:
        return 'Półfinały'
    elif round == 12:
        return 'Finał i 3. miejsce'
    else:
        return round+". kolejka"