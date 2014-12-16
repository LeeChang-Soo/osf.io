import os
import json
import uuid
import asyncio
import hashlib

import waterbutler
from waterbutler import streams
from waterbutler import settings
from waterbutler.providers import core
from waterbutler.providers import exceptions


@core.register_provider('osfstorage')
class OSFStorageProvider(core.BaseProvider):

    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)
        self.callback = settings.pop('callback')
        self.metadata_url = settings.pop('metadata')
        self.provider_name = settings.pop('provider')

    def make_provider(self, settings):
        """Requests on different files may need to use different providers,
        instances, e.g. when different files lives in different containers
        within a provider. This helper creates a single-use provider instance
        that optionally overrides the settings.

        :param dict settings: Overridden settings
        """
        return core.make_provider(
            self.provider_name,
            auth=self.auth,
            credentials=self.credentials,
            settings=settings,
        )

    @asyncio.coroutine
    def download(self, **kwargs):
        # osf storage metadata will return a virtual path within the provider
        resp = yield from self.make_request(
            'GET',
            self.callback,
            params=kwargs,
            expects=(200, ),
            throws=exceptions.DownloadError,
        )
        data = yield from resp.json()
        provider = self.make_provider(data['settings'])
        return (yield from provider.download(**data['data']))

    @asyncio.coroutine
    def upload(self, stream, path, **kwargs):
        pending_name = str(uuid.uuid4())
        pending_path = os.path.join(settings.FILE_PATH_PENDING, pending_name)

        stream.add_writer('md5', streams.HashStreamWriter(hashlib.md5))
        stream.add_writer('sha1', streams.HashStreamWriter(hashlib.sha1))
        stream.add_writer('sha256', streams.HashStreamWriter(hashlib.sha256))
        stream.add_writer('file', open(pending_path, 'wb'))

        provider = self.make_provider(self.settings)
        yield from provider.upload(stream, pending_name, **kwargs)

        complete_name = stream.writers['sha256'].hexdigest
        complete_path = os.path.join(settings.FILE_PATH_COMPLETE, complete_name)
        metadata = yield from provider.move(
            provider,
            {'path': pending_name},
            {'path': complete_name},
        )
        os.rename(pending_path, complete_path)
        yield from self.make_request(
            'POST',
            self.callback,
            data=json.dumps({
                # '...auth..provider metadata...hashes...virtual_path': '...',
                'auth': self.auth,
                'settings': self.settings,
                'metadata': metadata,
                'hashes': {
                    'md5': stream.writers['md5'].hexdigest,
                    'sha1': stream.writers['sha1'].hexdigest,
                    'sha256': stream.writers['sha256'].hexdigest,
                },
                'worker': {
                    'host': os.uname()[1],
                    # TODO: Include additional information
                    'address': None,
                    'version': waterbutler.__version__,
                },
                'path': path,
            }),
            headers={'Content-Type': 'application/json'},
        )

        # TODO: Celery Tasks for Parity & Archive
        # tasks.Archive()
        metadata['name'] = path
        return metadata
        # return OsfStorageMetadata(metadata, path)

    @asyncio.coroutine
    def delete(self, path, **kwargs):
        # resp = yield from self.make_request(
        #     'DELETE',
        #     self.identity['crudCallback'],
        #     params=kwargs,
        # )
        pass
        # # call to osf metadata
        # response = yield from self.make_request(
        #     'POST',
        #     self.build_url('fileops', 'delete'),
        #     data={'folder': 'auto', 'path': self.build_path(path)},
        # )
        # return streams.ResponseStream(response)

    @asyncio.coroutine
    def metadata(self, **kwargs):
        resp = yield from self.make_request(
            'GET',
            self.metadata_url,
            params=kwargs,
        )
        # response = yield from self.make_request(
        #     'GET',
        #     self.build_url('metadata', 'auto', self.build_path(path)),
        # )
        # if response.status != 200:
        #     raise exceptions.FileNotFoundError(path)
        #
        data = yield from resp.json()
        return data
        return [self.format_metadata(x) for x in data]

    def format_metadata(self, data):
        return {
            'provider': 'dropbox',
            'kind': 'folder' if data['is_dir'] else 'file',
            'name': os.path.split(data['path'])[1],
            'path': data['path'],
            'size': data['bytes'],
            'modified': data['modified'],
            'extra': {}  # TODO Include extra data from dropbox
        }


# class OsfStorageMetadata(core.BaseMetadata):

#     def __init__(self, raw, path):
#         super().__init__(raw)
#         self.path = path

#     @property
#     def provider(self):
#         pass

#     @property
#     def kind(self):
#         pass

#     @property
#     def name(self):
#         pass

#     @property
#     def path(self):
#         pass

#     @property
#     def modified(self):
#         pass

#     @property
#     def size(self):
#         pass

#     @property
#     def extra(self):
#         return {}
