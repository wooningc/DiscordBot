import aiohttp

ENDPOINT = 'https://api.paste.ee/v1/pastes'
DESCRIPTION = 'Automatic upload by HTSTEM-Bote'
ERROR_MESSAGE = 'Uploading to paste.ee failed: `{}`'


class DataUploader:
    def __init__(self, bot):
        self.session = aiohttp.ClientSession(loop=bot.loop)
        self.config = bot.config.get('paste.ee', {})
        self.api_key = self.config.get('api_key', '')
        print([self.api_key])
    
    async def upload(self, data, title=None):
        if title is None:
            title = DESCRIPTION
        json_data = {
            'description': DESCRIPTION,
            'sections': [
                {
                    'name': title,
                    'contents': data
                }
            ]
        }
        async with self.session.post(ENDPOINT,
                                     headers={
                                         'content-type': 'application/json',
                                         'X-Auth-Token': self.api_key,
                                     },
                                     json=json_data) as resp:
            json_obj = await resp.json()
            if resp.status == 201:
                url = '<{}>'format(json_obj['link'])
            else:
                url = ERROR_MESSAGE.format(resp.status)
                if 'errors' in json_obj:
                    print(json_obj['errors'])
        return url
