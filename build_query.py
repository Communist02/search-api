import json

SIZE = 1000


def build_full_text_query(text: str, fields: list[str]) -> list[dict]:
    """Строит текстовый запрос с учетом разных стратегий"""
    if not text or not fields:
        return []

    queries = []
    for field in fields:
        # 1. Exact match (phrase) - самый релевантный
        queries.append({
            "match_phrase": {
                field: {
                    "query": text,
                    "boost": 3.0
                }
            }
        })

        # 2. Fuzzy search
        queries.append({
            "match": {
                field: {
                    "query": text,
                    "fuzziness": "AUTO",
                    "boost": 2.0
                }
            }
        })

        # 3. Prefix search (более эффективно чем wildcard)
        queries.append({
            "wildcard": {
                field: f'*{text.lower()}*'
            }
        })

    # 4. Cross-field search (дополнительный вариант)
    queries.append({
        "multi_match": {
            "query": text,
            "fields": fields,
            "type": "best_fields",
            "fuzziness": "AUTO"
        }
    })

    return queries


def build_geo_distance_query(value: list[float], fields: list[str]) -> list[dict]:
    """
    value = [lat, lon, distance]

    fields = ["location", "geo.point", ...]
    """

    if not value or len(value) != 3:
        return []

    lat, lon, distance = value

    queries = []
    for field in fields:
        queries.append({
            "geo_distance": {
                "distance": f"{distance}m",
                field: {
                    "lat": lat,
                    "lon": lon
                }
            }
        })

    return queries


def build_geo_bounding_box_query(value: list[float], fields: list[str]) -> list[dict]:
    """
    value = [top_left.lat, top_left.lon, bottom_right.lat, bottom_right.lon]

    fields = ["location", "geo.point", ...]
    """

    if not value or len(value) != 4:
        return []

    top_left_lat, top_left_lon, bottom_right_lat, bottom_right_lon = value

    queries = []
    for field in fields:
        queries.append({
            "geo_bounding_box": {
                field: {
                    "top_left": {
                        "lat": top_left_lat,
                        "lon": top_left_lon
                    },
                    "bottom_right": {
                        "lat": bottom_right_lat,
                        "lon": bottom_right_lon
                    }
                }
            }
        })

    return queries


def build_query_for_category(filter: dict, text: str, config: dict) -> dict[str, dict | int]:
    must_clauses = []
    filter_clauses = []
    should_clauses = []

    for key, filter_config in config.items():
        filter_type = filter_config['type']
        filter_value = filter.get(key)

        if filter_type == 'full_text' and text:
            text_queries = build_full_text_query(
                text, filter_config['fields'])
            must_clauses.append(
                {
                    'bool': {
                        'should': text_queries
                    }
                }
            )
            continue

        if filter_value is None:
            continue

        match filter_type:
            case 'term':
                must_clauses.append({
                    'term': {
                        filter_config['fields'][0]: filter_value
                    }
                })
            case 'range':
                must_clauses.append({
                    'range': {
                        filter_config['fields'][0]: {
                            'gte': filter_value[0], 'lte': filter_value[1]}
                    }
                })
            case 'date_range':
                must_clauses.append({
                    'range': {
                        filter_config['fields'][0]: {
                            'gte': filter_value[0], 'lte': filter_value[1]}
                    }
                })
            case 'geo_bounding_box':
                must_clauses.append({
                    'geo_bounding_box': {
                        filter_config['fields'][0]: filter_value
                    }
                })
            case 'geo_distance':
                filter_clauses.append({
                    'bool': {
                        'should': build_geo_distance_query(filter_value, filter_config['fields'])
                    }
                })

    query: dict = {"query": {"bool": {}}}

    if must_clauses:
        query["query"]["bool"]["must"] = must_clauses

    if filter_clauses:
        query["query"]["bool"]["filter"] = filter_clauses

    # Если нет условий, возвращаем match_all
    if not must_clauses and not filter_clauses and not should_clauses:
        query["query"] = {"match_all": {}}

    query["size"] = SIZE

    return query


def build_queries_for_categories(categories: list[str], text: str, filters: dict) -> dict[str, dict]:
    categories_config = json.loads(
        open('categories.json', 'r').read())['categories']

    queries = {}

    for category in categories:
        query = build_query_for_category(
            filters.get(category, {}), text, categories_config[category]['filters'])
        queries[category] = query
    return queries
