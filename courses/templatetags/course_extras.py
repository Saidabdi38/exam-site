from django import template

register = template.Library()


@register.filter
def get_item(obj, key):
    """
    Safe dictionary lookup
    Works only if object supports .get()
    """
    try:
        if hasattr(obj, "get"):
            return obj.get(key)
    except Exception:
        pass
    return None