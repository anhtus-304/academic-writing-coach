import pytest
import uuid
from services.proposal_service import proposal_service, _content_hash
from models.user import User
from models.project import Project
from models.draft_document import DraftDocument
from models.agent_job import AgentJob
from models.agent_proposal import AgentProposal
from database import AsyncSessionLocal, engine, Base

@pytest.mark.asyncio
async def test_proposal_lifecycle_and_apply():
    # Ensure tables exist and schema is up to date
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: AgentProposal.__table__.drop(sync_conn, checkfirst=True))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db_session:
        # Setup test user and project
        user = User(
            email=f"test_{uuid.uuid4().hex[:6]}@example.com",
            display_name="Test Researcher",
            credit_balance=50,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        project = Project(
            topic="Test Proposal Workflow",
            field="Computer Science",
            citation_style="ieee",
            user_id=user.id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        # 1. Base content
        base_text = "<p>Initial paragraph.</p>"
        base_hash = _content_hash(base_text)

        # Create DraftDocument
        draft = DraftDocument(
            project_id=project.id,
            content={"html": base_text},
            version=1,
        )
        db_session.add(draft)
        await db_session.commit()

        # 2. Create Job and Proposal
        job = AgentJob(
            project_id=project.id,
            user_id=user.id,
            mode="auto",
            status="awaiting_approval",
            prompt="Add section 2 and replace initial",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        op1_id = str(uuid.uuid4())
        op2_id = str(uuid.uuid4())
        proposal_data = {
            "job_id": job.id,
            "base_version": 1,
            "base_hash": base_hash,
            "target_type": "document",
            "operations": [
                {
                    "operation_id": op1_id,
                    "type": "replace",
                    "before": "<p>Initial paragraph.</p>",
                    "after": "<p>Updated initial paragraph.</p>",
                    "status": "pending",
                },
                {
                    "operation_id": op2_id,
                    "type": "insert",
                    "after": "<p>New inserted conclusion.</p>",
                    "status": "pending",
                }
            ]
        }
        proposal = await proposal_service.save_proposal(db_session, proposal_data)
        assert proposal.status == "pending"
        assert len(proposal.operations) == 2

        # 3. Test record_decisions (partial accept op1 only)
        updated_prop = await proposal_service.record_decisions(
            db_session,
            proposal.id,
            user.id,
            decisions=[{"operation_id": op1_id, "decision": "accept"}],
        )
        # Verify in-memory and persistence
        assert updated_prop.status == "partially_accepted"
        ops = updated_prop.operations
        assert ops[0]["status"] == "accepted"
        assert ops[1]["status"] == "pending"

        # Query afresh from DB to verify SQLAlchemy JSON flag_modified dirty tracking worked!
        fresh_prop = await db_session.get(AgentProposal, proposal.id)
        await db_session.refresh(fresh_prop)
        assert fresh_prop.operations[0]["status"] == "accepted", "flag_modified must persist JSON changes to DB"

        # 4. Apply partial proposal (only op1)
        apply_result = await proposal_service.apply_proposal(
            db_session,
            project_id=project.id,
            proposal_id=proposal.id,
            accepted_operation_ids=[op1_id],
            base_version=1,
            base_hash=base_hash,
        )

        assert apply_result["success"] is True
        assert apply_result["new_version"] == 2
        assert op1_id in apply_result["applied_operations"]
        assert "content" in apply_result
        assert "<p>Updated initial paragraph.</p>" in apply_result["content"]
        assert "<p>New inserted conclusion.</p>" not in apply_result["content"]

        # Verify DraftDocument in DB updated
        updated_draft = await db_session.get(DraftDocument, draft.id)
        await db_session.refresh(updated_draft)
        assert updated_draft.version == 2
        assert "<p>Updated initial paragraph.</p>" in updated_draft.content["html"]


@pytest.mark.asyncio
async def test_tracked_html_lifecycle():
    before = "<h2>CHƯƠNG 1</h2><p>Đoạn cũ.</p>"
    after = "<h2>CHƯƠNG 1</h2><p>Đoạn mới được AI viết.</p><h3>1.1. Tiểu mục mới</h3>"

    tracked_html, ops = proposal_service.generate_tracked_html(before, after)
    assert len(ops) > 0
    assert "diff-del" in tracked_html
    assert "diff-ins" in tracked_html
    assert "Đoạn cũ." in tracked_html
    assert "Đoạn mới được AI viết." in tracked_html

    # Test Accept All: removes <del>, keeps <ins> content
    accepted_html = proposal_service.clean_tracked_html(tracked_html, action="accept_all")
    assert "<del" not in accepted_html
    assert "<ins" not in accepted_html
    assert "Đoạn cũ." not in accepted_html
    assert "Đoạn mới được AI viết." in accepted_html
    assert "<h3>1.1. Tiểu mục mới</h3>" in accepted_html

    # Test Reject All: removes <ins>, restores original from <del>
    rejected_html = proposal_service.clean_tracked_html(tracked_html, action="reject_all")
    assert "<ins" not in rejected_html
    assert "<del" not in rejected_html
    assert "Đoạn cũ." in rejected_html
    assert "Đoạn mới được AI viết." not in rejected_html


@pytest.mark.asyncio
async def test_orchestrator_build_and_save_proposal():
    from services.orchestrator_service import orchestrator_service
    from models.user import User
    from models.project import Project
    from models.agent_job import AgentJob
    from models.draft_document import DraftDocument
    from sqlalchemy import select

    async with AsyncSessionLocal() as db_session:
        user = User(
            email=f"orch_{uuid.uuid4().hex[:6]}@test.com",
            display_name="Orch Researcher",
            credit_balance=50,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        project = Project(
            user_id=user.id,
            topic="Orch Test Topic",
            field="Education",
            citation_style="apa7",
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        job = AgentJob(
            user_id=user.id,
            project_id=project.id,
            mode="auto",
            prompt="Write draft",
            status="running",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        agent_state = {
            "composed_content": "<h2>Chương 1</h2><p>Đoạn văn hoàn chỉnh do compose_agent tạo.</p>",
            "composed_sections": [{"title": "Chương 1"}],
            "extracted_evidence": [{"citation_key": "Nguyen2024", "quote": "trích dẫn test"}],
            "validation_report": {"warnings": []},
        }

        # Call orchestrator's _build_and_save_proposal
        has_prop = await orchestrator_service._build_and_save_proposal(db_session, job, agent_state)
        assert has_prop is True

        # Check DraftDocument updated with tracked_html
        stmt = select(DraftDocument).where(DraftDocument.project_id == project.id)
        draft_res = await db_session.execute(stmt)
        draft = draft_res.scalar_one_or_none()
        assert draft is not None
        assert "Chương 1" in draft.content["html"]


