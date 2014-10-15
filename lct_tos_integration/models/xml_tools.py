from lxml import etree as ET

def find_or_create(container, tag):
    element = container.find(tag)
    if element is None:
        element = element.SubElement(tag)
    return element

def dict_to_tree(vals, elmnt):
    for tag, val in vals.iteritems():
        subelmnt = ET.SubElement(elmnt, tag)
        if not val:
            pass
        elif isinstance(val, unicode):
            subelmnt.text = val
        elif isinstance(val, str):
            subelmnt.text = unicode(val)
        elif isinstance(val, int) or isinstance(val, long) and not isinstance(val, bool):
            subelmnt.text = unicode(str(val))
