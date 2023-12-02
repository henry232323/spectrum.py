def find(items, id):
    id = int(id)
    for item in items:
        if item.id == id:
            return item
