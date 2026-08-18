import time
from common import benchmark_call, save_batch_results
from services.career.provider import MockJobProvider
from services.career.pipeline import run_job_pipeline
from services.career.packet import generate_application_packet
from services.career.portal.engine import PortalAutomationEngine
from services.career.portal.mock_portal import MockApplicationPortal



def run_batch_career_portal():
    print("\n🚀 [BATCH D] Running Career OS & Portal Automation Benchmarks...")
    results = []

    # 1. Multi-Provider Ingestion + Normalization + Deduplication
    p1 = MockJobProvider()
    p2 = MockJobProvider()

    def test_job_ingestion():
        return run_job_pipeline(query="SDE", providers=[p1, p2])

    results.append(benchmark_call(
        name="Career: Multi-Provider Ingestion + Normalization + Dedup (20 Jobs)",
        category="Career",
        mode="LOCAL_REAL",
        fn=test_job_ingestion,
        iterations=30,
    ))

    # 2. Application Packet Generation
    sample_job = {
        "id": 201, "title": "Senior AI Infrastructure Engineer", "company": "MockCorp",
        "url": "https://careers.mockcorp.io/apply/201", "location": "Remote", "salary_raw": "$210k"
    }

    def test_packet_gen():
        return generate_application_packet(job=sample_job)

    results.append(benchmark_call(
        name="Career: Application Packet Assembly + SHA-256 Hash Binding",
        category="Career",
        mode="LOCAL_REAL",
        fn=test_packet_gen,
        iterations=40,
    ))

    # 3. Portal Form Discovery & Mapping
    engine = PortalAutomationEngine()
    _counter = 0

    def test_portal_discovery():
        nonlocal _counter
        _counter += 1
        job = {
            "id": 100000 + _counter,
            "title": f"Senior AI Infrastructure Engineer {_counter}",
            "company": f"MockCorp_{_counter}_{time.time()}",
            "url": f"https://careers.mockcorp.io/apply/{_counter}",
            "location": "Remote",
            "salary_raw": "$210k"
        }
        pkt = generate_application_packet(job=job)
        p = MockApplicationPortal()
        return engine.create_portal_session(pkt, portal=p)

    results.append(benchmark_call(
        name="Portal: Form Schema Discovery + Sensitivity Classification",
        category="Portal",
        mode="LOCAL_REAL",
        fn=test_portal_discovery,
        iterations=35,
    ))

    # 4. End-to-End Portal Execution
    def test_full_portal_execution():
        nonlocal _counter
        _counter += 1
        job = {
            "id": 200000 + _counter,
            "title": f"Staff AI Engineer {_counter}",
            "company": f"MockCorpExec_{_counter}_{time.time()}",
            "url": f"https://careers.mockcorp.io/apply/{_counter}",
            "location": "Remote",
            "salary_raw": "$210k"
        }
        pkt = generate_application_packet(job=job)
        p = MockApplicationPortal()
        sess_init = engine.create_portal_session(pkt, portal=p)
        sess_id = sess_init["session_id"]
        token = sess_init["approval_token"]
        return engine.execute_approved_submission(
            session_id=sess_id,
            approval_token=token,
            current_packet=pkt,
            confirmed_review_fields={"confirmed": True},
        )

    results.append(benchmark_call(
        name="Portal: Approved Submission Execution + Independent Verification",
        category="Portal",
        mode="LOCAL_REAL",
        fn=test_full_portal_execution,
        iterations=30,
    ))





    save_batch_results("batch_career_portal", results)


if __name__ == "__main__":
    run_batch_career_portal()
