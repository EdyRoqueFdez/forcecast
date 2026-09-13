"""Seed script for orchestrators — HU-T08 examples."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import (
    Orchestrator,
    OrchestratorTranslation,
    OrchestratorProvider,
    Provider,
)


ORCHESTRATORS = [
    {
        "slug": "gentle-orchestrator",
        "name": "Gentle Orchestrator",
        "version": "0.1.0",
        "maintainer": "Forcecast",
        "website": "https://forcecast.com",
        "repo_url": "https://github.com/forcecast/gentle-orchestrator",
        "license": "MIT",
        "translations": {
            "en": {"name": "Gentle Orchestrator", "description": "AI orchestration framework with SDD methodology"},
            "es": {"name": "Gentle Orchestrator", "description": "Framework de orquestación IA con metodología SDD"},
            "pt": {"name": "Gentle Orchestrator", "description": "Framework de orquestração IA com metodologia SDD"},
            "fr": {"name": "Gentle Orchestrator", "description": "Framework d'orchestration IA avec méthodologie SDD"},
            "zh": {"name": "Gentle Orchestrator", "description": "AI编排框架，采用SDD方法论"},
        },
        "provider_slugs": [],
    },
    {
        "slug": "langchain",
        "name": "LangChain",
        "version": "0.2.0",
        "maintainer": "LangChain Inc.",
        "website": "https://langchain.com",
        "repo_url": "https://github.com/langchain-ai/langchain",
        "license": "MIT",
        "translations": {
            "en": {"name": "LangChain", "description": "Framework for building LLM applications with composable components"},
            "es": {"name": "LangChain", "description": "Framework para construir aplicaciones LLM con componentes componibles"},
            "pt": {"name": "LangChain", "description": "Framework para construir aplicações LLM com componentes componíveis"},
            "fr": {"name": "LangChain", "description": "Framework pour construire des applications LLM avec des composants composites"},
            "zh": {"name": "LangChain", "description": "使用可组合组件构建LLM应用的框架"},
        },
        "provider_slugs": ["openai", "anthropic", "google"],
    },
    {
        "slug": "llamaindex",
        "name": "LlamaIndex",
        "version": "0.10.0",
        "maintainer": "LlamaIndex Inc.",
        "website": "https://llamaindex.ai",
        "repo_url": "https://github.com/run-llama/llama_index",
        "license": "MIT",
        "translations": {
            "en": {"name": "LlamaIndex", "description": "Data framework for LLM applications focused on retrieval-augmented generation"},
            "es": {"name": "LlamaIndex", "description": "Framework de datos para aplicaciones LLM enfocado en generación aumentada por recuperación"},
            "pt": {"name": "LlamaIndex", "description": "Framework de dados para aplicações LLM focado em geração aumentada por recuperação"},
            "fr": {"name": "LlamaIndex", "description": "Framework de données pour applications LLM axé sur la génération augmentée par récupération"},
            "zh": {"name": "LlamaIndex", "description": "专注于检索增强生成的LLM应用数据框架"},
        },
        "provider_slugs": ["openai", "anthropic"],
    },
    {
        "slug": "autogen",
        "name": "AutoGen",
        "version": "0.2.0",
        "maintainer": "Microsoft",
        "website": "https://microsoft.github.io/autogen",
        "repo_url": "https://github.com/microsoft/autogen",
        "license": "MIT",
        "translations": {
            "en": {"name": "AutoGen", "description": "Multi-agent conversation framework for complex AI workflows"},
            "es": {"name": "AutoGen", "description": "Framework de conversación multi-agente para flujos de trabajo IA complejos"},
            "pt": {"name": "AutoGen", "description": "Framework de conversação multi-agente para fluxos de trabalho IA complexos"},
            "fr": {"name": "AutoGen", "description": "Framework de conversation multi-agents pour workflows IA complexes"},
            "zh": {"name": "AutoGen", "description": "用于复杂AI工作流的多智能体对话框架"},
        },
        "provider_slugs": ["openai", "azure"],
    },
    {
        "slug": "crewai",
        "name": "CrewAI",
        "version": "0.30.0",
        "maintainer": "CrewAI Inc.",
        "website": "https://crewai.com",
        "repo_url": "https://github.com/crewAIInc/crewAI",
        "license": "MIT",
        "translations": {
            "en": {"name": "CrewAI", "description": "Framework for orchestrating role-playing autonomous AI agents"},
            "es": {"name": "CrewAI", "description": "Framework para orquestar agentes IA autónomos con roles"},
            "pt": {"name": "CrewAI", "description": "Framework para orquestrar agentes IA autônomos com papéis"},
            "fr": {"name": "CrewAI", "description": "Framework pour orchestrer des agents IA autonomes à rôles"},
            "zh": {"name": "CrewAI", "description": "用于编排角色扮演自主AI智能体的框架"},
        },
        "provider_slugs": ["openai"],
    },
    {
        "slug": "semantic-kernel",
        "name": "Semantic Kernel",
        "version": "1.0.0",
        "maintainer": "Microsoft",
        "website": "https://learn.microsoft.com/semantic-kernel",
        "repo_url": "https://github.com/microsoft/semantic-kernel",
        "license": "MIT",
        "translations": {
            "en": {"name": "Semantic Kernel", "description": "SDK for integrating LLMs into enterprise applications"},
            "es": {"name": "Semantic Kernel", "description": "SDK para integrar LLMs en aplicaciones empresariales"},
            "pt": {"name": "Semantic Kernel", "description": "SDK para integrar LLMs em aplicações empresariais"},
            "fr": {"name": "Semantic Kernel", "description": "SDK pour intégrer les LLMs dans les applications d'entreprise"},
            "zh": {"name": "Semantic Kernel", "description": "用于将LLM集成到企业应用中的SDK"},
        },
        "provider_slugs": ["openai", "azure"],
    },
    {
        "slug": "haystack",
        "name": "Haystack",
        "version": "2.0.0",
        "maintainer": "deepset",
        "website": "https://haystack.deepset.ai",
        "repo_url": "https://github.com/deepset-ai/haystack",
        "license": "Apache-2.0",
        "translations": {
            "en": {"name": "Haystack", "description": "End-to-end framework for building NLP and LLM pipelines"},
            "es": {"name": "Haystack", "description": "Framework extremo a extremo para construir pipelines NLP e LLM"},
            "pt": {"name": "Haystack", "description": "Framework ponta a ponta para construir pipelines NLP e LLM"},
            "fr": {"name": "Haystack", "description": "Framework de bout en bout pour construire des pipelines NLP et LLM"},
            "zh": {"name": "Haystack", "description": "用于构建NLP和LLM管道的端到端框架"},
        },
        "provider_slugs": ["openai", "anthropic"],
    },
    {
        "slug": "dspy",
        "name": "DSPy",
        "version": "2.0.0",
        "maintainer": "Stanford NLP",
        "website": "https://dspy.ai",
        "repo_url": "https://github.com/stanfordnlp/dspy",
        "license": "MIT",
        "translations": {
            "en": {"name": "DSPy", "description": "Framework for programming with foundation models instead of prompting"},
            "es": {"name": "DSPy", "description": "Framework para programar con modelos de base en lugar de prompts"},
            "pt": {"name": "DSPy", "description": "Framework para programar com modelos de base em vez de prompts"},
            "fr": {"name": "DSPy", "description": "Framework pour programmer avec des modèles de base au lieu de prompts"},
            "zh": {"name": "DSPy", "description": "用于编程基础模型而非提示的框架"},
        },
        "provider_slugs": ["openai"],
    },
]


async def seed_orchestrators(session: AsyncSession) -> dict:
    """Seed orchestrators into the database.

    Returns:
        Dict with counts of created/skipped items.
    """
    created = 0
    skipped = 0
    providers_created = 0

    for orch_data in ORCHESTRATORS:
        # Check if orchestrator already exists
        existing = await session.execute(
            select(Orchestrator).where(Orchestrator.slug == orch_data["slug"])
        )
        if existing.scalars().first():
            skipped += 1
            continue

        # Create orchestrator
        orch_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        orchestrator = Orchestrator(
            id=orch_id,
            slug=orch_data["slug"],
            name=orch_data["name"],
            version=orch_data["version"],
            maintainer=orch_data["maintainer"],
            website=orch_data["website"],
            repo_url=orch_data["repo_url"],
            license=orch_data["license"],
            status="approved",
            created_at=now,
            updated_at=now,
        )
        session.add(orchestrator)

        # Create translations
        for locale, trans in orch_data["translations"].items():
            translation = OrchestratorTranslation(
                id=str(uuid.uuid4()),
                orchestrator_id=orch_id,
                locale=locale,
                name=trans["name"],
                description=trans["description"],
            )
            session.add(translation)

        # Create provider associations
        for provider_slug in orch_data["provider_slugs"]:
            prov_result = await session.execute(
                select(Provider).where(Provider.slug == provider_slug)
            )
            provider = prov_result.scalars().first()
            if provider:
                assoc = OrchestratorProvider(
                    orchestrator_id=orch_id,
                    provider_id=provider.id,
                    created_at=now,
                )
                session.add(assoc)
                providers_created += 1

        created += 1

    await session.commit()

    return {
        "orchestrators_created": created,
        "orchestrators_skipped": skipped,
        "provider_associations_created": providers_created,
    }
