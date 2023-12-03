def find(items, id):
    id = int(id)
    for item in items:
        if item.id == id:
            return item


from .event_dispatch import event_dispatch, EventCallback, register_callback
