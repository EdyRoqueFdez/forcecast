"""Seed script for problem domains — HU-T05."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import Domain, DomainTranslation


DOMAINS = [
    {
        "slug": "healthcare",
        "translations": {
            "en": {"name": "Healthcare", "description": "Medical, clinical, and health-related problems"},
            "es": {"name": "Salud", "description": "Problemas médicos, clínicos y relacionados con la salud"},
            "pt": {"name": "Saúde", "description": "Problemas médicos, clínicos e relacionados à saúde"},
            "fr": {"name": "Santé", "description": "Problèmes médicaux, cliniques et liés à la santé"},
            "zh": {"name": "医疗保健", "description": "医疗、临床和健康相关问题"},
        },
    },
    {
        "slug": "travel",
        "translations": {
            "en": {"name": "Travel", "description": "Tourism, hospitality, and travel planning problems"},
            "es": {"name": "Viajes", "description": "Problemas de turismo, hostelería y planificación de viajes"},
            "pt": {"name": "Viagens", "description": "Problemas de turismo, hospitalidade e planejamento de viagens"},
            "fr": {"name": "Voyage", "description": "Problèmes de tourisme, hôtellerie et planification de voyages"},
            "zh": {"name": "旅行", "description": "旅游、酒店和旅行规划问题"},
        },
    },
    {
        "slug": "finance",
        "translations": {
            "en": {"name": "Finance", "description": "Banking, investment, and financial services problems"},
            "es": {"name": "Finanzas", "description": "Problemas de banca, inversión y servicios financieros"},
            "pt": {"name": "Finanças", "description": "Problemas de banca, investimento e serviços financeiros"},
            "fr": {"name": "Finance", "description": "Problèmes bancaires, d'investissement et de services financiers"},
            "zh": {"name": "金融", "description": "银行、投资和金融服务问题"},
        },
    },
    {
        "slug": "legal",
        "translations": {
            "en": {"name": "Legal", "description": "Legal, compliance, and regulatory problems"},
            "es": {"name": "Legal", "description": "Problemas legales, de cumplimiento y regulatorios"},
            "pt": {"name": "Jurídico", "description": "Problemas legais, de conformidade e regulatórios"},
            "fr": {"name": "Juridique", "description": "Problèmes juridiques, de conformité et réglementaires"},
            "zh": {"name": "法律", "description": "法律、合规和监管问题"},
        },
    },
    {
        "slug": "retail",
        "translations": {
            "en": {"name": "Retail", "description": "E-commerce, sales, and customer service problems"},
            "es": {"name": "Comercio", "description": "Problemas de comercio electrónico, ventas y servicio al cliente"},
            "pt": {"name": "Varejo", "description": "Problemas de comércio eletrônico, vendas e atendimento ao cliente"},
            "fr": {"name": "Commerce", "description": "Problèmes de e-commerce, ventes et service client"},
            "zh": {"name": "零售", "description": "电子商务、销售和客户服务问题"},
        },
    },
    {
        "slug": "education",
        "translations": {
            "en": {"name": "Education", "description": "Learning, training, and educational content problems"},
            "es": {"name": "Educación", "description": "Problemas de aprendizaje, capacitación y contenido educativo"},
            "pt": {"name": "Educação", "description": "Problemas de aprendizagem, treinamento e conteúdo educacional"},
            "fr": {"name": "Éducation", "description": "Problèmes d'apprentissage, de formation et de contenu éducatif"},
            "zh": {"name": "教育", "description": "学习、培训和教育内容问题"},
        },
    },
    {
        "slug": "logistics",
        "translations": {
            "en": {"name": "Logistics", "description": "Supply chain, transportation, and inventory problems"},
            "es": {"name": "Logística", "description": "Problemas de cadena de suministro, transporte e inventario"},
            "pt": {"name": "Logística", "description": "Problemas de cadeia de suprimentos, transporte e inventário"},
            "fr": {"name": "Logistique", "description": "Problèmes de chaîne d'approvisionnement, transport et inventaire"},
            "zh": {"name": "物流", "description": "供应链、运输和库存问题"},
        },
    },
    {
        "slug": "other",
        "translations": {
            "en": {"name": "Other", "description": "Problems that don't fit into other categories"},
            "es": {"name": "Otros", "description": "Problemas que no encajan en otras categorías"},
            "pt": {"name": "Outros", "description": "Problemas que não se encaixam em outras categorias"},
            "fr": {"name": "Autre", "description": "Problèmes qui ne correspondent pas à d'autres catégories"},
            "zh": {"name": "其他", "description": "不属于其他类别的问题"},
        },
    },
]


async def seed_domains(session: AsyncSession) -> dict:
    """Seed problem domains into the database.

    Returns:
        Dict with counts of created/skipped items.
    """
    created = 0
    skipped = 0

    for domain_data in DOMAINS:
        # Check if domain already exists
        existing = await session.execute(
            select(Domain).where(Domain.slug == domain_data["slug"])
        )
        if existing.scalars().first():
            skipped += 1
            continue

        # Create domain
        domain_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        domain = Domain(
            id=domain_id,
            slug=domain_data["slug"],
            parent_id=None,
            taxonomy_version="v1",
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(domain)

        # Create translations
        for locale, trans in domain_data["translations"].items():
            translation = DomainTranslation(
                id=str(uuid.uuid4()),
                domain_id=domain_id,
                locale=locale,
                name=trans["name"],
                description=trans["description"],
            )
            session.add(translation)

        created += 1

    await session.commit()

    return {
        "domains_created": created,
        "domains_skipped": skipped,
    }
