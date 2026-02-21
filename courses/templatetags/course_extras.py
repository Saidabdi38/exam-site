from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Allows dictionary lookup inside template
    usage:
    {{ dict|get_item:key }}
    """
    if dictionary:
        return dictionary.get(key)
    return None