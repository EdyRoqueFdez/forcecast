# Spec: HU-T08 — List Orchestrators

## Endpoint
`GET /api/v1/orchestrators`

## Query Parameters
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `lang` | string | `en` | Locale for translations |
| `category` | string | null | Filter by category slug |
| `cursor` | string | null | Cursor for pagination |
| `limit` | int | 20 | Items per page (1-100) |
| `sort` | string | `name` | Sort field: `name`, `version`, `created_at` |
| `order` | string | `asc` | Sort order: `asc`, `desc` |
| `page` | int | null | Page number (max 10, use cursor for more) |

## Response Schema

### Success (200)
```json
{
  "data": [
    {
      "id": "uuid",
      "slug": "langchain",
      "name": "LangChain",
      "version": "0.2.0",
      "maintainer": "LangChain Inc.",
      "website": "https://langchain.com",
      "repo_url": "https://github.com/langchain-ai/langchain",
      "status": "approved",
      "description": "Framework for building LLM applications",
      "locale_used": "en",
      "providers": [
        {
          "slug": "openai",
          "name": "OpenAI"
        }
      ]
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 8,
    "has_more": false,
    "next_cursor": null,
    "taxonomy_version": "v1"
  },
  "links": {
    "first": "/api/v1/orchestrators?limit=20",
    "prev": null,
    "next": null,
    "last": "/api/v1/orchestrators?limit=20"
  }
}
```

### Error (406)
```json
{
  "error": {
    "code": "UNSUPPORTED_LOCALE",
    "message": "Unsupported locale: xx. Supported: ['en', 'es', 'fr', 'pt', 'zh']",
    "details": [{"field": "lang", "issue": "must be one of ['en', 'es', 'fr', 'pt', 'zh']"}],
    "trace_id": "uuid"
  }
}
```

## Business Rules
- Only return orchestrators with `status=approved`
- Default sort by `name` ascending
- Cache TTL: 60 seconds
- Translations: EN, ES, PT, FR, ZH
- Providers are associated via OrchestratorProvider junction table

## Seed Data
| slug | name | maintainer | website |
|------|------|------------|---------|
| gentle-orchestrator | Gentle Orchestrator | Forcecast | https://forcecast.com |
| langchain | LangChain | LangChain Inc. | https://langchain.com |
| llamaindex | LlamaIndex | LlamaIndex Inc. | https://llamaindex.ai |
| autogen | AutoGen | Microsoft | https://microsoft.github.io/autogen |
| crewai | CrewAI | CrewAI Inc. | https://crewai.com |
| semantic-kernel | Semantic Kernel | Microsoft | https://learn.microsoft.com/semantic-kernel |
| haystack | Haystack | deepset | https://haystack.deepset.ai |
| dspy | DSPy | Stanford NLP | https://dspy.ai |

## Implementation Notes
- Follow existing patterns from `public.py` and `public` service
- Use `ProviderTranslation` pattern for orchestrator translations
- Create `OrchestratorProvider` junction table for many-to-many
- Add to `app/taxonomy/models/entities.py`
- Add to `app/taxonomy/services/public.py`
- Add to `app/taxonomy/api/public.py`
