from opensearchpy import AsyncOpenSearch
from config import config

# auth = ('admin', os.getenv('OPENSEARCH_PASS'))
# For testing only. Don't store credentials in code.
auth = (config.opensearch_user, config.opensearch_password)


class OpenSearchManager:
    def __init__(self, host: str = config.opensearch_host, port: int = config.opensearch_port, auth: tuple = auth):
        self.host = host
        self.port = port
        self.auth = auth

    # async def get_document(self, doc_id: int, index_name: str = config.opensearch_collections_index) -> dict | None:
    #     async with AsyncOpenSearch(
    #         hosts=[{'host': self.host, 'port': self.port}],
    #         http_compress=True,
    #         http_auth=auth,
    #         use_ssl=True,
    #         verify_certs=not config.debug_mode,
    #         ssl_assert_hostname=not config.debug_mode,
    #         ssl_show_warn=not config.debug_mode,
    #     ) as client:
    #         try:
    #             response = await client.get(
    #                 index=index_name,
    #                 id=doc_id,
    #             )
    #             return response['_source']
    #         except NotFoundError:
    #             return None

    async def search_documents(self, queries: dict, jwt_token: str):
        # size_collections = 100
        # size_files = 1000
        auth_header = {'Authorization': f'Bearer {jwt_token}'}

        async with AsyncOpenSearch(
            hosts=[{'host': config.opensearch_host,
                    'port': config.opensearch_port}],
            http_compress=True,
            headers=auth_header,
            use_ssl=True,
            verify_certs=not config.debug_mode,
            ssl_assert_hostname=not config.debug_mode,
            ssl_show_warn=not config.debug_mode
        ) as client:
            # response = await client.search(
            #     body=query_collections,
            #     index=index_collections,
            # )
            # collections = response['hits']['hits']
            result = {}
            for index, query in queries.items():
                response = await client.search(
                    body=query,
                    index=index,
                )
                files = {}
                for document in response['hits']['hits']:
                    files[document['_id']] = document['_source']
                result[index] = files
        return result
