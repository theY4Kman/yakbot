def comma_andify(seq, sep=', ', and_='and'):
    items = list(seq)
    length = len(items)
    if length == 0:
        return ''
    elif length == 1:
        return ''.join(items)
    elif length == 2:
        items.insert(1, and_)
        return ' '.join(items)
    else:
        items[-1] = '%s %s' % (and_, items[-1])
        return sep.join(items)


def pluralize(n, singular='', plural='s'):
    return singular if n == 1 else plural
