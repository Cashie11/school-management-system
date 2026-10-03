from academics.selectors import class_subjects_for


def available_class_subjects(user):
    """Kept for the results app; delegates to the shared academics selector."""
    return class_subjects_for(user)
