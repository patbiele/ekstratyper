from django import template
register = template.Library()

@register.filter
def index(List, i):
    return List[int(i)]

@register.filter(name='chr')
def chr_(value):
    return chr(value + 64)