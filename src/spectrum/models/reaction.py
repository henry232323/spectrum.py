from .. import httpclient


class Reaction:
    def __init__(self, client: 'httpclient.HTTPClient', payload: dict):
        self._client = client
        self.reaction_type: str = payload['reaction_type']
        self.entity_type: str = payload['entity_type']
        self.entity_id: int = int(payload['entity_id'])
        self.member_id: int = int(payload['member']['id'])

    @property
    def member(self):
        return self._client.get_member(self.member_id)

    @property
    def message(self):
        return self._client.get_message(self.member_id)
