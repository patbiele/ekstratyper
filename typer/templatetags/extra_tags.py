from django import template
register = template.Library()

@register.filter
def index(List, i):
    return List[int(i)]

@register.filter(name='chr')
def chr_(value):
    return chr(value + 64)

@register.filter(name='group_playoff')
def group_playoff_(value):
    if value < 9:
        return 'Grupa'+chr_(value)
    elif value == 9:
        return 'Runda 1/8'
    elif value == 10:
        return 'Ćwierćfinały'
    elif value == 11:
        return 'Półfinały'
    elif value == 12:
        return 'Finał i 3. miejsce'
    else:
        return value