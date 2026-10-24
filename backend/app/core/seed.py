"""Database seeding script for realistic enterprise demo scenarios."""

import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.team import Team
from app.models.ticket import (
    Ticket,
    TicketMessage,
    TicketStatus,
    TicketPriority,
    TicketCategory,
    TicketChannel,
    MessageSenderType,
)


def seed_database(db: Session = None):
    close_session = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_session = True

    try:
        # Check if already seeded
        existing_org = db.query(Organization).filter(Organization.slug == "acme-global").first()
        if existing_org:
            print("Database already contains seed data for Acme Global.")
            return

        print("Seeding database with enterprise demo scenarios...")
        now = datetime.now(timezone.utc)

        # 1. Organization
        org = Organization(
            name="Acme Global Technologies",
            slug="acme-global",
            plan="enterprise",
        )
        db.add(org)
        db.flush()

        # 2. Teams
        tier1 = Team(organization_id=org.id, name="Tier 1 Support", description="General customer inquiries and initial triage")
        billing = Team(organization_id=org.id, name="Billing & Finance", description="Payments, refunds, and subscription queries")
        tech = Team(organization_id=org.id, name="Technical Escalations", description="Bugs, API issues, and platform errors")
        db.add_all([tier1, billing, tech])
        db.flush()

        # 3. Users
        admin = User(
            organization_id=org.id,
            email="admin@acme.com",
            password_hash=get_password_hash("Password123!"),
            full_name="Sarah Connor (Admin)",
            role=UserRole.ADMIN,
            is_active=True,
        )
        manager = User(
            organization_id=org.id,
            email="manager@acme.com",
            password_hash=get_password_hash("Password123!"),
            full_name="Alex Rivera (Lead)",
            role=UserRole.SUPPORT_MANAGER,
            is_active=True,
        )
        agent = User(
            organization_id=org.id,
            email="agent@acme.com",
            password_hash=get_password_hash("Password123!"),
            full_name="David Kim (Support)",
            role=UserRole.SUPPORT_AGENT,
            is_active=True,
        )
        db.add_all([admin, manager, agent])
        db.flush()

        # 4. Realistic Support Tickets
        tickets_data = [
            {
                "ref": "RES-2026-0001",
                "customer": ("Michael Vance", "michael.vance@example.com"),
                "subject": "Double charged for Enterprise Annual Subscription",
                "desc": "I was charged twice ($4,800 x 2) on invoice #INV-9821 on Oct 23rd. Please issue a refund for the duplicate transaction.",
                "category": TicketCategory.REFUNDS,
                "priority": TicketPriority.HIGH,
                "status": TicketStatus.IN_PROGRESS,
                "channel": TicketChannel.WEB,
                "team": billing,
                "agent": agent,
                "first_resp_hours": 2,
                "res_hours": 8,
                "messages": [
                    ("customer", None, "I was charged twice ($4,800 x 2) on invoice #INV-9821 on Oct 23rd. Please issue a refund for the duplicate transaction.", False, -3),
                    ("agent", agent, "Hi Michael, thank you for reaching out. I see the duplicate charge on Stripe and have initiated refund #ref_2910 for $4,800.", False, -2),
                    ("agent", agent, "Internal note: Verified Stripe payment intent; finance authorization token attached.", True, -1),
                ],
            },
            {
                "ref": "RES-2026-0002",
                "customer": ("Elena Rostova", "elena.r@devops-cloud.io"),
                "subject": "Production REST API returning 504 Gateway Timeout during sync",
                "desc": "Our ETL pipeline syncing customer tables is encountering HTTP 504 Gateway Timeouts on /v2/records since 14:00 UTC.",
                "category": TicketCategory.TECHNICAL,
                "priority": TicketPriority.CRITICAL,
                "status": TicketStatus.OPEN,
                "channel": TicketChannel.API,
                "team": tech,
                "agent": None,
                "first_resp_hours": 1,
                "res_hours": 4,
                "messages": [
                    ("customer", None, "Our ETL pipeline syncing customer tables is encountering HTTP 504 Gateway Timeouts on /v2/records since 14:00 UTC.", False, -1),
                ],
            },
            {
                "ref": "RES-2026-0003",
                "customer": ("Marcus Aurelius", "marcus@zenith-logistics.com"),
                "subject": "Account Lockout: Cannot receive 2FA SMS code",
                "desc": "I recently switched phone carriers and am not receiving the SMS 2FA passcode to log into our production tenant.",
                "category": TicketCategory.ACCOUNT,
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.WAITING_CUSTOMER,
                "channel": TicketChannel.EMAIL,
                "team": tier1,
                "agent": agent,
                "first_resp_hours": 4,
                "res_hours": 24,
                "messages": [
                    ("customer", None, "I recently switched phone carriers and am not receiving the SMS 2FA passcode to log into our production tenant.", False, -5),
                    ("agent", agent, "Hello Marcus, we can switch your 2FA method to an Authenticator app (TOTP). Could you please verify the last 4 digits of your billing card on file?", False, -4),
                ],
            },
            {
                "ref": "RES-2026-0004",
                "customer": ("Priya Sharma", "priya.sharma@fintech-labs.in"),
                "subject": "Invoice #8821 Tax calculation error for GST",
                "desc": "The GST tax ID is listed correctly on our profile, but the invoice did not include the 18% reverse charge tax breakdown.",
                "category": TicketCategory.BILLING,
                "priority": TicketPriority.MEDIUM,
                "status": TicketStatus.RESOLVED,
                "channel": TicketChannel.WEB,
                "team": billing,
                "agent": manager,
                "first_resp_hours": 4,
                "res_hours": 24,
                "messages": [
                    ("customer", None, "The GST tax ID is listed correctly on our profile, but the invoice did not include the 18% reverse charge tax breakdown.", False, -24),
                    ("agent", manager, "Hi Priya, our finance team has regenerated invoice #8821-R with the verified GSTIN breakdown. It is available in your billing portal.", False, -20),
                ],
            },
            {
                "ref": "RES-2026-0005",
                "customer": ("Liam O'Connor", "liam@celtic-retail.com"),
                "subject": "Order #4810 shipment tracking link invalid",
                "desc": "The FedEx tracking link provided in the shipping confirmation email returns 'Tracking number not found'.",
                "category": TicketCategory.ORDERS,
                "priority": TicketPriority.LOW,
                "status": TicketStatus.OPEN,
                "channel": TicketChannel.WEB,
                "team": tier1,
                "agent": None,
                "first_resp_hours": 8,
                "res_hours": 48,
                "messages": [
                    ("customer", None, "The FedEx tracking link provided in the shipping confirmation email returns 'Tracking number not found'.", False, -2),
                ],
            },
        ]

        for t_spec in tickets_data:
            t_created = now + timedelta(hours=t_spec["messages"][0][4])
            t_first_resp = t_created + timedelta(hours=t_spec["first_resp_hours"])
            t_res_deadline = t_created + timedelta(hours=t_spec["res_hours"])

            ticket = Ticket(
                organization_id=org.id,
                reference_number=t_spec["ref"],
                customer_name=t_spec["customer"][0],
                customer_email=t_spec["customer"][1],
                subject=t_spec["subject"],
                description=t_spec["desc"],
                category=t_spec["category"],
                priority=t_spec["priority"],
                status=t_spec["status"],
                channel=t_spec["channel"],
                assigned_team_id=t_spec["team"].id if t_spec["team"] else None,
                assigned_agent_id=t_spec["agent"].id if t_spec["agent"] else None,
                first_response_deadline=t_first_resp,
                resolution_deadline=t_res_deadline,
                first_responded_at=t_created + timedelta(minutes=45) if len(t_spec["messages"]) > 1 else None,
                resolved_at=now - timedelta(hours=2) if t_spec["status"] == TicketStatus.RESOLVED else None,
                created_at=t_created,
                updated_at=now,
            )
            db.add(ticket)
            db.flush()

            for sender_type, user_obj, body, is_internal, offset_hours in t_spec["messages"]:
                msg_time = now + timedelta(hours=offset_hours)
                msg = TicketMessage(
                    ticket_id=ticket.id,
                    sender_type=MessageSenderType.AGENT if sender_type == "agent" else MessageSenderType.CUSTOMER,
                    sender_user_id=user_obj.id if user_obj else None,
                    body=body,
                    is_internal_note=is_internal,
                    created_at=msg_time,
                )
        # 5. Knowledge Documents & Vector Chunks
        from app.models.knowledge import KnowledgeDocument, DocumentChunk, DocumentStatus
        from app.ai.embeddings import EmbeddingEngine
        import json

        docs_spec = [
            {
                "title": "Official Acme Enterprise Billing & Refund Policy",
                "file_type": "md",
                "sections": [
                    (
                        "Refund & Duplicate Charges",
                        "Customers requesting a refund within 30 days of initial subscription are entitled to a full 100% refund. Duplicate charges will be processed immediately upon verification with invoice receipts and Stripe payment intents. Refunds typically take 3-5 business days to reflect on the customer's credit card statement."
                    ),
                    (
                        "Tax Invoices & GST Regulations",
                        "Tax invoices are generated on the 1st of every calendar month. If an enterprise customer holds a valid GSTIN or VAT registration number, reverse charge mechanisms are applied automatically provided the tax ID is verified prior to billing cycle generation."
                    ),
                ]
            },
            {
                "title": "Acme Platform REST API & Security Troubleshooting Manual",
                "file_type": "md",
                "sections": [
                    (
                        "API 504 Gateway Timeouts & Rate Limits",
                        "HTTP 504 Gateway Timeout errors occur when upstream ETL pipelines execute unindexed queries exceeding the 30-second gateway threshold. To resolve, clients must paginate requests with limit=100 or use the asynchronous /v2/bulk-export API endpoint."
                    ),
                    (
                        "Account Recovery & 2FA Lockout Procedures",
                        "When a customer is locked out due to carrier switch or missing SMS 2FA codes, the support agent must verify the last 4 digits of the payment card on file. Upon confirmation, the agent triggers a TOTP authenticator reset email to the account's primary email address."
                    ),
                    (
                        "Order Shipping & Carrier Tracking Propagation",
                        "Order confirmation emails contain carrier tracking links. Note that FedEx and UPS carrier tracking numbers take up to 4 to 6 hours after label generation to propagate on national carrier tracking databases. If 'Tracking number not found' appears within 6 hours, ask the customer to retry after 6 PM."
                    ),
                ]
            }
        ]

        for d_spec in docs_spec:
            doc = KnowledgeDocument(
                organization_id=org.id,
                title=d_spec["title"],
                file_type=d_spec["file_type"],
                file_path=f"./storage/{org.id}/{d_spec['title'].lower().replace(' ', '_')}.md",
                file_size=2048,
                status=DocumentStatus.INDEXED,
                chunk_count=len(d_spec["sections"]),
            )
            db.add(doc)
            db.flush()

            for idx, (section_title, chunk_content) in enumerate(d_spec["sections"]):
                embedding = EmbeddingEngine.get_embedding(chunk_content)
                chunk = DocumentChunk(
                    document_id=doc.id,
                    organization_id=org.id,
                    chunk_index=idx + 1,
                    content=chunk_content,
                    metadata_json=json.dumps({"section": section_title, "page": 1}),
                    embedding_json=json.dumps(embedding),
                )
                db.add(chunk)

        db.commit()
        print("Database seed completed successfully with tickets, knowledge documents, and vector embeddings!")


    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    seed_database()
