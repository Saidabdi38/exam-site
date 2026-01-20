def is_teacher(user):
    # Teacher if staff OR in Teachers group
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="Teachers").exists()
    )
