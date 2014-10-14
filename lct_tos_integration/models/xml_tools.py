
def find_or_create(container, tag):
    element = container.find(tag)
    if element is None:
        element = element.SubElement(tag)
    return element

