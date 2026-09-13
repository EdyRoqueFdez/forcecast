"""Seed script for orchestrator categories — HU-T10."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import Category, CategoryTranslation


ORCHESTRATOR_CATEGORIES = [
    {
        "slug": "multi_agent",
        "translations": {
            "en": {"name": "Multi-Agent", "description": "Frameworks supporting multiple AI agents working together"},
            "es": {"name": "Multi-Agente", "description": "Frameworks que soportan múltiples agentes IA trabajando juntos"},
            "pt": {"name": "Multi-Agente", "description": "Frameworks que suportam múltiplos agentes IA trabalhando juntos"},
            "fr": {"name": "Multi-Agent", "description": "Frameworks supportant plusieurs agents IA travaillant ensemble"},
            "zh": {"name": "多智能体", "description": "支持多个AI智能体协同工作的框架"},
        },
    },
    {
        "slug": "tool_use",
        "translations": {
            "en": {"name": "Tool Use", "description": "Frameworks enabling AI to use external tools and APIs"},
            "es": {"name": "Uso de Herramientas", "description": "Frameworks que permiten a la IA usar herramientas y APIs externas"},
            "pt": {"name": "Uso de Ferramentas", "description": "Frameworks que permitem à IA usar ferramentas e APIs externas"},
            "fr": {"name": "Utilisation d'Outils", "description": "Frameworks permettant à l'IA d'utiliser des outils et APIs externes"},
            "zh": {"name": "工具使用", "description": "使AI能够使用外部工具和API的框架"},
        },
    },
    {
        "slug": "planning",
        "translations": {
            "en": {"name": "Planning", "description": "Frameworks with task planning and decomposition capabilities"},
            "es": {"name": "Planificación", "description": "Frameworks con capacidades de planificación y descomposición de tareas"},
            "pt": {"name": "Planejamento", "description": "Frameworks com capacidades de planejamento e decomposição de tarefas"},
            "fr": {"name": "Planification", "description": "Frameworks avec capacités de planification et décomposition des tâches"},
            "zh": {"name": "规划", "description": "具有任务规划和分解能力的框架"},
        },
    },
    {
        "slug": "memory",
        "translations": {
            "en": {"name": "Memory", "description": "Frameworks with persistent or contextual memory capabilities"},
            "es": {"name": "Memoria", "description": "Frameworks con capacidades de memoria persistente o contextual"},
            "pt": {"name": "Memória", "description": "Frameworks com capacidades de memória persistente ou contextual"},
            "fr": {"name": "Mémoire", "description": "Frameworks avec capacités de mémoire persistante ou contextuelle"},
            "zh": {"name": "记忆", "description": "具有持久化或上下文记忆能力的框架"},
        },
    },
    {
        "slug": "rag",
        "translations": {
            "en": {"name": "RAG", "description": "Retrieval-Augmented Generation frameworks"},
            "es": {"name": "RAG", "description": "Frameworks de Generación Aumentada por Recuperación"},
            "pt": {"name": "RAG", "description": "Frameworks de Geração Aumentada por Recuperação"},
            "fr": {"name": "RAG", "description": "Frameworks de Génération Augmentée par Récupération"},
            "zh": {"name": "RAG", "description": "检索增强生成框架"},
        },
    },
    {
        "slug": "workflow",
        "translations": {
            "en": {"name": "Workflow", "description": "Frameworks for orchestrating complex AI workflows"},
            "es": {"name": "Flujo de Trabajo", "description": "Frameworks para orquestar flujos de trabajo IA complejos"},
            "pt": {"name": "Fluxo de Trabalho", "description": "Frameworks para orquestrar fluxos de trabalho IA complexos"},
            "fr": {"name": "Flux de Travail", "description": "Frameworks pour orchestrer des workflows IA complexes"},
            "zh": {"name": "工作流", "description": "用于编排复杂AI工作流的框架"},
        },
    },
    {
        "slug": "evaluation",
        "translations": {
            "en": {"name": "Evaluation", "description": "Frameworks for evaluating AI model performance"},
            "es": {"name": "Evaluación", "description": "Frameworks para evaluar el rendimiento de modelos IA"},
            "pt": {"name": "Avaliação", "description": "Frameworks para avaliar o desempenho de modelos IA"},
            "fr": {"name": "Évaluation", "description": "Frameworks pour évaluer les performances des modèles IA"},
            "zh": {"name": "评估", "description": "用于评估AI模型性能的框架"},
        },
    },
    {
        "slug": "routing",
        "translations": {
            "en": {"name": "Routing", "description": "Frameworks for intelligent request routing to appropriate models"},
            "es": {"name": "Enrutamiento", "description": "Frameworks para enrutamiento inteligente de solicitudes a modelos apropiados"},
            "pt": {"name": "Roteamento", "description": "Frameworks para roteamento inteligente de solicitações a modelos apropriados"},
            "fr": {"name": "Routage", "description": "Frameworks pour le routage intelligent des requêtes vers les modèles appropriés"},
            "zh": {"name": "路由", "description": "用于将请求智能路由到适当模型的框架"},
        },
    },
    {
        "slug": "observability",
        "translations": {
            "en": {"name": "Observability", "description": "Frameworks for monitoring and observing AI system behavior"},
            "es": {"name": "Observabilidad", "description": "Frameworks para monitorear y observar el comportamiento de sistemas IA"},
            "pt": {"name": "Observabilidade", "description": "Frameworks para monitorar e observar o comportamento de sistemas IA"},
            "fr": {"name": "Observabilité", "description": "Frameworks pour surveiller et observer le comportement des systèmes IA"},
            "zh": {"name": "可观测性", "description": "用于监控和观察AI系统行为的框架"},
        },
    },
    {
        "slug": "cost_optimization",
        "translations": {
            "en": {"name": "Cost Optimization", "description": "Frameworks for optimizing AI infrastructure costs"},
            "es": {"name": "Optimización de Costos", "description": "Frameworks para optimizar costos de infraestructura IA"},
            "pt": {"name": "Otimização de Custos", "description": "Frameworks para otimizar custos de infraestrutura IA"},
            "fr": {"name": "Optimisation des Coûts", "description": "Frameworks pour optimiser les coûts d'infrastructure IA"},
            "zh": {"name": "成本优化", "description": "用于优化AI基础设施成本的框架"},
        },
    },
]

# Independent taxonomy version for orchestrator categories
ORCHESTRATOR_TAXONOMY_VERSION = "orchestrators-v1"


async def seed_orchestrator_categories(session: AsyncSession) -> dict:
    """Seed orchestrator categories into the database.

    Returns:
        Dict with counts of created/skipped items.
    """
    created = 0
    skipped = 0

    # Ensure taxonomy version exists
    from app.taxonomy.models.entities import TaxonomyVersion

    existing_version = await session.execute(
        select(TaxonomyVersion).where(TaxonomyVersion.version == ORCHESTRATOR_TAXONOMY_VERSION)
    )
    if not existing_version.scalars().first():
        now = datetime.now(UTC)
        version = TaxonomyVersion(
            id=str(uuid.uuid4()),
            version=ORCHESTRATOR_TAXONOMY_VERSION,
            released_at=now,
            notes="Orchestrator categories taxonomy",
            is_current=True,
        )
        session.add(version)

    for cat_data in ORCHESTRATOR_CATEGORIES:
        # Check if category already exists
        existing = await session.execute(
            select(Category).where(
                Category.slug == cat_data["slug"],
                Category.taxonomy_version == ORCHESTRATOR_TAXONOMY_VERSION,
            )
        )
        if existing.scalars().first():
            skipped += 1
            continue

        # Create category
        cat_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        category = Category(
            id=cat_id,
            slug=cat_data["slug"],
            parent_id=None,
            taxonomy_version=ORCHESTRATOR_TAXONOMY_VERSION,
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(category)

        # Create translations
        for locale, trans in cat_data["translations"].items():
            translation = CategoryTranslation(
                id=str(uuid.uuid4()),
                category_id=cat_id,
                locale=locale,
                name=trans["name"],
                description=trans["description"],
            )
            session.add(translation)

        created += 1

    await session.commit()

    return {
        "categories_created": created,
        "categories_skipped": skipped,
        "taxonomy_version": ORCHESTRATOR_TAXONOMY_VERSION,
    }
