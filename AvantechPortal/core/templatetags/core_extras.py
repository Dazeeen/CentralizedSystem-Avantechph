from django import template
from pathlib import Path

register = template.Library()


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def is_image_file(file_field):
    if not file_field:
        return False
    name = getattr(file_field, 'name', '') or ''
    lowered = name.lower()
    return lowered.endswith('.png') or lowered.endswith('.jpg') or lowered.endswith('.jpeg') or lowered.endswith('.webp')


@register.filter
def is_video_file(file_field):
    if not file_field:
        return False
    name = getattr(file_field, 'name', '') or ''
    lowered = name.lower()
    return (
        lowered.endswith('.mp4')
        or lowered.endswith('.mov')
        or lowered.endswith('.avi')
        or lowered.endswith('.mkv')
        or lowered.endswith('.webm')
        or lowered.endswith('.mpeg')
        or lowered.endswith('.mpg')
    )


@register.filter
def is_pdf_file(file_field):
    if not file_field:
        return False
    name = getattr(file_field, 'name', '') or ''
    return name.lower().endswith('.pdf')


@register.filter
def file_extension(file_field):
    if not file_field:
        return ''
    name = getattr(file_field, 'name', '') or ''
    if '.' not in name:
        return 'FILE'
    return name.rsplit('.', 1)[-1].upper()


@register.filter
def basename(file_field):
    if not file_field:
        return ''
    name = getattr(file_field, 'name', '') or ''
    return Path(name).name


@register.filter
def is_word_file(file_field):
    if not file_field:
        return False
    name = getattr(file_field, 'name', '') or ''
    lowered = name.lower()
    return lowered.endswith('.doc') or lowered.endswith('.docx')


@register.filter
def is_excel_file(file_field):
    if not file_field:
        return False
    name = getattr(file_field, 'name', '') or ''
    lowered = name.lower()
    return lowered.endswith('.xls') or lowered.endswith('.xlsx')


@register.filter
def choice_label(value, choices):
    if choices is None:
        return value
    for option_value, option_label in choices:
        if str(option_value) == str(value):
            return option_label
    return value
